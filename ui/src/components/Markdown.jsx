function inline(text) {
  return String(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|[^_])_([^_]+)_/g, '$1<em>$2</em>')
}

export default function Markdown({ text }) {
  const blocks = []
  let list = null

  const flushList = () => {
    if (list) {
      blocks.push(list)
      list = null
    }
  }

  for (const raw of String(text).split('\n')) {
    const line = raw.trimEnd()
    if (!line) {
      flushList()
      continue
    }
    const heading = line.match(/^#{2,4}\s+(.*)/)
    const item = line.match(/^[-*]\s+(.*)/)
    if (heading) {
      flushList()
      blocks.push({ type: 'h', text: heading[1] })
    } else if (item) {
      if (!list) list = { type: 'ul', items: [] }
      list.items.push(item[1])
    } else {
      flushList()
      blocks.push({ type: 'p', text: line })
    }
  }
  flushList()

  return (
    <div className="md">
      {blocks.map((b, i) => {
        if (b.type === 'h') {
          return <div key={i} className="md-h" dangerouslySetInnerHTML={{ __html: inline(b.text) }} />
        }
        if (b.type === 'ul') {
          return (
            <ul key={i}>
              {b.items.map((it, j) => (
                <li key={j} dangerouslySetInnerHTML={{ __html: inline(it) }} />
              ))}
            </ul>
          )
        }
        return <p key={i} dangerouslySetInnerHTML={{ __html: inline(b.text) }} />
      })}
    </div>
  )
}
