/** All animation in the app goes through GSAP (team decision), with these shared timings. */
import { useLayoutEffect, type DependencyList, type RefObject } from 'react'
import gsap from 'gsap'

// Short and calm: the design system allows fades and small slides only, no bounce.
export const DURATION = 0.25
export const EASE = 'power2.out'
const REVEAL_OFFSET_PX = 8
const REVEAL_STAGGER_S = 0.04

export function reducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Fade-and-rise every [data-reveal] element inside the scope, in order, when deps change. */
export function useReveal(scope: RefObject<HTMLElement | null>, deps: DependencyList) {
  useLayoutEffect(() => {
    if (!scope.current || reducedMotion()) return
    const ctx = gsap.context(() => {
      gsap.from('[data-reveal]', { y: REVEAL_OFFSET_PX, opacity: 0, duration: DURATION, ease: EASE, stagger: REVEAL_STAGGER_S, clearProps: 'transform,opacity' })
    }, scope)
    return () => ctx.revert()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Fade-and-rise one element that just appeared (a chat message, a check result). */
export function enter(el: Element | null) {
  if (!el || reducedMotion()) return
  gsap.from(el, { y: REVEAL_OFFSET_PX, opacity: 0, duration: DURATION, ease: EASE, clearProps: 'transform,opacity' })
}

/** Small scale pulse to confirm something just got done (a task step ticking). */
export function pop(el: Element | null) {
  if (!el || reducedMotion()) return
  gsap.fromTo(el, { scale: 0.6 }, { scale: 1, duration: DURATION, ease: 'back.out(2)', clearProps: 'transform' })
}

export { gsap }
