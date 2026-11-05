/**
 * React Query Configuration - Cache Strategy
 */

export const STALE_TIMES = {
  /** Data that rarely changes - system config */
  STATIC: 60 * 60 * 1000, // 1 hour

  /** User content - examples, preferences */
  USER_CONTENT: 5 * 60 * 1000, // 5 minutes

  /** Frequently changing data - notifications */
  REALTIME: 30 * 1000, // 30 seconds

  /** Session data - never stale during session */
  SESSION: Number.POSITIVE_INFINITY,
} as const;

export const GC_TIMES = {
  /** Short cache - temporary data */
  SHORT: 5 * 60 * 1000, // 5 minutes

  /** Medium cache - user data */
  MEDIUM: 15 * 60 * 1000, // 15 minutes

  /** Long cache - static data */
  LONG: 60 * 60 * 1000, // 1 hour
} as const;

/** Default items per page for paginated queries */
export const DEFAULT_PER_PAGE = 10;

/** Polling intervals for processing status */
export const POLLING_INTERVALS = {
  /** Fast polling for active operations */
  FAST: 2000, // 2 seconds

  /** Normal polling */
  NORMAL: 5000, // 5 seconds

  /** Slow polling for less critical data */
  SLOW: 30000, // 30 seconds
} as const;
