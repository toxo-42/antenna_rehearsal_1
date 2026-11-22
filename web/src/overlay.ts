// Two sweeps on one shared scale, so before and after can be read against each other.

import { chartScale, freqDecimals, freqTicks, sweepPoints, xOf } from './chart.ts'
import type { ChartScale, FreqTick, PlotBox, Point } from './chart.ts'
import type { SweepPoint } from './types.ts'

export interface OverlayModel {
  scale: ChartScale
  before: Point[]
  after: Point[]
  targetX: number
  freqTicks: FreqTick[]
}

export function overlayModel(
  before: readonly SweepPoint[],
  after: readonly SweepPoint[],
  targetMhz: number,
  box: PlotBox,
): OverlayModel {
  const scale = chartScale([...before, ...after], box)
  const decimals = freqDecimals(scale)
  return {
    scale,
    before: sweepPoints(before, scale),
    after: sweepPoints(after, scale),
    targetX: xOf(targetMhz, scale),
    freqTicks: freqTicks(scale).map((f) => ({ x: xOf(f, scale), label: f.toFixed(decimals) })),
  }
}
