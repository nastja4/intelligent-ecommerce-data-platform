const numberFormat = new Intl.NumberFormat('en-US');
const snapshotFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  second: '2-digit', timeZone: 'UTC', timeZoneName: 'short', hourCycle: 'h23',
});

export const formatCount = (count: number) => numberFormat.format(count);

export function formatAmount(amount: string | null): string {
  if (amount === null) return '—';
  const [whole, fraction] = amount.split('.');
  return `${numberFormat.format(BigInt(whole))}.${fraction}`;
}

export const formatSnapshot = (timestamp: string) => snapshotFormat.format(new Date(timestamp));

export function categoryLabel(category: string): string {
  return category.replace(/[-_]+/g, ' ').replace(/\b\p{Ll}/gu, char => char.toUpperCase());
}

export function parseBoundedInteger(value: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(value)) return null;
  const number = Number(value);
  return Number.isSafeInteger(number) && number >= min && number <= max ? number : null;
}
