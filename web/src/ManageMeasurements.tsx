import { HISTORY_LIMIT, deleteMeasurement, listMeasurements } from './api.ts'
import { EmptyNotice, ErrorNotice, LoadingNotice, SourceBadge, StageChip } from './Badges.tsx'
import { timeText } from './labels.ts'
import { measurementDeleteQuestion } from './manage.ts'
import type { Act } from './ManagePanel.tsx'
import { isTruncated } from './trend.ts'
import type { Antenna, MeasurementRow } from './types.ts'
import { useLoad } from './useLoad.ts'

/** The measurements of the antenna chosen in the sidebar, each with a delete button. */
export function ManageMeasurements({ antenna, act }: { antenna: Antenna; act: Act }) {
  const [rows, reload] = useLoad(() => listMeasurements(antenna.id), antenna.id)
  const remove = (row: MeasurementRow) => {
    if (!window.confirm(measurementDeleteQuestion(row.measured_at))) return
    void act(async () => {
      await deleteMeasurement(row.id)
    })
  }
  return (
    <section className="card card-table">
      <h2 className="table-title">측정 기록 · {antenna.name}</h2>
      {rows.status === 'loading' && <LoadingNotice />}
      {rows.status === 'error' && <ErrorNotice error={rows.error} onRetry={reload} />}
      {rows.status === 'ready' && rows.data.length === 0 && (
        <EmptyNotice>이 안테나의 측정이 아직 없습니다.</EmptyNotice>
      )}
      {rows.status === 'ready' && rows.data.length > 0 && <MeasurementTable rows={rows.data} onDelete={remove} />}
    </section>
  )
}

function MeasurementTable(props: { rows: MeasurementRow[]; onDelete: (row: MeasurementRow) => void }) {
  return (
    <>
      <table>
        <thead>
          <tr>
            <th scope="col">시각</th>
            <th scope="col">출처</th>
            <th scope="col">판정</th>
            <th scope="col">공진 주파수</th>
            <th scope="col">바꾼 것</th>
            <th scope="col">삭제</th>
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row) => (
            <tr key={row.id}>
              <td>{timeText(row.measured_at)}</td>
              <td><SourceBadge source={row.source} /></td>
              <td><StageChip stage={row.stage} /></td>
              <td>{row.resonance_mhz === null ? '—' : `${row.resonance_mhz.toFixed(2)} MHz`}</td>
              <td>{row.change_note || '—'}</td>
              <td>
                <button type="button" className="button-danger" onClick={() => props.onDelete(row)}>
                  삭제
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {isTruncated(props.rows.length) && <p className="muted table-foot">최근 {HISTORY_LIMIT}건만 보여 줍니다.</p>}
    </>
  )
}
