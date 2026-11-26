import type { ReactNode } from 'react';

interface Column<T> {
  label: string;
  numeric?: boolean;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  label: string;
  empty: string;
  rows: T[];
  rowKey: (row: T) => number;
  columns: Column<T>[];
}

export function DataTable<T>({ label, empty, rows, rowKey, columns }: DataTableProps<T>) {
  if (!rows.length) return <p className="panel-message">{empty}</p>;
  return <div className="table-wrap">
    <table>
      <caption className="sr-only">{label}</caption>
      <thead><tr>{columns.map(column => <th key={column.label} scope="col"
        className={column.numeric ? 'numeric' : undefined}>{column.label}</th>)}</tr></thead>
      <tbody>{rows.map(row => <tr key={rowKey(row)}>{columns.map((column, index) =>
        index === 0
          ? <th key={column.label} scope="row">{column.render(row)}</th>
          : <td key={column.label} className={column.numeric ? 'numeric' : undefined}>{column.render(row)}</td>,
      )}</tr>)}</tbody>
    </table>
  </div>;
}
