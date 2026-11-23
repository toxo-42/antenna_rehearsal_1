import { useState } from 'react'
import { getHealth } from './api.ts'
import { screenFor } from './mode.ts'
import type { Antenna, Measurement } from './types.ts'
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
  const [changes, setChanges] = useState(0)
  const antennas = useAntennas()
  const antenna = antennas.antennas.find((item) => item.id === antennas.antennaId) ?? null
  const card = useCard(antenna, () => setTab('card'))
  const [health, reloadHealth] = useLoad(getHealth, 'health')
  // The mode decides tabs, badge and empty texts; see mode.ts and its tests.
  const screen = screenFor(TABS, chosen, health.status === 'ready' ? health.data : null)
  // The card belongs to one antenna: choosing another one in the sidebar puts it away.
  const select = (id: number) => {
    antennas.select(id)
    card.keepFor(id)
  }
  // A new antenna is in the list once it is loaded again; then it is chosen like any other.
  const add = async (added: Antenna) => {
    await antennas.refresh()
    select(added.id)
  }
  // After a rename or a delete the open card may show what is gone, and the summary is stale.
  const managed = () => {
    card.close()
    setChanges((count) => count + 1)
  }
  const retry = () => {
    reloadHealth()
    antennas.reload()
  }
  return {
    screen, setTab, antennas, antenna, select, add, managed, retry,
    current: card.current, show: card.open, measure: card.measure,
    // Demo mode has no measure tab: no add form, no measure-again bar.
    canMeasure: screen.tabs.some((item) => item.id === 'measure'),
    // No panel before the mode is known, so demo mode never opens the measure tab (and its USB
    // port list). A failed mode answer is shown as an error, not guessed as local.
    loaded: health.status === 'ready' ? antennas.loaded : health,
    summaryKey: `${card.current?.id ?? 0}:${changes}`,
  }
}

/** The open card and the measuring that fills it. `onShown` opens the card tab. */
function useCard(antenna: Antenna | null, onShown: () => void) {
  const [current, setCurrent] = useState<Measurement | null>(null)
  const show = (measurement: Measurement) => {
    setCurrent(measurement)
    onShown()
  }
  const measure = useMeasure(show, antenna)
  // A card opened from the history is not the measurement that failed: its error goes away.
  const open = (measurement: Measurement) => {
    measure.clearError()
    show(measurement)
  }
  const keepFor = (antennaId: number) =>
    setCurrent((shown) => (shown !== null && shown.antenna.id !== antennaId ? null : shown))
  return { current, measure, open, keepFor, close: () => setCurrent(null) }
}
