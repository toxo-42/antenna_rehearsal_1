import type { ReactNode } from 'react'
import { EmptyNotice, ErrorNotice } from './Badges.tsx'
import { ChangeNoteFields } from './ChangeNoteFields.tsx'
import { antennaText, calModeLabel } from './labels.ts'
import { LengthField } from './LengthField.tsx'
import { methodLabel, visibleMethods } from './measureMethod.ts'
import { CsvMeasure, SampleMeasure } from './MeasureSources.tsx'
import { CAL_MODES } from './types.ts'
import { UsbMeasure } from './UsbMeasure.tsx'
import type { Antenna, CalMode } from './types.ts'
import type { MeasureState } from './useAppState.ts'

const CAL_HINT: Record<CalMode, string> = {
  vna: 'VNA 본체에서 cal을 마쳤습니다',
  unknown: '교정하지 않았거나 모릅니다',
}

type PanelProps = { antenna: Antenna | null; measure: MeasureState }

/** Screen 1: for the antenna chosen in the sidebar, note what changed, then measure. */
export function MeasurePanel({ antenna, measure }: PanelProps) {
  const saved = measure.changeNote === '' ? '없음' : measure.changeNote
  return (
    <div className="page">
      <header className="page-head page-head-row">
        <h1>측정</h1>
        {antenna !== null && (
          <span>
            {antenna.name} · {antennaText(antenna)}
          </span>
        )}
      </header>
      {antenna === null && <EmptyNotice>왼쪽에서 측정할 안테나를 먼저 추가해 주세요.</EmptyNotice>}
      {measure.error !== null && <ErrorNotice error={measure.error} />}
      {measure.busy && (
        <p className="notice" role="status">
          측정하는 중…
        </p>
      )}
      <section className="card form-rows">
        {antenna?.kind === 'monopole' && (
          <FormRow title="도체 길이" hint="선택. 급전점에서 도체 끝까지 잰 길이입니다. 비워 두면 목표 주파수만으로 판정합니다.">
            <LengthField measure={measure} />
          </FormRow>
        )}
        <FormRow title="Calibration" hint="VNA 교정">
          <CalModeOptions measure={measure} />
        </FormRow>
        <FormRow title="지난 측정 뒤 바꾼 것" hint={`저장될 기록: ${saved}`}>
          <ChangeNoteFields measure={measure} />
        </FormRow>
        <FormRow title="측정 방법" hint="하나를 골라 측정합니다">
          <MethodPicker measure={measure} />
          <MethodBody antenna={antenna} measure={measure} />
        </FormRow>
      </section>
    </div>
  )
}

/** One row of the measure form: what it is on the left, the controls on the right. */
function FormRow(props: { title: string; hint: string; children: ReactNode }) {
  return (
    <div className="form-row">
      <div>
        <h2>{props.title}</h2>
        <small>{props.hint}</small>
      </div>
      <div className="field-stack">{props.children}</div>
    </div>
  )
}

function CalModeOptions({ measure }: { measure: MeasureState }) {
  return (
    <div className="field-row">
      {CAL_MODES.map((mode) => (
        <label key={mode} className="option">
          <input
            type="radio"
            name="cal_mode"
            checked={measure.calMode === mode}
            disabled={measure.busy}
            onChange={() => measure.setCalMode(mode)}
          />
          <span>
            <strong>{calModeLabel(mode)}</strong>
            <small>{CAL_HINT[mode]}</small>
          </span>
        </label>
      ))}
    </div>
  )
}

/** VNA or CSV. Synthetic samples join the choice only after "practice without a VNA". */
function MethodPicker({ measure }: { measure: MeasureState }) {
  return (
    <div className="row-between">
      <div className="segmented" role="group" aria-label="측정 방법">
        {visibleMethods(measure.practice).map((method) => (
          <button
            key={method}
            type="button"
            aria-pressed={measure.method === method}
            disabled={measure.busy}
            onClick={() => measure.setMethod(method)}
          >
            {methodLabel(method)}
          </button>
        ))}
      </div>
      {!measure.practice && (
        <button type="button" className="link" disabled={measure.busy} onClick={measure.startPractice}>
          장비 없이 연습하기 (합성 샘플)
        </button>
      )}
    </div>
  )
}

function MethodBody({ antenna, measure }: PanelProps) {
  const antennaId = antenna?.id ?? null
  if (measure.method === 'csv') return <CsvMeasure antennaId={antennaId} measure={measure} />
  if (measure.method === 'sample') return <SampleMeasure antennaId={antennaId} measure={measure} />
  return <UsbMeasure antenna={antenna} measure={measure} />
}
