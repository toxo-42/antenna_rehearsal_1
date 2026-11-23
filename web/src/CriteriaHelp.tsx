import { useState } from 'react'
import { listCriteria } from './api.ts'
import { ErrorNotice, LoadingNotice } from './Badges.tsx'
import { criteriaByTone } from './criteria.ts'
import type { Kind } from './types.ts'
import { useLoad } from './useLoad.ts'

/** "What do 양호, 주의, 문제 mean?" next to the chip. Loaded only when opened. */
export function CriteriaHelp({ kind }: { kind: Kind }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="criteria">
      <button type="button" className="link" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? '판정 기준 닫기' : '판정 기준 보기'}
      </button>
      {open && <CriteriaList kind={kind} />}
    </div>
  )
}

function CriteriaList({ kind }: { kind: Kind }) {
  const [criteria, reload] = useLoad(() => listCriteria(kind), `criteria:${kind}`)
  if (criteria.status === 'loading') return <LoadingNotice />
  if (criteria.status === 'error') return <ErrorNotice error={criteria.error} onRetry={reload} />
  return (
    <dl className="criteria-list">
      {criteriaByTone(criteria.data).map((group) => (
        <div key={group.tone}>
          <dt>
            <span className={`chip tone-${group.tone}`}>
              <span aria-hidden="true">{group.symbol}</span> {group.label}
            </span>
          </dt>
          {group.texts.map((text) => (
            <dd key={text}>{text}</dd>
          ))}
        </div>
      ))}
    </dl>
  )
}
