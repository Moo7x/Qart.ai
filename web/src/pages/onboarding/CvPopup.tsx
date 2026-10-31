import { X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

const CLOSE_MS = 200 // the fade-out; immediate when motion is reduced
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** The CV popup's dialog shell: focus moves inside and is kept there, Escape and the close button
 *  close it, focus returns to the opener, and the page behind stops scrolling until it closes. */
export function CvPopup({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const [closing, setClosing] = useState(false)
  const latest = useRef(onClose)
  useEffect(() => { latest.current = onClose })
  // Stable for the dialog's lifetime, so the setup below runs once (focus, keys, scroll lock).
  const close = useCallback(() => {
    if (reduced()) return latest.current()
    setClosing(true)
    window.setTimeout(() => latest.current(), CLOSE_MS)
  }, [])
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeButton.current?.focus()
    const overflow = document.documentElement.style.overflow
    document.documentElement.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return }
      if (e.key !== 'Tab') return
      const stops = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select, textarea, [tabindex="0"]') ?? []).filter((el) => el.getClientRects().length > 0)
      const edge = e.shiftKey ? stops[0] : stops.at(-1)
      if (document.activeElement === edge) { e.preventDefault(); (e.shiftKey ? stops.at(-1) : stops[0])?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.documentElement.style.overflow = overflow
      opener?.focus()
    }
  }, [close])
  return createPortal(
    <div className={`j-veil ${closing ? 'j-closing' : ''}`} onMouseDown={(e) => e.target === e.currentTarget && close()}>
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="j-title" className="j-dialog">
        <button ref={closeButton} type="button" aria-label="Close" onClick={close} className="j-close"><X size={16} aria-hidden="true" /></button>
        {children}
      </div>
    </div>,
    document.body,
  )
}
