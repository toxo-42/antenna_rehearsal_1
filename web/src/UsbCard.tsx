import { useState } from 'react'
import { listPorts, measureUsb } from './api.ts'
import { EmptyNotice, ErrorNotice, LoadingNotice, SourceBadge } from './Badges.tsx'
import type { Antenna } from './types.ts'
import { USB_CAL_NOTICE, USB_MODE_NOTICE, choosePort, rangeWarning } from './usbRange.ts'
import type { RangeBoxes } from './usbRange.ts'
import type { MeasureState } from './useAppState.ts'
import { useLoad } from './useLoad.ts'

interface UsbProps {
  antenna: Antenna | null
  measure: MeasureState
}

/** Measure on a SAA-2 over USB. The PC sets the range; the device screen settings are not used. */
export function UsbCard({ antenna, measure }: UsbProps) {
  const [ports, reload] = useLoad(() => listPorts(), 'ports')
  const [port, setPort] = useState<string | null>(null)
  const { startMhz, stopMhz, points } = measure.usbRange
  const setBox = (name: keyof RangeBoxes) => (value: number) =>
    measure.setUsbRange((boxes) => ({ ...boxes, [name]: value }))
  const chosen = choosePort(port, ports.status === 'ready' ? ports.data : null)
  const warning = rangeWarning(startMhz, stopMhz, antenna?.target_mhz ?? null)
  const start = () =>
    antenna !== null &&
    chosen !== null &&
    measure.run(() =>
      measureUsb(antenna.id, { port: chosen, startMhz, stopMhz, points }, measure.calMode, measure.changeNote),
    )
  return (
    <section className="card">
      <h2>
        3-다. SAA-2로 측정 (USB) <SourceBadge source="usb" />
      </h2>
      {ports.status === 'loading' && <LoadingNotice />}
      {ports.status === 'error' && <ErrorNotice error={ports.error} onRetry={reload} />}
      {ports.status === 'ready' && (
        <PortPicker ports={ports.data} chosen={chosen} onChoose={setPort} onReload={reload} />
      )}
      <div className="field-row">
        <NumberField label="시작 MHz" value={startMhz} onChange={setBox('startMhz')} />
        <NumberField label="종료 MHz" value={stopMhz} onChange={setBox('stopMhz')} />
        <NumberField label="점 개수 (11~1001)" value={points} onChange={setBox('points')} />
      </div>
      {warning !== null && <p className="explain-warning">{warning}</p>}
      <p className="muted">{USB_CAL_NOTICE}</p>
      <button type="button" disabled={measure.busy || antenna === null || chosen === null} onClick={start}>
        SAA-2로 측정
      </button>
      <p className="explain-warning" role="note">
        {USB_MODE_NOTICE}
      </p>
    </section>
  )
}

interface PortPickerProps {
  ports: string[]
  chosen: string | null
  onChoose: (port: string) => void
  onReload: () => void
}

function PortPicker({ ports, chosen, onChoose, onReload }: PortPickerProps) {
  return (
    <div className="field-row">
      {ports.length === 0 ? (
        <EmptyNotice>연결된 포트가 없습니다. SAA-2를 USB로 연결하고 다시 찾아 주세요.</EmptyNotice>
      ) : (
        <label className="field">
          포트 (SAA-2가 맨 앞)
          <select value={chosen ?? ''} onChange={(event) => onChoose(event.target.value)}>
            {ports.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}
      <button type="button" onClick={onReload}>
        포트 다시 찾기
      </button>
    </div>
  )
}

function NumberField(props: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="field">
      {props.label}
      <input type="number" value={props.value} onChange={(event) => props.onChange(event.target.valueAsNumber)} />
    </label>
  )
}
