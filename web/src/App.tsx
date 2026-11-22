import { useState } from 'react'
import { getHealth } from './api.ts'
import { ErrorNotice, LoadingNotice } from './Badges.tsx'
import { CardPage } from './CardPage.tsx'
import { HistoryPanel } from './HistoryPanel.tsx'
import { MeasurePanel } from './MeasurePanel.tsx'
import { screenFor } from './mode.ts'
import type { Screen } from './mode.ts'
import type { Measurement } from './types.ts'
import { useAntennas, useMeasure } from './useAppState.ts'
import { useLoad } from './useLoad.ts'

const TABS = [
  { id: 'measure', label: '① 측정' },
  { id: 'card', label: '② 판정 카드' },
  { id: 'history', label: '③ 이력' },
] as const
type TabItem = (typeof TABS)[number]
type Tab = TabItem['id']

export default function App() {
  const [chosen, setTab] = useState<Tab>('measure')
  const [current, setCurrent] = useState<Measurement | null>(null)
  const antennas = useAntennas()
  const show = (measurement: Measurement) => {
    setCurrent(measurement)
    setTab('card')
  }
  const measure = useMeasure(show)
  const [health, reloadHealth] = useLoad(getHealth, 'health')
  // The mode decides tabs, badge and empty texts; see mode.ts and its tests.
  const screen = screenFor(TABS, chosen, health.status === 'ready' ? health.data : null)
  const { tab } = screen
  // No panel before the mode is known, so demo mode never opens the measure tab (and its USB
  // port list). A failed mode answer is shown as an error, not guessed as local.
  const loaded = health.status === 'ready' ? antennas.loaded : health
  const retry = () => {
    reloadHealth()
    antennas.reload()
  }

  return (
    <>
      <TopBar screen={screen} locked={measure.busy} onTab={setTab} />
      <main>
        {loaded.status === 'loading' && <LoadingNotice />}
        {loaded.status === 'error' && <ErrorNotice error={loaded.error} onRetry={retry} />}
        {loaded.status === 'ready' && tab === 'measure' && (
          <MeasurePanel antennas={antennas} measure={measure} />
        )}
        {loaded.status === 'ready' && tab === 'card' && (
          <CardPage measurement={current} emptyText={screen.empty.card} />
        )}
        {loaded.status === 'ready' && tab === 'history' && (
          <HistoryPanel antennas={antennas} onOpen={show} empty={screen.empty} />
        )}
      </main>
    </>
  )
}

type TopBarProps = { screen: Screen<TabItem>; locked: boolean; onTab: (tab: Tab) => void }

function TopBar({ screen, locked, onTab }: TopBarProps) {
  const { tab, badge, tabs } = screen
  return (
    <header className="topbar">
      <strong className="app-name">안테나 S11 도우미</strong>
      {badge !== null && (
        <span className="badge badge-demo" title="저장된 측정만 볼 수 있습니다. 측정·저장·AI 설명은 꺼져 있습니다.">
          {badge}
        </span>
      )}
      <nav aria-label="화면">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            className="tab"
            aria-current={tab === item.id ? 'page' : undefined}
            disabled={locked && tab !== item.id}
            title={locked ? '측정이 끝나면 이동할 수 있습니다' : undefined}
            onClick={() => onTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </header>
  )
}
