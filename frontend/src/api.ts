import type {
  BusinessKpis, CategoryPerformance, CustomerPerformance, Health, InventoryProduct,
  ProductPerformance, SnapshotRows,
} from './contracts';

export class ApiError extends Error {
  readonly kind: 'connection' | 'warehouse' | 'response';

  constructor(message: string, kind: ApiError['kind']) {
    super(message);
    this.kind = kind;
  }
}

async function read<T>(path: string, signal: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { signal, headers: { Accept: 'application/json' }, cache: 'no-store' });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiError('Start FastAPI at 127.0.0.1:8000, then reload the dashboard.', 'connection');
  }

  const isJson = response.headers.get('content-type')?.includes('application/json');
  if (response.status === 503) {
    throw new ApiError(
      'FastAPI is reachable, but the warehouse is unavailable. Check WAREHOUSE_PATH and that the snapshot has been initialized.',
      'warehouse',
    );
  }
  if (response.status === 502 || response.status === 504 || (response.status === 500 && !isJson)) {
    throw new ApiError('Start FastAPI at 127.0.0.1:8000, then reload the dashboard.', 'connection');
  }
  if (!response.ok) {
    throw new ApiError(`The API returned HTTP ${response.status}. Try reloading the dashboard.`, 'response');
  }
  if (!isJson) {
    throw new ApiError('The server returned an unexpected response. Check that the API proxy is configured.', 'response');
  }
  try {
    return await response.json() as T;
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiError('The API returned invalid JSON. Try reloading the dashboard.', 'response');
  }
}

export const api = {
  health: (signal: AbortSignal) => read<Health>('/health', signal),
  kpis: (signal: AbortSignal) => read<BusinessKpis>('/api/v1/kpis', signal),
  categories: (signal: AbortSignal) => read<SnapshotRows<CategoryPerformance>>('/api/v1/categories', signal),
  products: (limit: number, signal: AbortSignal) =>
    read<SnapshotRows<ProductPerformance>>(`/api/v1/products/top?${new URLSearchParams({ limit: String(limit) })}`, signal),
  customers: (limit: number, signal: AbortSignal) =>
    read<SnapshotRows<CustomerPerformance>>(`/api/v1/customers/top?${new URLSearchParams({ limit: String(limit) })}`, signal),
  inventory: (threshold: number, signal: AbortSignal) =>
    read<SnapshotRows<InventoryProduct>>(`/api/v1/inventory/low-stock?${new URLSearchParams({ threshold: String(threshold) })}`, signal),
};
