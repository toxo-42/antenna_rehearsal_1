// Demo mode (APP_MODE=demo): stored measurements only. The server refuses every write with 403;
// the screen hides the measure tab so no button leads to that refusal.

import type { Health } from './types.ts'

const DEMO = 'demo'
const MEASURE_TAB = 'measure'
const DEMO_START_TAB = 'history'

export function isDemo(health: Health | null): boolean {
  return health?.mode === DEMO
}

export function visibleTabs<T extends { id: string }>(tabs: readonly T[], demo: boolean): T[] {
  return tabs.filter((tab) => !demo || tab.id !== MEASURE_TAB)
}

/** The tab to show for the chosen one: in demo mode the hidden measure tab becomes history. */
export function shownTab<T extends string>(tab: T, demo: boolean): T | typeof DEMO_START_TAB {
  return demo && tab === MEASURE_TAB ? DEMO_START_TAB : tab
}

/** What an empty screen says. Demo texts never point at the hidden measure tab. */
export interface EmptyTexts {
  card: string
  antennas: string
  measurements: string
}

const EMPTY_LOCAL: EmptyTexts = {
  card: '아직 측정이 없습니다. ① 측정에서 시작하거나 ③ 이력에서 골라 주세요.',
  antennas: '등록된 안테나가 없습니다. ① 측정에서 먼저 추가해 주세요.',
  measurements: '이 안테나의 측정이 아직 없습니다. ① 측정에서 시작해 주세요.',
}

const EMPTY_DEMO: EmptyTexts = {
  card: '③ 이력에서 측정을 골라 주세요.',
  antennas: '시연용 DB에 안테나가 없습니다.',
  measurements: '시연용 DB에 이 안테나의 측정이 없습니다. 다른 안테나를 골라 주세요.',
}

export interface Screen<T> {
  badge: string | null
  tabs: T[]
  tab: string
  empty: EmptyTexts
}

/** Everything the mode changes on screen. `health` is null until it is known (shown as local). */
export function screenFor<T extends { id: string }>(
  tabs: readonly T[],
  chosen: T['id'],
  health: Health | null,
): Screen<T> {
  const demo = isDemo(health)
  return {
    badge: demo ? '시연 모드' : null,
    tabs: visibleTabs(tabs, demo),
    tab: shownTab(chosen, demo),
    empty: demo ? EMPTY_DEMO : EMPTY_LOCAL,
  }
}
