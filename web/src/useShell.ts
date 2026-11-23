import { useState } from 'react'
import { getHealth } from './api.ts'
import { screenFor } from './mode.ts'
import type { Measurement } from './types.ts'
import { useAntennas, useMeasure } from './useAppState.ts'
import { useLoad } from './useLoad.ts'

export const TABS = [
  { id: 'measure', label: '측정' },
  { id: 'card', label: '판정' },
  { id: 'history', label: '이력' },
  { id: 'manage', label: '관리' },
] as const
export type TabItem = (typeof TABS)[number]
export type Tab = TabItem['id']

export type Shell = ReturnType<typeof useShell>

/** Everything above the screens: the tab, the chosen antenna, the open card and the mode. */
export function useShell() {
  const [chosen, setTab] = useState<Tab>('measure')
  const [current, setCurrent] = useState<Measurement | null>(null)
  const [changes, setChanges] = useState(0)
  const antennas = useAntennas()
  const show = (measurement: Measurement) => {
    setCurrent(measurement)
    setTab('card')
  }
  const measure = useMeasure(show)
  const [health, reloadHealth] = useLoad(getHealth, 'health')
  // The mode decides tabs, badge and empty texts; see mode.ts and its tests.
  const screen = screenFor(TABS, chosen, health.status === 'ready' ? health.data : null)
  // The card belongs to one antenna: choosing another one in the sidebar puts it away.
  const select = (id: number) => {
    antennas.select(id)
    if (current !== null && current.antenna.id !== id) setCurrent(null)
  }
  // After a rename or a delete the open card may show what is gone, and the summary is stale.
  const managed = () => {
    setCurrent(null)
    setChanges((count) => count + 1)
  }
  const retry = () => {
    reloadHealth()
    antennas.reload()
  }
  return {
    screen, setTab, current, show, antennas, select, measure, managed, retry,
    antenna: antennas.antennas.find((item) => item.id === antennas.antennaId) ?? null,
    // Demo mode has no measure tab: no add form, no measure-again bar.
    canMeasure: screen.tabs.some((item) => item.id === 'measure'),
    // No panel before the mode is known, so demo mode never opens the measure tab (and its USB
    // port list). A failed mode answer is shown as an error, not guessed as local.
    loaded: health.status === 'ready' ? antennas.loaded : health,
    summaryKey: `${current?.id ?? 0}:${changes}`,
  }
}
