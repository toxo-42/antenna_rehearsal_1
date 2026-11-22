import type { PlotBox } from './chart.ts'
import { sourceLabel } from './labels.ts'
import { isTruncated, orderText, trendModel } from './trend.ts'
import type { TrendPoint } from './trend.ts'
import type { MeasurementRow } from './types.ts'

const WIDTH = 600
const HEIGHT = 220
const BOX: PlotBox = { left: 64, top: 14, width: 510, height: 160 }
const RIGHT = BOX.left + BOX.width
const BOTTOM = BOX.top + BOX.height

/** Resonance frequency by measurement order (1 = first). A measurement without resonance has no dot. */
export function TrendChart({ rows, targetMhz }: { rows: MeasurementRow[]; targetMhz: number }) {
  const model = trendModel(rows, targetMhz, BOX)
  const truncated = isTruncated(rows.length)
  const path = model.points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="측정 순서별 공진 주파수">
        <rect className="chart-area" x={BOX.left} y={BOX.top} width={BOX.width} height={BOX.height} />
        <text className="chart-tick" x={BOX.left - 8} y={BOX.top + 4} textAnchor="end">
          {model.fMax.toFixed(0)}
        </text>
        <text className="chart-tick" x={BOX.left - 8} y={BOTTOM} textAnchor="end">
          {model.fMin.toFixed(0)}
        </text>
        <text className="chart-unit" x={6} y={BOX.top + 4}>MHz</text>
        <line className="chart-target" x1={BOX.left} x2={RIGHT} y1={model.targetY} y2={model.targetY} />
        <text className="chart-target-label" x={RIGHT - 6} y={model.targetY - 6} textAnchor="end">
          목표 {targetMhz} MHz
        </text>
        <polyline className="chart-curve" points={path} />
        {model.points.map((p) => (
          <TrendDot key={p.id} point={p} truncated={truncated} />
        ))}
        <text className="chart-tick" x={BOX.left} y={BOTTOM + 20}>1</text>
        <text className="chart-tick" x={RIGHT} y={BOTTOM + 20} textAnchor="end">{model.count}</text>
        <text className="chart-unit" x={RIGHT} y={BOTTOM + 40} textAnchor="end">
          {truncated ? `측정 순서 (최근 ${rows.length}건)` : '측정 순서'}
        </text>
      </svg>
      <figcaption className="chart-legend">
        <span>● 공진 주파수</span>
        {model.hasSynthetic && <span className="legend-synthetic">◆ 합성 데이터</span>}
        <span>┄ 목표 주파수</span>
        <span>공진이 없는 측정은 점이 없습니다</span>
      </figcaption>
    </figure>
  )
}

/** A synthetic measurement is a diamond in the synthetic color, never the same dot as a real one. */
function TrendDot({ point, truncated }: { point: TrendPoint; truncated: boolean }) {
  const order = orderText(point.order, truncated)
  const title = (
    <title>{`${order} 측정 · ${sourceLabel(point.source)} · 공진 ${point.resonanceMhz.toFixed(2)} MHz`}</title>
  )
  if (point.source !== 'synthetic') {
    return (
      <circle className="chart-marker" cx={point.x} cy={point.y} r={5}>
        {title}
      </circle>
    )
  }
  const { x, y } = point
  return (
    <polygon className="chart-marker-synthetic" points={`${x},${y - 6} ${x + 6},${y} ${x},${y + 6} ${x - 6},${y}`}>
      {title}
    </polygon>
  )
}
