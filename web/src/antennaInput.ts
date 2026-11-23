// The add-antenna form is checked here before anything is sent, so the student reads a Korean
// sentence instead of the server's field name. The server still checks the values again.

export const NAME_NOTICE = '안테나 이름을 입력해 주세요'
export const TARGET_NOTICE = '목표 주파수를 숫자로 입력해 주세요 (MHz)'

/** The typed target as a number; NaN when the box is empty or does not hold a number. */
export function targetValue(target: string): number {
  return target.trim() === '' ? Number.NaN : Number(target)
}

/** What is wrong with the form, or null when it can be sent. The name is checked first. */
export function antennaInputError(name: string, target: string): string | null {
  if (name.trim() === '') return NAME_NOTICE
  const value = targetValue(target)
  return Number.isFinite(value) && value > 0 ? null : TARGET_NOTICE
}
