export function formatPercent(value: number) {
  return new Intl.NumberFormat("en", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatSignedPercent(value: number) {
  const formatted = formatPercent(Math.abs(value));
  return `${value >= 0 ? "+" : "-"}${formatted}`;
}
