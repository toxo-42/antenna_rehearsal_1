import { AntennaSidebar } from './AntennaSidebar.tsx'
import { ErrorNotice, LoadingNotice } from './Badges.tsx'
import { CardPage } from './CardPage.tsx'
import { HistoryPanel } from './HistoryPanel.tsx'
import { ManagePanel } from './ManagePanel.tsx'
import { MeasurePanel } from './MeasurePanel.tsx'
import type { Screen } from './mode.ts'
import type { Remeasure } from './types.ts'
import { withRemeasure } from './usbRange.ts'
import { useShell } from './useShell.ts'
import type { Shell, Tab, TabItem } from './useShell.ts'

export default function App() {
  const shell = useShell()
  const { loaded, antennas, measure } = shell
  return (
    <>
      <TopBar screen={shell.screen} locked={measure.busy} onTab={shell.setTab} />
      <div className="shell">
        {loaded.status === 'ready' && (
          <AntennaSidebar
            antennas={antennas.antennas}
            antennaId={antennas.antennaId}
            onSelect={shell.select}
            onAdded={shell.canMeasure ? antennas.add : undefined}
            locked={measure.busy}
            refreshKey={shell.summaryKey}
          />
        )}
        <main>
          {loaded.status === 'loading' && <LoadingNotice />}
          {loaded.status === 'error' && <ErrorNotice error={loaded.error} onRetry={shell.retry} />}
          {loaded.status === 'ready' && <Screens shell={shell} />}
        </main>
      </div>
    </>
  )
}

/** The screen of the chosen tab. */
function Screens({ shell }: { shell: Shell }) {
  const { screen, measure, antenna, setTab } = shell
  // The suggested range goes into the USB boxes. With a port known from an earlier USB
  // measurement the student can measure again right on the card; otherwise the measure tab opens.
  const fillRange = (remeasure: Remeasure) => {
    measure.setUsbRange((boxes) => withRemeasure(boxes, remeasure))
    if (measure.lastPort === null) setTab('measure')
  }
  const again = { measure, onRemeasure: fillRange, onGoMeasure: () => setTab('measure') }
  if (screen.tab === 'measure') return <MeasurePanel antenna={antenna} measure={measure} />
  if (screen.tab === 'history') return <HistoryPanel antenna={antenna} onOpen={shell.show} empty={screen.empty} />
  if (screen.tab === 'manage') return <ManagePanel antennas={shell.antennas} onChanged={shell.managed} />
  return (
    <CardPage
      measurement={shell.current}
      emptyText={screen.empty.card}
      again={shell.canMeasure ? again : undefined}
    />
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
