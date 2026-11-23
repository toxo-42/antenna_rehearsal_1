// The change note: part, action and unit are picked from fixed lists, the amount is a typed
// number. No free text: the app does not interpret it. Same grammar as src/change_note.py.

export const NO_CHANGE = '없음'
export const PARTS = [NO_CHANGE, '도체', '접지판', '케이블', '교정', '납땜'] as const
export const ACTIONS = [NO_CHANGE, '줄임', '늘림', '변경'] as const
export const UNITS = ['mm', 'cm', '%'] as const
// A plain number, up to 4 digits and 2 decimals. Zero is refused in amountValue.
export const AMOUNT_PATTERN = /^(0|[1-9]\d{0,3})(\.\d{1,2})?$/

export interface NoteChoice {
  part: string
  action: string
  /** As typed; empty means no amount. */
  amount: string
  unit: string
}

export const EMPTY_NOTE: NoteChoice = { part: NO_CHANGE, action: NO_CHANGE, amount: '', unit: UNITS[0] }

/** The amount to write into the note, or null when the box is empty or not a positive number. */
export function amountValue(text: string): string | null {
  const typed = text.trim()
  return AMOUNT_PATTERN.test(typed) && Number(typed) > 0 ? typed : null
}

/** Shown under the box when its text is left out of the note, so a typo is never dropped silently. */
export function amountNotice(text: string): string | null {
  if (text.trim() === '' || amountValue(text) !== null) return null
  return '0보다 큰 숫자만 입력해 주세요 (예: 5 또는 0.5, 소수 둘째 자리까지).'
}

/** "도체 줄임 5 mm". Empty when no part is chosen; a missing action or amount is left out. */
export function changeNoteText(choice: NoteChoice): string {
  if (choice.part === NO_CHANGE) return ''
  const words = [choice.part]
  if (choice.action !== NO_CHANGE) words.push(choice.action)
  const amount = amountValue(choice.amount)
  if (amount !== null) words.push(amount, choice.unit)
  return words.join(' ')
}
