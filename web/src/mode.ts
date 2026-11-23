// Demo mode (APP_MODE=demo): stored measurements only. The server refuses every write with 403;
// the screen hides the measure tab so no button leads to that refusal.

import type { Health } from './types.ts'

const DEMO = 'demo'
// Tabs whose every button is a write: measuring, and managing (rename, delete).
const WRITE_TABS: readonly string[] = ['measure', 'manage']
const DEMO_START_TAB = 'history'

export function isDemo(health: Health | null): boolean {
  return health?.mode === DEMO
}

export function visibleTabs<T extends { id: string }>(tabs: readonly T[], demo: boolean): T[] {
  return tabs.filter((tab) => !demo || !WRITE_TABS.includes(tab.id))
}

/** The tab to show for the chosen one: in demo mode a hidden tab becomes history. */
export function shownTab<T extends string>(tab: T, demo: boolean): T | typeof DEMO_START_TAB {
  return demo && WRITE_TABS.includes(tab) ? DEMO_START_TAB : tab
}

/** What an empty screen says. Demo texts never point at the hidden measure tab. */
export interface EmptyTexts {
  card: string
  antennas: string
  measurements: string
}

const EMPTY_LOCAL: EmptyTexts = {
  card: '아직 측정이 없습니다. 측정 화면에서 시작하거나 이력에서 골라 주세요.',
  antennas: '등록된 안테나가 없습니다. 왼쪽에서 먼저 추가해 주세요.',
  measurements: '이 안테나의 측정이 아직 없습니다. 측정 화면에서 시작해 주세요.',
}

const EMPTY_DEMO: EmptyTexts = {
  card: '이력에서 측정을 골라 주세요.',
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
