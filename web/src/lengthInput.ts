// The conductor length box on the measure screen. Optional: empty means "not entered", and the
// verdict then works from the target frequency alone. The server checks the range (0 < cm <= 1000).

/** The number to send, or null when the box is empty or does not hold a number. */
export function lengthValue(text: string): number | null {
  if (text.trim() === '') return null
  const value = Number(text)
  return Number.isFinite(value) ? value : null
}

/** Shown under the box when its text cannot be sent, so a typo is never dropped silently. */
export function lengthNotice(text: string): string | null {
  if (text.trim() === '' || lengthValue(text) !== null) return null
  return '숫자만 입력해 주세요 (예: 12 또는 11.5).'
}
