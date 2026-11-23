import { useState } from 'react'
import type { FormEvent } from 'react'
import { antennaInputError, targetValue } from './antennaInput.ts'
import { createAntenna, describeError } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { ErrorNotice } from './Badges.tsx'
import { kindLabel } from './labels.ts'
import { KINDS } from './types.ts'
import type { Antenna, Kind } from './types.ts'

interface FormProps {
  onAdded: (antenna: Antenna) => void
  /** True while a measurement runs: nothing can be typed or sent. */
  disabled: boolean
}

/** Add an antenna (`name`, `kind`, `target_mhz`). Checked here first, then by the server. */
export function AntennaForm({ onAdded, disabled }: FormProps) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState<Kind>('monopole')
  const [target, setTarget] = useState('433')
  const { busy, error, send } = useSend(onAdded)
  const off = busy || disabled
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!off) void send(name, kind, target).then((added) => added && setName(''))
  }
  return (
    <form className="subform" onSubmit={submit}>
      <h3>새 안테나 추가</h3>
      <label className="field">
        이름
        <input
          type="text"
          value={name}
          placeholder="예: 모노폴 B"
          disabled={off}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <KindSelect kind={kind} disabled={off} onChange={setKind} />
      <TargetField target={target} disabled={off} onChange={setTarget} />
      {error !== null && <ErrorNotice error={error} />}
      <button type="submit" className="button-secondary" disabled={off}>
        안테나 추가
      </button>
    </form>
  )
}

/** Sends the form once it passes the check in antennaInput.ts. Resolves true when added. */
function useSend(onAdded: (antenna: Antenna) => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ErrorInfo | null>(null)
  async function send(name: string, kind: Kind, target: string): Promise<boolean> {
    const problem = antennaInputError(name, target)
    setError(problem === null ? null : { message: problem, serverDown: false })
    if (problem !== null) return false
    setBusy(true)
    try {
      onAdded(await createAntenna({ name, kind, target_mhz: targetValue(target) }))
      return true
    } catch (failure) {
      setError(describeError(failure))
      return false
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, send }
}

type TargetProps = { target: string; disabled: boolean; onChange: (target: string) => void }

function TargetField({ target, disabled, onChange }: TargetProps) {
  return (
    <label className="field">
      목표 주파수 (MHz)
      <input
        type="text"
        inputMode="decimal"
        value={target}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

function KindSelect({ kind, disabled, onChange }: { kind: Kind; disabled: boolean; onChange: (kind: Kind) => void }) {
  return (
    <label className="field">
      종류
      <select value={kind} disabled={disabled} onChange={(event) => onChange(event.target.value as Kind)}>
        {KINDS.map((value) => (
          <option key={value} value={value}>
            {kindLabel(value)}
          </option>
        ))}
      </select>
    </label>
  )
}
