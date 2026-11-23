import { MATCH_LINE_DB, chartModel, yOf } from './chart.ts'
import type { ChartModel, PlotBox } from './chart.ts'
import type { Measurement } from './types.ts'

const WIDTH = 600
// Taller than wide enough to stand next to the verdict card at the same height.
const HEIGHT = 480
const BOX: PlotBox = { left: 52, top: 14, width: 524, height: 410 }
const RIGHT = BOX.left + BOX.width
const BOTTOM = BOX.top + BOX.height

/** S11 over frequency. The target and the resonance come from the response, never from the sweep. */
export function S11Chart({ measurement }: { measurement: Measurement }) {
  const model = chartModel(measurement, BOX)
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="S11 그래프">
        <Axes model={model} />
        <TargetLine model={model} targetMhz={measurement.antenna.target_mhz} />
        <polyline
          className="chart-curve"
          points={model.curve.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')}
        />
        <ResonanceMark model={model} resonanceMhz={measurement.resonance_mhz} />
      </svg>
      <figcaption className="chart-legend">
        <span>━ S11</span>
        <span>┆ 목표 주파수</span>
        {model.marker !== null && <span>● 공진</span>}
        <span>┄ {MATCH_LINE_DB} dB 기준</span>
      </figcaption>
    </figure>
  )
}

function Axes({ model }: { model: ChartModel }) {
  return (
    <g>
      <rect className="chart-area" x={BOX.left} y={BOX.top} width={BOX.width} height={BOX.height} />
      {model.dbTicks.map((db) => (
        <g key={db}>
          <line className="chart-grid" x1={BOX.left} x2={RIGHT} y1={yOf(db, model.scale)} y2={yOf(db, model.scale)} />
          <text className="chart-tick" x={BOX.left - 8} y={yOf(db, model.scale) + 4} textAnchor="end">
            {db}
          </text>
        </g>
      ))}
      {model.freqTicks.map((tick) => (
        <text key={tick.label} className="chart-tick" x={tick.x} y={BOTTOM + 20} textAnchor="middle">
          {tick.label}
        </text>
      ))}
      <text className="chart-unit" x={6} y={BOX.top + 4}>dB</text>
      <text className="chart-unit" x={RIGHT} y={BOTTOM + 40} textAnchor="end">MHz</text>
      <line className="chart-match" x1={BOX.left} x2={RIGHT} y1={model.matchY} y2={model.matchY} />
      <text className="chart-match-label" x={RIGHT - 6} y={model.matchY - 6} textAnchor="end">
        {MATCH_LINE_DB} dB
      </text>
    </g>
  )
}

function TargetLine({ model, targetMhz }: { model: ChartModel; targetMhz: number }) {
  const onLeft = model.targetX > BOX.left + BOX.width * 0.7
  return (
    <g>
      <line className="chart-target" x1={model.targetX} x2={model.targetX} y1={BOX.top} y2={BOTTOM} />
      <text
        className="chart-target-label"
        x={onLeft ? model.targetX - 6 : model.targetX + 6}
        y={BOTTOM - 8}
        textAnchor={onLeft ? 'end' : 'start'}
      >
        목표 {targetMhz} MHz
      </text>
    </g>
  )
}

function ResonanceMark({ model, resonanceMhz }: { model: ChartModel; resonanceMhz: number | null }) {
  const { marker } = model
  if (marker === null || resonanceMhz === null) return null
  const onRight = marker.x < BOX.left + BOX.width * 0.3
  return (
    <g>
      <circle className="chart-marker" cx={marker.x} cy={marker.y} r={6} />
      <text
        className="chart-marker-label"
        x={onRight ? marker.x + 12 : marker.x - 12}
        y={marker.y + 4}
        textAnchor={onRight ? 'start' : 'end'}
      >
        공진 {resonanceMhz.toFixed(2)} MHz
      </text>
    </g>
  )
}
