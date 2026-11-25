param(
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')]
    [string]$Project = ('ecommerce-smoke-' + [guid]::NewGuid().ToString('N')),
    [string]$Image = 'ecommerce-fullstack:local',
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [ValidatePattern('^172\.(1[6-9]|2[0-9]|3[01])\.(0|[1-9][0-9]?|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')]
    [string]$SubnetPrefix = '172.30.80',
    [switch]$KeepRunning,
    [switch]$CleanupVolumes,
    [string]$CleanupMarker
)

$ErrorActionPreference = 'Stop'
$compose = @('--project-name', $Project, '--env-file', '.env.example')
$base = "http://127.0.0.1:$Port"
$chatOrigin = 'http://127.0.0.1:8000'
# Use the production Host and Origin even when a local test needs an alternate socket.
$chatHost = @{ Host = '127.0.0.1:8000' }
$succeeded = $false

if ($KeepRunning -and $CleanupVolumes) { throw 'Choose either KeepRunning or CleanupVolumes.' }
if ($CleanupMarker -and -not $CleanupVolumes) { throw 'CleanupMarker requires CleanupVolumes.' }

# Refuse to reuse a project or its volumes, including unlabeled volume name collisions.
$projectLabel = "label=com.docker.compose.project=$Project"
$helperLabel = "label=ecommerce.smoke.project=$Project"
$existing = @(docker ps -aq --filter $projectLabel)
if ($LASTEXITCODE -ne 0) { throw 'Could not list Compose containers.' }
$existing += @(docker ps -aq --filter $helperLabel)
if ($LASTEXITCODE -ne 0) { throw 'Could not list smoke-test helpers.' }
$existing += @(docker network ls -q --filter $projectLabel)
if ($LASTEXITCODE -ne 0) { throw 'Could not list Compose networks.' }
$volumes = @(docker volume ls -q)
if ($LASTEXITCODE -ne 0) { throw 'Could not list Docker volumes.' }
if ($existing.Count -or "${Project}_warehouse" -in $volumes -or "${Project}_usage" -in $volumes) {
    throw "Smoke test requires a fresh Compose project: $Project."
}
$imageId = docker image inspect --format '{{.Id}}' $Image
if ($LASTEXITCODE -ne 0) { throw "Smoke test requires a locally built image: $Image." }
if ($CleanupMarker) { Set-Content -LiteralPath $CleanupMarker -Value $Project }
$previousImage = $env:ECOMMERCE_IMAGE
$previousPort = $env:ECOMMERCE_PORT
$previousSubnet = $env:ECOMMERCE_SUBNET
$previousGateway = $env:ECOMMERCE_GATEWAY
$env:ECOMMERCE_IMAGE = $Image
$env:ECOMMERCE_PORT = "$Port"
$env:ECOMMERCE_SUBNET = "$SubnetPrefix.0/24"
$env:ECOMMERCE_GATEWAY = "$SubnetPrefix.1"

function Invoke-Compose {
    docker compose @compose @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose command failed ($LASTEXITCODE)." }
}

function Assert-Status([int]$Expected, [string]$Path, [hashtable]$Options = @{}) {
    try {
        $response = Invoke-WebRequest -Uri "$base$Path" -UseBasicParsing @Options
        $actual = [int]$response.StatusCode
    } catch {
        if (-not $_.Exception.Response) { throw }
        $actual = [int]$_.Exception.Response.StatusCode
    }
    if ($actual -ne $Expected) { throw "Expected HTTP $Expected at $Path, got $actual." }
}

function Wait-ForApi {
    foreach ($attempt in 1..30) {
        try {
            if ((Invoke-RestMethod "$base/health" -TimeoutSec 3).status -eq 'ok') { return }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw 'The container did not become ready.'
}

try {
    @'
import os
import re
import shutil
from pathlib import Path

assert "ANTHROPIC_API_KEY" not in os.environ
assert shutil.which("node") is None
assert shutil.which("npm") is None
for root in map(Path, ("/app", "/data", "/usage")):
    for path in root.rglob("*"):
        assert path.name not in {".git", ".venv", "node_modules", ".claude", ".mcp.json"}
        assert not path.name.startswith(".env")
        assert not path.name.endswith((".duckdb", ".duckdb.wal", ".sqlite3", ".map"))
dist = Path("/app/frontend/dist")
assert set(dist.parent.iterdir()) == {dist}
for path in (dist / "assets").iterdir():
    assert not re.search(rb"sk-ant-[a-zA-Z0-9_-]{20,}", path.read_bytes())
print("Verified clean image filesystem and compiled-only frontend.")
'@ | docker run --rm --interactive --label "ecommerce.smoke.project=$Project" --network none $Image python -
    if ($LASTEXITCODE -ne 0) { throw 'Image content check failed.' }
    Invoke-Compose run --rm --no-deps --pull never refresh
    Invoke-Compose up --detach --no-build --pull never app
    Wait-ForApi

    $dashboardResponse = Invoke-WebRequest "$base/" -UseBasicParsing
    if ($dashboardResponse.Content -notmatch '<title>Commerce Intelligence</title>') { throw 'Missing compiled dashboard.' }
    $assets = [regex]::Matches($dashboardResponse.Content, '/assets/[^" ]+\.(js|css)').Value
    if ($assets.Count -lt 2) { throw 'Missing compiled asset links.' }
    foreach ($asset in $assets) { Assert-Status 200 $asset }
    $favicon = Invoke-WebRequest "$base/favicon.svg" -UseBasicParsing
    if ([string]$favicon.Headers['Content-Type'] -notmatch 'image/svg\+xml') { throw 'Missing SVG favicon.' }

    foreach ($path in @('/health', '/api/v1/kpis', '/api/v1/products/top', '/api/v1/categories',
        '/api/v1/customers/top', '/api/v1/inventory/low-stock', '/docs', '/openapi.json')) {
        Assert-Status 200 $path
    }
    $kpis = Invoke-RestMethod "$base/api/v1/kpis"
    if ($kpis.total_gross_cart_value -ne '20.00' -or $kpis.cart_count -ne 3 -or
        $kpis.average_cart_value -ne '6.67' -or $kpis.total_quantity -ne 3) { throw 'Wrong fixture KPIs.' }
    $schema = Invoke-RestMethod "$base/openapi.json"
    if (-not $schema.paths.'/api/v1/chat'.post) { throw 'Missing chat OpenAPI contract.' }
    Assert-Status 404 '/api/v1/unknown'
    try { Invoke-RestMethod "$base/api/v1/unknown" | Out-Null } catch {
        if ($_.ErrorDetails.Message -notmatch '"detail"\s*:\s*"Not Found"') { throw 'The API 404 was not JSON.' }
    }
    if ((Invoke-RestMethod "$base/api/v1/chat/status" -Headers $chatHost).availability -ne 'disabled') { throw 'AI must be disabled.' }
    $post = @{ Method = 'Post'; ContentType = 'application/json'; Body = '{"question":"Fixture KPI check"}'; Headers = $chatHost }
    Assert-Status 403 '/api/v1/chat' $post
    $post.Headers = $chatHost + @{ Origin = $chatOrigin; 'Sec-Fetch-Site' = 'same-origin' }
    Assert-Status 503 '/api/v1/chat' $post
    $post.Headers.Origin = 'http://127.0.0.1:5173'
    Assert-Status 403 '/api/v1/chat' $post

    $container = Invoke-Compose ps -q app
    if ((docker inspect --format '{{.Image}}' $container) -ne $imageId) { throw 'Unexpected serving image.' }
    $mounts = docker inspect --format '{{json .Mounts}}' $container | ConvertFrom-Json
    if (($mounts | Where-Object Destination -eq '/data').RW -ne $false -or
        ($mounts | Where-Object Destination -eq '/usage').RW -ne $true) { throw 'Invalid runtime mount modes.' }
    @'
import errno
import os
from decimal import Decimal
from pathlib import Path
from ecommerce.ai_config import usage_path_from_env
from ecommerce.ai_usage import Ledger, Usage

assert os.geteuid() == os.getegid() == 10001
try:
    with Path("/data/warehouse.duckdb").open("r+b"):
        raise AssertionError("Warehouse was writable")
except OSError as exc:
    assert exc.errno == errno.EROFS

ledger = Ledger(usage_path_from_env(), Decimal("2.00"))
assert ledger.balances() == (0, 2_000_000_000)
call = ledger.reserve("synthetic-smoke", "claude-haiku-5-5", 10_750_000)
ledger.settle(call, Usage(input_tokens=100, output_tokens=20))
print("Verified non-root runtime, read-only DuckDB file, and writable SQLite ledger.")
'@ | docker compose @compose exec -T app python -
    if ($LASTEXITCODE -ne 0) { throw 'Runtime storage check failed.' }

    @'
import urllib.error
import urllib.request
request = urllib.request.Request("http://app:8000/api/v1/chat/status", headers={
    "Host": "127.0.0.1:8000", "X-Forwarded-For": "127.0.0.1",
})
try:
    urllib.request.urlopen(request, timeout=5)
except urllib.error.HTTPError as error:
    assert error.code == 403
else:
    raise AssertionError("A sibling container reached chat")
print("Verified sibling and spoofed forwarded address rejection.")
'@ | docker run --rm --interactive --label "ecommerce.smoke.project=$Project" --network "${Project}_application" $Image python -
    if ($LASTEXITCODE -ne 0) { throw 'Bridge boundary check failed.' }

    Invoke-Compose restart app
    Wait-ForApi
    if ((Invoke-Compose ps -q app) -ne $container) { throw 'Restart unexpectedly replaced the container.' }
    Invoke-Compose up --detach --no-build --pull never --force-recreate app
    Wait-ForApi
    $replacement = Invoke-Compose ps -q app
    if ($replacement -eq $container) { throw 'Expected a replacement container.' }
    if ((docker inspect --format '{{.Image}}' $replacement) -ne $imageId) { throw 'Unexpected replacement image.' }
    if ((Invoke-RestMethod "$base/api/v1/kpis").snapshot_at -ne $kpis.snapshot_at) { throw 'Snapshot did not persist.' }
    @'
from decimal import Decimal
from ecommerce.ai_config import usage_path_from_env
from ecommerce.ai_usage import Ledger

assert Ledger(usage_path_from_env(), Decimal("2.00")).balances() == (20_000, 1_999_980_000)
print("Verified the fixture snapshot and synthetic usage after replacement.")
'@ | docker compose @compose exec -T app python -
    if ($LASTEXITCODE -ne 0) { throw 'Ledger persistence check failed.' }
    $succeeded = $true
} finally {
    try {
        if (-not ($KeepRunning -and $succeeded)) {
            try {
                $helpers = @(docker ps -aq --filter $helperLabel)
                if ($LASTEXITCODE -ne 0) { throw 'Could not list smoke-test helpers for cleanup.' }
                if ($helpers.Count) {
                    docker rm -f @helpers
                    if ($LASTEXITCODE -ne 0) { throw 'Could not remove smoke-test helpers.' }
                }
            } finally {
                if ($CleanupVolumes) {
                    Invoke-Compose down --volumes --remove-orphans
                } else {
                    Invoke-Compose down --remove-orphans
                }
            }
        }
        Write-Output "Verification project: $Project. Temporary volume cleanup: $CleanupVolumes."
    } finally {
        $env:ECOMMERCE_IMAGE = $previousImage
        $env:ECOMMERCE_PORT = $previousPort
        $env:ECOMMERCE_SUBNET = $previousSubnet
        $env:ECOMMERCE_GATEWAY = $previousGateway
    }
}
