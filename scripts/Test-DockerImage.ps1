param(
    [string]$Image = 'ecommerce-mvp:local',
    [switch]$KeepVolume
)

$ErrorActionPreference = 'Stop'
$id = [guid]::NewGuid().ToString('N')
$volume = "ecommerce-smoke-$id"
$names = @("ecommerce-api-$id-first", "ecommerce-api-$id-second")
$writable = "type=volume,source=$volume,target=/data"
$readOnly = "$writable,readonly"

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
}

Invoke-Docker volume create $volume | Out-Null
try {
    Invoke-Docker run --rm --mount $writable $Image python -m ecommerce.refresh --fixture-dir tests/fixtures
    $firstSnapshot = $null
    foreach ($name in $names) {
        Invoke-Docker run --detach --name $name --publish '127.0.0.1::8000' --mount $readOnly $Image | Out-Null
        $port = Invoke-Docker port $name '8000/tcp'
        if ($port -notmatch '^127\.0\.0\.1:\d+$') { throw "Expected a loopback-only host port." }
        $url = "http://$port"
        $health = $null
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $health = Invoke-RestMethod "$url/health" -TimeoutSec 2
                break
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        if ($health.status -ne 'ok') {
            Invoke-Docker logs $name
            throw "Container did not become healthy."
        }
        $kpis = Invoke-RestMethod "$url/api/v1/kpis"
        if ($kpis.total_gross_cart_value -cne '20.00' -or $kpis.cart_count -ne 3 -or
            $kpis.average_cart_value -cne '6.67' -or $kpis.total_quantity -ne 3 -or
            $kpis.metric_basis -cne 'gross_simulated_cart_line_value_before_discounts' -or !$kpis.snapshot_at) {
            throw "Fixture KPIs did not match expectations."
        }
        $swagger = Invoke-WebRequest "$url/docs" -UseBasicParsing
        if ($swagger.StatusCode -ne 200 -or $swagger.Content -notmatch 'Swagger UI') {
            throw "Swagger UI was unavailable."
        }
        $mount = Invoke-Docker inspect --format '{{json .Mounts}}' $name | ConvertFrom-Json
        if (@($mount | Where-Object { $_.Destination -eq '/data' -and $_.Name -eq $volume -and !$_.RW }).Count -ne 1) {
            throw "Expected the fixture volume to be mounted read-only at /data."
        }
        if ($null -eq $firstSnapshot) {
            $firstSnapshot = $kpis.snapshot_at
        } elseif ($firstSnapshot -ne $kpis.snapshot_at) {
            throw "The fixture snapshot changed when the serving container was recreated."
        }
        Write-Output "$name passed health, KPIs (20.00 / 3 / 6.67 / 3), Swagger and read-only mount checks."
        Invoke-Docker rm --force $name | Out-Null
    }
    Write-Output "Warehouse persisted across container recreation. Snapshot: $firstSnapshot"
}
finally {
    foreach ($name in $names) {
        $existing = & docker ps --all --quiet --filter "name=^/$name$"
        if ($existing) { Invoke-Docker rm --force $name | Out-Null }
    }
    if ($KeepVolume) {
        Write-Output "Retained volume: $volume"
    } else {
        Invoke-Docker volume rm $volume | Out-Null
    }
}
