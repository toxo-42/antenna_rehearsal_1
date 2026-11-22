import { useState } from 'react'
import { ErrorNotice, LoadingNotice } from './Badges.tsx'
import { CardPage } from './CardPage.tsx'
import { HistoryPanel } from './HistoryPanel.tsx'
import { MeasurePanel } from './MeasurePanel.tsx'
import type { Measurement } from './types.ts'
import { useAntennas, useMeasure } from './useAppState.ts'

const TABS = [
  { id: 'measure', label: '① 측정' },
  { id: 'card', label: '② 판정 카드' },
  { id: 'history', label: '③ 이력' },
] as const
type Tab = (typeof TABS)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>('measure')
  const [current, setCurrent] = useState<Measurement | null>(null)
  const antennas = useAntennas()
  const show = (measurement: Measurement) => {
    setCurrent(measurement)
    setTab('card')
  }
  const measure = useMeasure(show)
  const { loaded } = antennas

  return (
    <>
      <TopBar tab={tab} locked={measure.busy} onTab={setTab} />
      <main>
        {loaded.status === 'loading' && <LoadingNotice />}
        {loaded.status === 'error' && <ErrorNotice error={loaded.error} onRetry={antennas.reload} />}
        {loaded.status === 'ready' && tab === 'measure' && (
          <MeasurePanel antennas={antennas} measure={measure} />
        )}
        {loaded.status === 'ready' && tab === 'card' && <CardPage measurement={current} />}
        {loaded.status === 'ready' && tab === 'history' && (
          <HistoryPanel antennas={antennas} onOpen={show} />
        )}
      </main>
    </>
  )
}

function TopBar({ tab, locked, onTab }: { tab: Tab; locked: boolean; onTab: (tab: Tab) => void }) {
  return (
    <header className="topbar">
      <strong className="app-name">안테나 S11 도우미</strong>
      <nav aria-label="화면">
        {TABS.map((item) => (
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
