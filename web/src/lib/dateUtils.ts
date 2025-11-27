/**
 * Date formatting utilities
 *
 * All dates are displayed in YYYY-MM-DD HH:MM:SS format across the app.
 */

/**
 * Format a date/timestamp to YYYY-MM-DD HH:MM:SS
 */
export function formatDateTime(timestamp: string | Date): string {
  const date = typeof timestamp === 'string'
    ? new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
    : timestamp;

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * Format a date to YYYY-MM-DD (date only, no time)
 */
export function formatDate(timestamp: string | Date): string {
  const date = typeof timestamp === 'string'
    ? new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
    : timestamp;

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

/**
 * Format a timestamp with relative time for recent events, absolute for older
 * (e.g., "5m ago" or "2024-11-27 14:30:00")
 */
export function formatTimestamp(timestamp: string): string {
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDateTime(timestamp);
}

/**
 * Format an upcoming time with relative time for near future, absolute for far
 * (e.g., "in 15m" or "2024-11-28 09:30:00")
 */
export function formatUpcomingTime(timestamp: string): string {
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `in ${diffMins}m`;
  if (diffHours < 24) return `in ${diffHours}h ${diffMins % 60}m`;

  return formatDateTime(timestamp);
}
