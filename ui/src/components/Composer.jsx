import { forwardRef, useImperativeHandle, useRef, useState } from 'react'
import { Paperclip, Send } from 'lucide-react'

const CHIPS = [
  'Check attendance policy',
  'Find upcoming events',
  'Check placement eligibility',
  'Find student services help',
]

const Composer = forwardRef(function Composer({ onSend, disabled }, ref) {
  const [text, setText] = useState('')
  const inputRef = useRef(null)

  useImperativeHandle(ref, () => ({
    fill: (value) => {
      setText(value)
      inputRef.current?.focus()
    },
  }))

  const submit = () => {
    const value = text.trim()
    if (!value || disabled) return
    setText('')
    onSend(value)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="composer">
      <div className="chips">
        {CHIPS.map((c) => (
          <button
            key={c}
            className="chip"
            disabled={disabled}
            onClick={() => {
              setText(c)
              inputRef.current?.focus()
            }}
          >
            {c}
          </button>
        ))}
      </div>
      <div className="chat-input">
        <textarea
          ref={inputRef}
          value={text}
          placeholder="Ask the agent team anything about college operations…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="composer-tools"><span>Llama-3-70B Local</span><Paperclip size={14} aria-label="Attachments are not enabled" /></div>
        <button className="send" onClick={submit} disabled={disabled || !text.trim()} aria-label="Send">
          <Send size={14} />
        </button>
      </div>
    </div>
  )
})

export default Composer
