// The change note is picked from fixed lists, never typed: the app does not interpret free text.

export const NO_CHANGE = '없음'
export const PARTS = [NO_CHANGE, '도체', '접지판', '케이블', '교정', '납땜'] as const
export const ACTIONS = [NO_CHANGE, '줄임', '늘림', '변경'] as const
export const AMOUNTS = [NO_CHANGE, '0.5', '1', '2', '3', '5', '10', '20', '50'] as const
export const UNITS = ['mm', 'cm', '%'] as const

export interface NoteChoice {
  part: string
  action: string
  amount: string
  unit: string
}

export const EMPTY_NOTE: NoteChoice = { part: NO_CHANGE, action: NO_CHANGE, amount: NO_CHANGE, unit: UNITS[0] }

/** "도체 줄임 5 mm". Empty when no part is chosen; a missing action or amount is left out. */
export function changeNoteText(choice: NoteChoice): string {
  if (choice.part === NO_CHANGE) return ''
  const words = [choice.part]
  if (choice.action !== NO_CHANGE) words.push(choice.action)
  if (choice.amount !== NO_CHANGE) words.push(choice.amount, choice.unit)
  return words.join(' ')
}
