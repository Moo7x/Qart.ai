import { useEffect, useRef } from 'react'
import { HERO_SCENE_SVG } from './heroSceneSvg'

// The landing page's landscape: a winding path from the foreground to a distant city, the career
// pathway. Decorative only (aria-hidden). Layers drift with the pointer; every animation is CSS
// inside prefers-reduced-motion: no-preference, and the SMIL walker is paused when motion is reduced.
const WALKER_PAUSED_AT_SECONDS = 9 // a point on the path where the walker is clearly visible

export function HeroScene() {
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = root.current
    const svg = el?.querySelector('svg')
    if (!el || !svg) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      svg.pauseAnimations()
      svg.setCurrentTime(WALKER_PAUSED_AT_SECONDS)
      return
    }
    let frame = 0
    const move = (e: PointerEvent) => {
      const x = e.clientX / window.innerWidth - 0.5
      const y = e.clientY / window.innerHeight - 0.5
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        el.style.setProperty('--px', (x * 2).toFixed(3))
        el.style.setProperty('--py', (y * 2).toFixed(3))
      })
    }
    window.addEventListener('pointermove', move, { passive: true })
    return () => {
      window.removeEventListener('pointermove', move)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [])
  return (
    <div ref={root} className="s-scene" aria-hidden="true">
      {/* Static markup generated from our own drawing code (heroSceneSvg.ts), never user input. */}
      <div className="contents" dangerouslySetInnerHTML={{ __html: HERO_SCENE_SVG }} />
      <div className="s-veil" />
    </div>
  )
}
