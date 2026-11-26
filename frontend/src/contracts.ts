export interface Snapshot {
  snapshot_at: string;
  metric_basis: 'gross_simulated_cart_line_value_before_discounts';
}

export interface Health {
  status: 'ok';
}

export interface BusinessKpis extends Snapshot {
  total_gross_cart_value: string;
  cart_count: number;
  average_cart_value: string | null;
  total_quantity: number;
}

export interface SnapshotRows<T> extends Snapshot {
  items: T[];
}

export interface CategoryPerformance {
  category: string;
  gross_cart_value: string;
  total_quantity: number;
}

export interface ProductPerformance extends CategoryPerformance {
  product_id: number;
  title: string;
}

export interface CustomerPerformance {
  customer_id: number;
  gross_cart_value: string;
  cart_count: number;
}

export interface InventoryProduct {
  product_id: number;
  title: string;
  stock: number;
}
