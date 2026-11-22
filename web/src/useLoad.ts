import { useCallback, useEffect, useEffectEvent, useState } from 'react'
import { describeError } from './api.ts'
import type { ErrorInfo } from './api.ts'

export type Load<T> =
  | { status: 'loading' }
  | { status: 'error'; error: ErrorInfo }
  | { status: 'ready'; data: T }

/** Load once per `key` and again on `reload()`. Late answers of an older load are dropped. */
export function useLoad<T>(loader: () => Promise<T>, key: string | number): [Load<T>, () => void] {
  const [attempt, setAttempt] = useState(0)
  const [answer, setAnswer] = useState<{ token: string; load: Load<T> } | null>(null)
  const token = `${key}:${attempt}`
  const load = useEffectEvent(loader)

  useEffect(() => {
    let current = true
    load().then(
      (data) => current && setAnswer({ token, load: { status: 'ready', data } }),
      (error: unknown) =>
        current && setAnswer({ token, load: { status: 'error', error: describeError(error) } }),
    )
    return () => {
      current = false
    }
  }, [token])

  const reload = useCallback(() => setAttempt((count) => count + 1), [])
  // Until the answer for this key and attempt arrives, the state is "loading".
  return [answer?.token === token ? answer.load : { status: 'loading' }, reload]
}
