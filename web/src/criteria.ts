// The stage criteria grouped under the three states of the chip. The sentences are the
// server's (built from the rule constants) and are shown as they are.

import { TONES, stageTone, toneLabel, toneSymbol } from './labels.ts'
import type { Tone } from './labels.ts'
import type { Criterion } from './types.ts'

export interface CriteriaGroup {
  tone: Tone
  label: string
  symbol: string
  texts: string[]
}

/** 양호, 주의, 문제 in that order; a state without a sentence is left out. */
export function criteriaByTone(items: readonly Criterion[]): CriteriaGroup[] {
  return TONES.map((tone) => ({
    tone,
    label: toneLabel(tone),
    symbol: toneSymbol(tone),
    texts: items.filter((item) => stageTone(item.stage) === tone).map((item) => item.text),
  })).filter((group) => group.texts.length > 0)
}
