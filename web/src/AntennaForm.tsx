import { useState } from 'react'
import type { FormEvent } from 'react'
import { createAntenna, describeError } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { ErrorNotice } from './Badges.tsx'
import { kindLabel } from './labels.ts'
import { KINDS } from './types.ts'
import type { Antenna, Kind } from './types.ts'

/** An empty or non-numeric target becomes NaN (null in JSON); the server answers in Korean. */
function targetValue(target: string): number {
  return target.trim() === '' ? Number.NaN : Number(target)
}

/** Add an antenna (`name`, `kind`, `target_mhz`). The server checks the values and explains. */
export function AntennaForm({ onAdded }: { onAdded: (antenna: Antenna) => void }) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState<Kind>('monopole')
  const [target, setTarget] = useState('433')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ErrorInfo | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onAdded(await createAntenna({ name, kind, target_mhz: targetValue(target) }))
      setName('')
    } catch (failure) {
      setError(describeError(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="subform" onSubmit={submit}>
      <h3>새 안테나 추가</h3>
      <label className="field">
        이름 (name)
        <input type="text" value={name} placeholder="예: 모노폴 B" onChange={(event) => setName(event.target.value)} />
      </label>
      <div className="field-row">
        <KindSelect kind={kind} onChange={setKind} />
        <TargetField target={target} onChange={setTarget} />
      </div>
      {error !== null && <ErrorNotice error={error} />}
      <button type="submit" className="button-secondary" disabled={busy}>
        안테나 추가
      </button>
    </form>
  )
}

function TargetField({ target, onChange }: { target: string; onChange: (target: string) => void }) {
  return (
    <label className="field">
      목표 주파수 (target_mhz, MHz)
      <input type="text" inputMode="decimal" value={target} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function KindSelect({ kind, onChange }: { kind: Kind; onChange: (kind: Kind) => void }) {
  return (
    <label className="field">
      종류 (kind)
      <select value={kind} onChange={(event) => onChange(event.target.value as Kind)}>
        {KINDS.map((value) => (
          <option key={value} value={value}>
            {kindLabel(value)} ({value})
          </option>
        ))}
      </select>
    </label>
  )
}
