/**
 * Keeps only the newest of several overlapping requests. Take a ticket before sending and apply
 * the answer only while that ticket is still current: a late answer to an older click is dropped.
 */
export interface Latest {
  next: () => number
  isCurrent: (ticket: number) => boolean
}

export function latestOnly(): Latest {
  let current = 0
  return {
    next: () => ++current,
    isCurrent: (ticket) => ticket === current,
  }
}
