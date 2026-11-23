import { useState } from 'react'
import { listMeasurements } from './api.ts'
import { AntennaForm } from './AntennaForm.tsx'
import { EmptyNotice, ErrorNotice, LoadingNotice, StageChip } from './Badges.tsx'
import { antennaText } from './labels.ts'
import { antennaSummary, countText } from './summary.ts'
import type { Antenna } from './types.ts'
import { useLoad } from './useLoad.ts'

interface SidebarProps {
  antennas: Antenna[]
  antennaId: number | null
  onSelect: (id: number) => void
  /** Left out in demo mode, where the server refuses every write. */
  onAdded?: (antenna: Antenna) => void
  /** True while a measurement runs: the antenna it belongs to must not change under it. */
  locked: boolean
  /** Changes after each measurement, rename or delete so the summary is loaded again. */
  refreshKey: string
}

/** Always on the left: which antenna every screen is about, and its latest result. */
export function AntennaSidebar(props: SidebarProps) {
  const { antennas, antennaId } = props
  const chosen = antennas.find((item) => item.id === antennaId) ?? null
  return (
    <aside className="sidebar" aria-label="안테나">
      <h2 className="sidebar-title">안테나</h2>
      {antennas.length === 0 && <EmptyNotice>등록된 안테나가 없습니다.</EmptyNotice>}
      <ul className="antenna-list">
        {antennas.map((antenna) => (
          <li key={antenna.id}>
            <button
              type="button"
              className="antenna-item"
              aria-current={antenna.id === antennaId ? 'true' : undefined}
              disabled={props.locked}
              onClick={() => props.onSelect(antenna.id)}
            >
              <strong>{antenna.name}</strong>
              <small>{antennaText(antenna)}</small>
            </button>
          </li>
        ))}
      </ul>
      {props.onAdded !== undefined && <AddAntenna onAdded={props.onAdded} />}
      {chosen !== null && <SummaryBox key={`${chosen.id}:${props.refreshKey}`} antenna={chosen} />}
    </aside>
  )
}

/** The add form stays folded until asked for, and folds again once the antenna is added. */
function AddAntenna({ onAdded }: { onAdded: (antenna: Antenna) => void }) {
  const [open, setOpen] = useState(false)
  const added = (antenna: Antenna) => {
    setOpen(false)
    onAdded(antenna)
  }
  return (
    <>
      <button type="button" className="button-dashed" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? '추가 닫기' : '+ 안테나 추가'}
      </button>
      {open && <AntennaForm onAdded={added} />}
    </>
  )
}

function SummaryBox({ antenna }: { antenna: Antenna }) {
  const [rows, reload] = useLoad(() => listMeasurements(antenna.id), antenna.id)
  if (rows.status === 'loading') return <LoadingNotice />
  if (rows.status === 'error') return <ErrorNotice error={rows.error} onRetry={reload} />
  const summary = antennaSummary(rows.data)
  const resonance = summary.latestResonanceMhz
  return (
    <dl className="summary">
      <dt className="summary-title">{antenna.name} 요약</dt>
      <div>
        <dt>측정 횟수</dt>
        <dd>{countText(summary.count)}</dd>
      </div>
      <div>
        <dt>최근 공진</dt>
        <dd>{resonance === null ? '—' : `${resonance.toFixed(2)} MHz`}</dd>
      </div>
      <div>
        <dt>최근 판정</dt>
        <dd>{summary.latestStage === null ? '—' : <StageChip stage={summary.latestStage} />}</dd>
      </div>
    </dl>
  )
}
