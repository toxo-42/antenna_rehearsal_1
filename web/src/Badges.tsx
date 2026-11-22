import type { ErrorInfo } from './api.ts'
import { sourceLabel, sourceSymbol, stageLabel, stageSymbol, stageTone } from './labels.ts'
import type { Source, Stage } from './types.ts'

/** Where the data came from. Always shown next to a measurement. */
export function SourceBadge({ source }: { source: Source }) {
  return (
    <span className={`badge badge-${source}`}>
      <span aria-hidden="true">{sourceSymbol(source)}</span> {sourceLabel(source)}
    </span>
  )
}

/** The state of a card: symbol and word together, the color only supports them. */
export function StageChip({ stage }: { stage: Stage }) {
  return (
    <span className={`chip tone-${stageTone(stage)}`}>
      <span aria-hidden="true">{stageSymbol(stage)}</span> {stageLabel(stage)}
    </span>
  )
}

export function LoadingNotice() {
  return (
    <p className="notice" role="status">
      불러오는 중…
    </p>
  )
}

export function EmptyNotice({ children }: { children: string }) {
  return <p className="notice">{children}</p>
}

/**
 * A failed call. The server's sentence (or the server-down sentence) is shown as it is.
 * "Server off" gets its own look and a hint on how to start the server again.
 */
export function ErrorNotice({ error, onRetry }: { error: ErrorInfo; onRetry?: () => void }) {
  return (
    <div className={`notice notice-error${error.serverDown ? ' notice-down' : ''}`} role="alert">
      <div>
        {error.serverDown && <strong className="notice-title">서버 꺼짐</strong>}
        <p>
          <span aria-hidden="true">×</span> {error.message}
        </p>
        {error.serverDown && (
          <small>터미널에서 앱 서버를 다시 켠 뒤 "다시 시도"를 눌러 주세요.</small>
        )}
      </div>
      {onRetry && (
        <button type="button" className="button-secondary" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  )
}
