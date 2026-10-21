/** Display formatting only. These functions do not change stored finance values. */

function formatFixed(value: number, digits: number): string {
  const text = value.toFixed(digits)
  return Number(text) === 0 ? (0).toFixed(digits) : text
}

export function formatPercent(value: number): string {
  return `${formatFixed(value * 100, 2)}%`
}

export function formatPercentile(value: number): string {
  return formatFixed(value, 1)
}

export function formatPrice(value: number): string {
  return formatFixed(value, 2)
}

export function formatCount(value: number): string {
  return String(Math.trunc(value))
}
