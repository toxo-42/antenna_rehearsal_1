// Coordinates of the S11 graph: value -> screen position, and the axis ranges. Pure functions.
// The frequency axis runs over the sweep; the dB axis runs from 0 (top) down to `dbBottom`.

import type { SweepPoint } from './types.ts'

export const DB_TOP = 0
export const DB_SHALLOWEST_BOTTOM = -30
export const DB_DEEPEST_BOTTOM = -60
export const MATCH_LINE_DB = -10

/** The drawing area inside the SVG, in SVG units. */
export interface PlotBox {
  left: number
  top: number
  width: number
  height: number
}

export interface ChartScale {
  box: PlotBox
  fMin: number
  fMax: number
  dbBottom: number
}

export interface Point {
  x: number
  y: number
}

/** What the graph needs from a measurement. The target and the resonance come from the response. */
export interface ChartInput {
  sweep: readonly SweepPoint[]
  antenna: { target_mhz: number }
  resonance_mhz: number | null
  s11_db: number | null
}

export interface FreqTick {
  x: number
  label: string
}

export interface ChartModel {
  scale: ChartScale
  curve: Point[]
  targetX: number
  matchY: number
  marker: Point | null
  dbTicks: number[]
  freqTicks: FreqTick[]
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value))
}

/** Bottom of the dB axis: the sweep minimum, kept between -30 (shallowest) and -60 (deepest). */
export function dbBottom(sweep: readonly SweepPoint[]): number {
  const lowest = sweep.reduce((low, point) => Math.min(low, point.s11_db), DB_SHALLOWEST_BOTTOM)
  return clamp(lowest, DB_DEEPEST_BOTTOM, DB_SHALLOWEST_BOTTOM)
}

export function chartScale(sweep: readonly SweepPoint[], box: PlotBox): ChartScale {
  // A loop, not Math.min(...freqs): spreading a large CSV sweep overflows the call stack.
  let fMin = Infinity
  let fMax = -Infinity
  for (const point of sweep) {
    fMin = Math.min(fMin, point.f_mhz)
    fMax = Math.max(fMax, point.f_mhz)
  }
  if (sweep.length === 0) fMin = fMax = 0
  return { box, fMin, fMax, dbBottom: dbBottom(sweep) }
}

/** Frequency -> x. Values outside the sweep stick to the plot edges. */
export function xOf(fMhz: number, scale: ChartScale): number {
  const span = scale.fMax - scale.fMin
  if (!(span > 0)) return scale.box.left // a single point (or nothing) has no span to divide by
  const ratio = clamp((fMhz - scale.fMin) / span, 0, 1)
  return scale.box.left + ratio * scale.box.width
}

/** dB -> y, 0 dB on top. Values outside the axis (above 0 dB too) stick to the axis ends. */
export function yOf(db: number, scale: ChartScale): number {
  const ratio = clamp((DB_TOP - db) / (DB_TOP - scale.dbBottom), 0, 1)
  return scale.box.top + ratio * scale.box.height
}

export function sweepPoints(sweep: readonly SweepPoint[], scale: ChartScale): Point[] {
  return sweep.map((point) => ({ x: xOf(point.f_mhz, scale), y: yOf(point.s11_db, scale) }))
}

/** Where to draw the resonance mark. `null` when the response has no resonance. */
export function markerPoint(
  resonanceMhz: number | null,
  s11Db: number | null,
  scale: ChartScale,
): Point | null {
  if (resonanceMhz === null || s11Db === null) return null
  return { x: xOf(resonanceMhz, scale), y: yOf(s11Db, scale) }
}

/** Tick values on the dB axis: every 10 dB from 0 down to the bottom. */
export function dbTicks(scale: ChartScale): number[] {
  const ticks: number[] = []
  for (let db = DB_TOP; db >= scale.dbBottom; db -= 10) ticks.push(db)
  return ticks
}

/** Five evenly spaced tick values on the frequency axis (one when the sweep has no span). */
export function freqTicks(scale: ChartScale): number[] {
  if (!(scale.fMax > scale.fMin)) return [scale.fMin]
  return [0, 0.25, 0.5, 0.75, 1].map((ratio) => scale.fMin + ratio * (scale.fMax - scale.fMin))
}

/** Decimal places that keep neighbouring frequency ticks distinct: 0 for steps of 1 MHz or more. */
function freqDecimals(scale: ChartScale): number {
  const step = (scale.fMax - scale.fMin) / 4
  if (!(step > 0) || step >= 1) return 0
  // With d decimals one unit is 10^-d <= step, so rounded neighbours never collide.
  return Math.min(6, Math.ceil(-Math.log10(step)))
}

/** Everything the graph draws, in SVG coordinates. */
export function chartModel(input: ChartInput, box: PlotBox): ChartModel {
  const scale = chartScale(input.sweep, box)
  const decimals = freqDecimals(scale)
  return {
    scale,
    curve: sweepPoints(input.sweep, scale),
    targetX: xOf(input.antenna.target_mhz, scale),
    matchY: yOf(MATCH_LINE_DB, scale),
    marker: markerPoint(input.resonance_mhz, input.s11_db, scale),
    dbTicks: dbTicks(scale),
    freqTicks: freqTicks(scale).map((f) => ({ x: xOf(f, scale), label: f.toFixed(decimals) })),
  }
}
