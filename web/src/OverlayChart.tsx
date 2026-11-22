import type { PlotBox, Point } from './chart.ts'
import { sourceLabel } from './labels.ts'
import { overlayModel } from './overlay.ts'
import type { Measurement } from './types.ts'

const WIDTH = 600
const HEIGHT = 330
const BOX: PlotBox = { left: 52, top: 14, width: 524, height: 260 }
const BOTTOM = BOX.top + BOX.height

function line(points: Point[]): string {
  return points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
}

/** Both sweeps on one scale: before dashed, after solid, with the target line. */
export function OverlayChart({ before, after }: { before: Measurement; after: Measurement }) {
  const target = after.antenna.target_mhz
  const model = overlayModel(before.sweep, after.sweep, target, BOX)
  const { scale } = model
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="두 스윕 겹쳐 보기">
        <rect className="chart-area" x={BOX.left} y={BOX.top} width={BOX.width} height={BOX.height} />
        <text className="chart-tick" x={BOX.left - 8} y={BOX.top + 4} textAnchor="end">0</text>
        <text className="chart-tick" x={BOX.left - 8} y={BOTTOM} textAnchor="end">
          {scale.dbBottom.toFixed(0)}
        </text>
        {model.freqTicks.map((tick) => (
          <text key={tick.label} className="chart-tick" x={tick.x} y={BOTTOM + 20} textAnchor="middle">
            {tick.label}
          </text>
        ))}
        <text className="chart-unit" x={BOX.left + BOX.width} y={BOTTOM + 40} textAnchor="end">MHz</text>
        <line className="chart-target" x1={model.targetX} x2={model.targetX} y1={BOX.top} y2={BOTTOM} />
        <polyline className="chart-curve chart-curve-before" points={line(model.before)} />
        <polyline className="chart-curve" points={line(model.after)} />
      </svg>
      <figcaption className="chart-legend">
        <span>┄ 이전 ({before.id}번 · {sourceLabel(before.source)})</span>
        <span>━ 이후 ({after.id}번 · {sourceLabel(after.source)})</span>
        <span>┆ 목표 {target} MHz</span>
      </figcaption>
    </figure>
  )
}
