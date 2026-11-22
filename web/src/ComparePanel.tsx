import { useState } from 'react'
import type { ReactNode } from 'react'
import { compareMeasurements, getMeasurement } from './api.ts'
import { ErrorNotice, LoadingNotice, SourceBadge, StageChip } from './Badges.tsx'
import { signedText, sourceLabel, timeText } from './labels.ts'
import { OverlayChart } from './OverlayChart.tsx'
import { inMeasurementOrder, isTruncated, orderText } from './trend.ts'
import type { Comparison, Measurement, MeasurementRow } from './types.ts'
import { useLoad } from './useLoad.ts'

type Pair = { before: number; after: number }

/** The last two measurements by default, or the same one twice when there is only one. */
function defaultPair(ordered: MeasurementRow[]): Pair {
  const last = ordered[ordered.length - 1].id
  return { before: ordered[ordered.length - 2]?.id ?? last, after: last }
}

/** Pick two measurements of this antenna; the server decides what changed. */
export function ComparePanel({ rows }: { rows: MeasurementRow[] }) {
  const ordered = inMeasurementOrder(rows)
  const [pair, setPair] = useState<Pair>(() => defaultPair(ordered))
  const pick = (side: keyof Pair) => (event: { target: { value: string } }) =>
    setPair({ ...pair, [side]: Number(event.target.value) })
  return (
    <section className="card">
      <h2>전후 비교</h2>
      <div className="field-row">
        <MeasurementSelect label="이전 측정" rows={ordered} value={pair.before} onChange={pick('before')} />
        <MeasurementSelect label="이후 측정" rows={ordered} value={pair.after} onChange={pick('after')} />
      </div>
      <CompareResult key={`${pair.before}:${pair.after}`} pair={pair} />
    </section>
  )
}

function MeasurementSelect(props: {
  label: string
  rows: MeasurementRow[]
  value: number
  onChange: (event: { target: { value: string } }) => void
}) {
  const truncated = isTruncated(props.rows.length)
  return (
    <label className="field">
      {props.label}
      <select value={props.value} onChange={props.onChange}>
        {props.rows.map((row, index) => (
          <option key={row.id} value={row.id}>
            {orderText(index + 1, truncated)} · {sourceLabel(row.source)} · {timeText(row.measured_at)} ·{' '}
            {row.change_note || '변경 기록 없음'}
          </option>
        ))}
      </select>
    </label>
  )
}

type Loaded = { comparison: Comparison; before: Measurement; after: Measurement }

async function loadPair(pair: Pair): Promise<Loaded> {
  const [comparison, before, after] = await Promise.all([
    compareMeasurements(pair.before, pair.after),
    getMeasurement(pair.before),
    getMeasurement(pair.after),
  ])
  return { comparison, before, after }
}

function CompareResult({ pair }: { pair: Pair }) {
  const [loaded, reload] = useLoad(() => loadPair(pair), `${pair.before}:${pair.after}`)
  if (loaded.status === 'loading') return <LoadingNotice />
  if (loaded.status === 'error') return <ErrorNotice error={loaded.error} onRetry={reload} />
  const { comparison: c, before, after } = loaded.data
  return (
    <>
      <p className="meta">
        이전 <SourceBadge source={before.source} /> → 이후 <SourceBadge source={after.source} />
      </p>
      <h3 className="compare-verdict">{c.verdict}</h3>
      {c.reasons.length > 0 && (
        <ul>
          {c.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <CompareTable c={c} />
      <p>{c.summary}</p>
      <p className="muted">
        {c.step_mhz !== null &&
          `공진점 주변 측정 간격 ${c.step_mhz.toFixed(2)} MHz보다 작은 거리 변화는 차이로 보지 않습니다. `}
        이 비교는 무엇을 바꾼 뒤 어떻게 됐는지만 보여 주며, 원인을 판단하지 않습니다.
      </p>
      <OverlayChart before={before} after={after} />
    </>
  )
}

function CompareTable({ c }: { c: Comparison }) {
  const distance =
    c.distance_before_mhz === null || c.distance_after_mhz === null
      ? '—'
      : `${c.distance_before_mhz.toFixed(2)} → ${c.distance_after_mhz.toFixed(2)} MHz`
  const rows: [string, ReactNode][] = [
    ['공진 이동', signedText(c.shift_mhz, 'MHz')],
    ['목표와의 거리', distance],
    ['거리 변화', signedText(c.distance_change_mhz, 'MHz')],
    ['공진점 S11 변화', signedText(c.s11_change_db, 'dB')],
    ['대역폭 변화', signedText(c.bandwidth_change_pct, '%p')],
    ['단계', <><StageChip stage={c.stage.before} /> → <StageChip stage={c.stage.after} /></>],
    ['바꾼 것 (이후 측정의 기록)', c.change_note || '기록 없음'],
  ]
  return (
    <table>
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
