// Text for the AI explanation and the question box. The generated text is shown with only two
// kinds of formatting: `## ` headings and numbered lists. Everything else stays plain text.

import type { AskStatus, ExplainStatus } from './types.ts'

export const EXPLAIN_BUTTON = 'AI 튜터에게 설명 듣기'
export const EXPLAIN_LABEL = 'AI 설명(참고용). 결론과 수치는 위 카드가 기준입니다'
export const ASK_NOT_IN_CARD = '이번 측정에서는 나타나지 않은 항목입니다'

export type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'list'; start: number; items: string[] }

const HEADING = '## '
const LIST_ITEM = /^\s*(\d+)[.)]\s+(.*)$/

/** Split a generated text into headings, numbered lists, and plain paragraphs (one per line). */
export function explanationBlocks(text: string): Block[] {
  const blocks: Block[] = []
  let list: Extract<Block, { kind: 'list' }> | null = null
  for (const line of text.split('\n')) {
    const item = LIST_ITEM.exec(line)
    if (item !== null) {
      if (list === null) {
        list = { kind: 'list', start: Number(item[1]), items: [] }
        blocks.push(list)
      }
      list.items.push(item[2].trim())
      continue
    }
    list = null
    if (line.trim() === '') continue
    if (line.startsWith(HEADING)) blocks.push({ kind: 'heading', text: line.slice(HEADING.length).trim() })
    else blocks.push({ kind: 'paragraph', text: line.trim() })
  }
  return blocks
}

export function warningText(warnings: string[]): string | null {
  return warnings.length === 0 ? null : `카드에 없는 수치가 있습니다: ${warnings.join(', ')}`
}

const EXPLAIN_NOTICE: Record<ExplainStatus, string | null> = {
  ok: null,
  off: null,
  rejected: 'AI 설명이 카드와 달라 표시하지 않습니다',
  failed: 'AI 설명을 만들지 못했습니다. 위 카드를 기준으로 보세요.',
}

/** What replaces the text when it is not shown. */
export function explainNotice(status: ExplainStatus): string | null {
  return EXPLAIN_NOTICE[status]
}

const ASK_NOTICE: Record<AskStatus, string | null> = {
  matched: null,
  none: '관련 설명 없음',
  failed: '질문을 설명에 연결하지 못했습니다. 아래 목록에서 직접 골라 보세요.',
}

export function askNotice(status: AskStatus): string | null {
  return ASK_NOTICE[status]
}
