import { AntennaForm } from './AntennaForm.tsx'
import { EmptyNotice, ErrorNotice } from './Badges.tsx'
import { antennaText, calModeLabel } from './labels.ts'
import { CsvCard, SampleCard } from './MeasureSources.tsx'
import { CAL_MODES } from './types.ts'
import type { CalMode } from './types.ts'
import type { MeasureState, useAntennas } from './useAppState.ts'

type Antennas = ReturnType<typeof useAntennas>

const CAL_HINT: Record<CalMode, string> = {
  vna: 'vna — LiteVNA 본체에서 교정을 마쳤습니다',
  unknown: 'unknown — 교정 여부를 모릅니다',
}

/** Screen 1: choose or add an antenna, choose the calibration state, then measure. */
export function MeasurePanel({ antennas, measure }: { antennas: Antennas; measure: MeasureState }) {
  return (
    <div className="page">
      <header className="page-head">
        <h1>측정</h1>
        <p>안테나를 고르고, 교정 상태를 확인한 뒤, 측정 데이터를 불러옵니다.</p>
      </header>
      {measure.error !== null && <ErrorNotice error={measure.error} />}
      {measure.busy && (
        <p className="notice" role="status">
          측정하는 중…
        </p>
      )}
      <div className="columns">
        <div className="column column-narrow">
          <AntennaCard antennas={antennas} />
          <CalModeCard measure={measure} />
        </div>
        <div className="column">
          <SampleCard antennaId={antennas.antennaId} measure={measure} />
          <CsvCard antennaId={antennas.antennaId} measure={measure} />
        </div>
      </div>
    </div>
  )
}

function AntennaCard({ antennas }: { antennas: Antennas }) {
  const { antennaId, select, add } = antennas
  return (
    <section className="card">
      <h2>1. 안테나</h2>
      {antennas.antennas.length === 0 ? (
        <EmptyNotice>등록된 안테나가 없습니다. 아래에서 먼저 추가해 주세요.</EmptyNotice>
      ) : (
        <label className="field">
          측정할 안테나
          <select value={antennaId ?? ''} onChange={(event) => select(Number(event.target.value))}>
            {antennas.antennas.map((antenna) => (
              <option key={antenna.id} value={antenna.id}>
                {antenna.name} · {antennaText(antenna)}
              </option>
            ))}
          </select>
        </label>
      )}
      <AntennaForm onAdded={add} />
    </section>
  )
}

function CalModeCard({ measure }: { measure: MeasureState }) {
  return (
    <section className="card">
      <h2>2. 교정 상태</h2>
      {CAL_MODES.map((mode) => (
        <label key={mode} className="option">
          <input
            type="radio"
            name="cal_mode"
            checked={measure.calMode === mode}
            onChange={() => measure.setCalMode(mode)}
          />
          <span>
            <strong>{calModeLabel(mode)}</strong>
            <small>{CAL_HINT[mode]}</small>
          </span>
        </label>
      ))}
    </section>
  )
}
