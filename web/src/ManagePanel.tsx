import { useState } from 'react'
import { deleteAntenna, describeError, getOverview, renameAntenna } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { EmptyNotice, ErrorNotice, LoadingNotice, SourceBadge, StageChip } from './Badges.tsx'
import { antennaText, timeText } from './labels.ts'
import { antennaDeleteQuestion, lastSource } from './manage.ts'
import { ManageMeasurements } from './ManageMeasurements.tsx'
import type { AntennaOverview } from './types.ts'
import type { useAntennas } from './useAppState.ts'
import { useLoad } from './useLoad.ts'

/** Runs one change; a failure is shown above the tables in the server's sentence. */
export type Act = (change: () => Promise<void>) => Promise<void>

interface ManageProps {
  antennas: ReturnType<typeof useAntennas>
  /** After anything was renamed or deleted: the card and the sidebar summary may be stale. */
  onChanged: () => void
}

/** Screen 4: what is stored per antenna, renaming, and deleting (asked first, never undone). */
export function ManagePanel({ antennas, onChanged }: ManageProps) {
  const [error, setError] = useState<ErrorInfo | null>(null)
  const [version, setVersion] = useState(0)
  const act: Act = async (change) => {
    setError(null)
    try {
      await change()
      onChanged()
    } catch (failure) {
      setError(describeError(failure))
    }
    setVersion((count) => count + 1) // load again either way: the screen shows what is stored
  }
  const chosen = antennas.antennas.find((item) => item.id === antennas.antennaId) ?? null
  return (
    <div className="page">
      <header className="page-head page-head-row">
        <h1>관리</h1>
        <span>이름 수정과 삭제. 삭제한 것은 되돌릴 수 없습니다.</span>
      </header>
      {error !== null && <ErrorNotice error={error} />}
      <AntennaTable key={version} antennas={antennas} act={act} />
      {chosen !== null && <ManageMeasurements key={`${chosen.id}:${version}`} antenna={chosen} act={act} />}
    </div>
  )
}

function AntennaTable({ antennas, act }: { antennas: ManageProps['antennas']; act: Act }) {
  const [rows, reload] = useLoad(getOverview, 'overview')
  if (rows.status === 'loading') return <LoadingNotice />
  if (rows.status === 'error') return <ErrorNotice error={rows.error} onRetry={reload} />
  if (rows.data.length === 0) return <EmptyNotice>등록된 안테나가 없습니다. 왼쪽에서 먼저 추가해 주세요.</EmptyNotice>
  // After either change the sidebar list is loaded again from the server.
  const rename = (id: number, name: string) =>
    act(async () => {
      await renameAntenna(id, name)
      await antennas.refresh()
    })
  const remove = (row: AntennaOverview) => {
    if (!window.confirm(antennaDeleteQuestion(row.name, row.measurement_count))) return
    void act(async () => {
      await deleteAntenna(row.id)
      await antennas.refresh()
    })
  }
  return (
    <section className="card card-table">
      <table>
        <thead>
          <tr>
            <th scope="col">안테나</th>
            <th scope="col">측정</th>
            <th scope="col">최근 측정</th>
            <th scope="col">최근 판정</th>
            <th scope="col">이름 수정 · 삭제</th>
          </tr>
        </thead>
        <tbody>
          {rows.data.map((row) => (
            <AntennaRow key={row.id} row={row} onRename={rename} onDelete={() => remove(row)} />
          ))}
        </tbody>
      </table>
    </section>
  )
}

interface RowProps {
  row: AntennaOverview
  onRename: (id: number, name: string) => Promise<void>
  onDelete: () => void
}

function AntennaRow({ row, onRename, onDelete }: RowProps) {
  const [name, setName] = useState<string | null>(null) // null: not being edited
  const save = () => name !== null && onRename(row.id, name)
  const source = lastSource(row)
  return (
    <tr>
      <td>
        {name === null ? <strong>{row.name}</strong> : <NameBox name={name} onChange={setName} />}
        <small>{antennaText(row)}</small>
      </td>
      <td>{row.measurement_count}건</td>
      <td>
        {row.last_measured_at === null ? '—' : timeText(row.last_measured_at)}{' '}
        {source !== null && <SourceBadge source={source} />}
      </td>
      <td>{row.last_stage === null ? '—' : <StageChip stage={row.last_stage} />}</td>
      <td className="row-actions">
        {name === null ? (
          <button type="button" className="button-secondary" onClick={() => setName(row.name)}>
            이름 수정
          </button>
        ) : (
          <button type="button" onClick={save}>
            저장
          </button>
        )}
        <button type="button" className="button-danger" onClick={onDelete}>
          삭제
        </button>
      </td>
    </tr>
  )
}

function NameBox({ name, onChange }: { name: string; onChange: (name: string) => void }) {
  return (
    <label className="field">
      새 이름
      <input type="text" value={name} autoFocus onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}
