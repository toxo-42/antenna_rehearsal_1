// How to get a sweep on the measure screen. Synthetic samples are for practice and checking the
// app without a VNA, so they stay out of the way until asked for.

export type Method = 'usb' | 'csv' | 'sample'

const METHOD_LABEL: Record<Method, string> = {
  usb: 'VNA (USB)',
  csv: 'CSV 파일',
  sample: '합성 샘플 (연습)',
}

export const DEFAULT_METHOD: Method = 'usb'

export function methodLabel(method: Method): string {
  return METHOD_LABEL[method]
}

/** The methods to choose from: the sample one only once practice was asked for. */
export function visibleMethods(practice: boolean): Method[] {
  return practice ? ['usb', 'csv', 'sample'] : ['usb', 'csv']
}
