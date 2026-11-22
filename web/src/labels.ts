// What the screen shows for each value-list value. The state color comes from `stage` only and
// the badge from `source` only. Color is never the only cue: each tone has a symbol and a word.

import type { CalMode, Kind, Source, Stage } from './types.ts'

export type Tone = 'good' | 'caution' | 'problem'

/** Calibration starts as "not confirmed": the student must choose "calibrated" on purpose. */
export const DEFAULT_CAL_MODE: CalMode = 'unknown'

const STAGE_TONE: Record<Stage, Tone> = {
  good: 'good',
  narrow: 'caution',
  offtarget: 'caution',
  unmatched: 'problem',
  none: 'problem',
  invalid: 'problem',
}

const TONE_LABEL: Record<Tone, string> = { good: '양호', caution: '주의', problem: '문제' }
const TONE_SYMBOL: Record<Tone, string> = { good: '○', caution: '△', problem: '×' }
const INVALID_LABEL = '측정 오류'

const SOURCE_LABEL: Record<Source, string> = {
  usb: '실측',
  csv: 'CSV',
  synthetic: '합성 데이터',
  // The original source of a stored sweep is unknown, so it is never called a live measurement.
  stored: '저장된 측정',
}

const SOURCE_SYMBOL: Record<Source, string> = { usb: '●', csv: '▤', synthetic: '◇', stored: '▣' }

const KIND_LABEL: Record<Kind, string> = { monopole: '모노폴', patch: '패치' }

const CAL_MODE_LABEL: Record<CalMode, string> = {
  vna: '본체에서 교정함',
  unknown: '확인되지 않음',
}

export function stageTone(stage: Stage): Tone {
  return STAGE_TONE[stage]
}

export function stageLabel(stage: Stage): string {
  return stage === 'invalid' ? INVALID_LABEL : TONE_LABEL[STAGE_TONE[stage]]
}

export function stageSymbol(stage: Stage): string {
  return TONE_SYMBOL[STAGE_TONE[stage]]
}

export function sourceLabel(source: Source): string {
  return SOURCE_LABEL[source]
}

export function sourceSymbol(source: Source): string {
  return SOURCE_SYMBOL[source]
}

export function kindLabel(kind: Kind): string {
  return KIND_LABEL[kind]
}

export function calModeLabel(mode: CalMode): string {
  return CAL_MODE_LABEL[mode]
}

/** "모노폴 · 목표 433 MHz" for an antenna or a sample. */
export function antennaText(antenna: { kind: Kind; target_mhz: number }): string {
  return `${KIND_LABEL[antenna.kind]} · 목표 ${antenna.target_mhz} MHz`
}

/** The server's ISO local time with a space instead of the `T`. */
export function timeText(measuredAt: string): string {
  return measuredAt.replace('T', ' ')
}
