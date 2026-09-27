const UNITS = [
  { limit: 60, divisor: 1, unit: "second" },
  { limit: 3600, divisor: 60, unit: "minute" },
  { limit: 86400, divisor: 3600, unit: "hour" },
  { limit: 604800, divisor: 86400, unit: "day" },
  { limit: 2629800, divisor: 604800, unit: "week" },
  { limit: 31557600, divisor: 2629800, unit: "month" },
  { limit: Infinity, divisor: 31557600, unit: "year" },
];

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "always" });

// Formats a date as "now", "5 minutes ago", "in 2 hours", etc.
export function formatRelativeTime(input) {
  if (!input) return "";

  const date = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(date.getTime())) return "";

  const seconds = Math.round((Date.now() - date.getTime()) / 1000);

  if (Math.abs(seconds) < 45) return "now";

  const { divisor, unit } = UNITS.find((u) => Math.abs(seconds) < u.limit);
  const value = Math.round(Math.abs(seconds) / divisor);

  return rtf.format(seconds >= 0 ? -value : value, unit);
}
