import { useState } from 'react'
import { listSamples, measureSample, uploadCsv } from './api.ts'
import { EmptyNotice, ErrorNotice, LoadingNotice, SourceBadge } from './Badges.tsx'
import { antennaText } from './labels.ts'
import type { Sample } from './types.ts'
import type { MeasureState } from './useAppState.ts'
import { useLoad } from './useLoad.ts'

interface SourceProps {
  antennaId: number | null
  measure: MeasureState
}

/** Measure a synthetic sample. The sample's kind and target are a hint; the chosen antenna judges. */
export function SampleCard({ antennaId, measure }: SourceProps) {
  const [samples, reload] = useLoad(() => listSamples(), 'samples')
  const [sample, setSample] = useState<string | null>(null)
  const start = () =>
    antennaId !== null &&
    sample !== null &&
    measure.run(() => measureSample(antennaId, sample, measure.calMode, measure.changeNote))
  return (
    <section className="card">
      <h2>
        3-가. 합성 샘플로 측정 <SourceBadge source="synthetic" />
      </h2>
      <p className="muted">샘플의 종류와 목표 주파수는 참고용입니다. 판정은 위에서 선택한 안테나로 합니다.</p>
      {samples.status === 'loading' && <LoadingNotice />}
      {samples.status === 'error' && <ErrorNotice error={samples.error} onRetry={reload} />}
      {samples.status === 'ready' && <SampleList samples={samples.data} chosen={sample} onChoose={setSample} />}
      <button type="button" disabled={measure.busy || antennaId === null || sample === null} onClick={start}>
        선택한 샘플로 측정
      </button>
    </section>
  )
}

function SampleList(props: { samples: Sample[]; chosen: string | null; onChoose: (name: string) => void }) {
  if (props.samples.length === 0) return <EmptyNotice>합성 샘플이 없습니다.</EmptyNotice>
  return (
    <div className="sample-list">
      {props.samples.map((item) => (
        <label key={item.name} className="option">
          <input
            type="radio"
            name="sample"
            checked={props.chosen === item.name}
            onChange={() => props.onChoose(item.name)}
          />
          <span>
            <strong>{item.name}</strong>
            <small>{antennaText(item)}</small>
          </span>
        </label>
      ))}
    </div>
  )
}

/** Measure an uploaded CSV file. */
export function CsvCard({ antennaId, measure }: SourceProps) {
  const [file, setFile] = useState<File | null>(null)
  const start = () =>
    antennaId !== null &&
    file !== null &&
    measure.run(() => uploadCsv(antennaId, file, measure.calMode, measure.changeNote))
  return (
    <section className="card">
      <h2>
        3-나. CSV 파일로 측정 <SourceBadge source="csv" />
      </h2>
      <label className="field file-field">
        CSV 파일 (UTF-8, 2 MB 이하)
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <button type="button" disabled={measure.busy || antennaId === null || file === null} onClick={start}>
        업로드하고 측정
      </button>
    </section>
  )
}
