import { useState } from 'react'
import { describeError, getMeasurement, listMeasurements } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { EmptyNotice, ErrorNotice, LoadingNotice, SourceBadge, StageChip } from './Badges.tsx'
import { antennaText, timeText } from './labels.ts'
import { latestOnly } from './latest.ts'
import type { Measurement, MeasurementRow } from './types.ts'
import type { useAntennas } from './useAppState.ts'
import { useLoad } from './useLoad.ts'
import { VerdictCard } from './VerdictCard.tsx'

type OnOpen = (measurement: Measurement) => void

/** Screen 3: the measurements of one antenna, and the card of the one that is clicked. */
export function HistoryPanel(props: { antennas: ReturnType<typeof useAntennas>; onOpen: OnOpen }) {
  const { antennas, antennaId, select } = props.antennas
  return (
    <div className="page">
      <header className="page-head page-head-row">
        <h1>이력</h1>
        {antennas.length > 0 && (
          <select aria-label="안테나 선택" value={antennaId ?? ''} onChange={(event) => select(Number(event.target.value))}>
            {antennas.map((antenna) => (
              <option key={antenna.id} value={antenna.id}>
                {antenna.name} · {antennaText(antenna)}
              </option>
            ))}
          </select>
        )}
      </header>
      {antennaId === null ? (
        <EmptyNotice>등록된 안테나가 없습니다. ① 측정에서 먼저 추가해 주세요.</EmptyNotice>
      ) : (
        <HistoryList key={antennaId} antennaId={antennaId} onOpen={props.onOpen} />
      )}
    </div>
  )
}

type Picked = { id: number; measurement: Measurement | null; error: ErrorInfo | null }

function HistoryList({ antennaId, onOpen }: { antennaId: number; onOpen: OnOpen }) {
  const [rows, reload] = useLoad(() => listMeasurements(antennaId), antennaId)
  const [picked, setPicked] = useState<Picked | null>(null)
  const [latest] = useState(latestOnly)

  async function open(id: number) {
    const ticket = latest.next()
    setPicked({ id, measurement: null, error: null })
    try {
      const measurement = await getMeasurement(id)
      if (latest.isCurrent(ticket)) setPicked({ id, measurement, error: null })
    } catch (failure) {
      if (latest.isCurrent(ticket)) setPicked({ id, measurement: null, error: describeError(failure) })
    }
  }

  if (rows.status === 'loading') return <LoadingNotice />
  if (rows.status === 'error') return <ErrorNotice error={rows.error} onRetry={reload} />
  if (rows.data.length === 0) {
    return <EmptyNotice>이 안테나의 측정이 아직 없습니다. ① 측정에서 시작해 주세요.</EmptyNotice>
  }
  return (
    <div className="columns">
      <HistoryTable rows={rows.data} selectedId={picked?.id ?? null} onPick={open} />
      <div className="column column-narrow">
        <PickedCard picked={picked} onOpen={onOpen} />
      </div>
    </div>
  )
}

function HistoryTable(props: { rows: MeasurementRow[]; selectedId: number | null; onPick: (id: number) => void }) {
  return (
    <section className="card card-table column">
      <table>
        <thead>
          <tr>
            <th scope="col">시각</th>
            <th scope="col">출처</th>
            <th scope="col">단계</th>
            <th scope="col">공진 주파수</th>
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row) => (
            <tr key={row.id} className={row.id === props.selectedId ? 'row-selected' : undefined}>
              <td>
                <button type="button" className="link" onClick={() => props.onPick(row.id)}>
                  {timeText(row.measured_at)}
                </button>
              </td>
              <td><SourceBadge source={row.source} /></td>
              <td><StageChip stage={row.stage} /></td>
              <td>{row.resonance_mhz === null ? '—' : `${row.resonance_mhz.toFixed(2)} MHz`}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted table-foot">시각을 누르면 오른쪽에 그 측정의 판정 카드가 보입니다.</p>
    </section>
  )
}

function PickedCard({ picked, onOpen }: { picked: Picked | null; onOpen: OnOpen }) {
  if (picked === null) return <EmptyNotice>목록에서 측정 한 건을 골라 주세요.</EmptyNotice>
  if (picked.error !== null) return <ErrorNotice error={picked.error} />
  const { measurement } = picked
  if (measurement === null) return <LoadingNotice />
  return (
    <>
      <p className="meta">
        <SourceBadge source={measurement.source} /> {timeText(measurement.measured_at)}
        <button type="button" className="button-secondary" onClick={() => onOpen(measurement)}>
          그래프와 함께 보기 →
        </button>
      </p>
      <VerdictCard key={measurement.id} card={measurement.card} />
    </>
  )
}
