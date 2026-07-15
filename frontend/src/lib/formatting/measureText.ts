const LIST_LINE_RE = /^(?:[-*•]|\d+[.)]|[A-Za-z][.)])\s+/


function normalizeLine(line: string) {
  return line.replace(/\s+/g, ' ').trim()
}


function isListLine(line: string) {
  return LIST_LINE_RE.test(line)
}


function normalizeBlock(block: string) {
  const lines = block
    .split('\n')
    .map(normalizeLine)
    .filter((line) => line.length > 0)

  if (lines.length <= 1) {
    return lines[0] ?? ''
  }

  const output: string[] = []
  let currentParagraph: string[] = []

  function flushParagraph() {
    if (currentParagraph.length === 0) {
      return
    }

    output.push(currentParagraph.join(' '))
    currentParagraph = []
  }

  for (const line of lines) {
    if (isListLine(line)) {
      flushParagraph()
      output.push(line)
      continue
    }

    currentParagraph.push(line)
  }

  flushParagraph()
  return output.join('\n')
}


export function formatMeasureText(text: string) {
  return text
    .replace(/\r\n?/g, '\n')
    .split(/\n{2,}/)
    .map((block) => normalizeBlock(block.trim()))
    .filter((block) => block.length > 0)
    .join('\n\n')
}


export function formatMeasureSnippet(text: string, limit = 220) {
  const normalized = formatMeasureText(text).replace(/\n+/g, ' ')
  return normalized.length <= limit ? normalized : `${normalized.slice(0, limit - 3)}...`
}