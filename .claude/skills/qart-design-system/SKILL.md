---
name: qart-design-system
description: Qart.ai visual design system (warm-paper "Notion" style adapted for a general upskilling app). Use whenever building, restyling or reviewing any screen, component, chart, icon or UI copy in web/, so every page shares one look, one voice and the project's evidence-labelling rules.
---

# Qart.ai design system

Qart.ai helps people in **any job** practise real work with an AI companion, learn new skills and upgrade existing ones. Bank reconciliation is only the first example job, so nothing in the design may look finance-specific (no money-green, no ticker bands, no banking imagery).

**Base style:** Refero "Notion" (https://styles.refero.design/style/2bf4c61f-de10-4614-ba1b-20c0453bd2a9, read 2026-10-22). A warm paper notebook: white cards on a warm canvas, hairline borders, one blue for actions, soft accent tints for status. **Borrowed from Refero "Perplexity AI"** (https://styles.refero.design/style/81afaa5c-73ac-4ef4-9a99-296da325ea6c): the left sidebar + centred column layout for the companion/workspace screen only.

Mood: calm, friendly, honest. A place to learn, not a dashboard that judges you.

## 1. Colour tokens

Paste this into `web/src/index.css` after `@import "tailwindcss";`. Use the token classes (`bg-canvas`, `text-ink`, `border-hairline`…), never raw Tailwind palette colours such as `indigo-700` or `gray-500`.

```css
@theme {
  /* Surfaces */
  --color-canvas: #f6f5f4;      /* page background (never pure white) */
  --color-surface: #ffffff;     /* cards, panels, inputs */
  --color-linen: #efedea;       /* secondary panels, selected rows, code/data wells */
  --color-hairline: rgb(0 0 0 / 0.08); /* 1px borders on cards and dividers */
  --color-hairline-strong: rgb(0 0 0 / 0.16); /* input borders, outlined buttons */

  /* Text */
  --color-ink: #1f1e1d;         /* headings and primary text (softer than pure black) */
  --color-graphite: #615d59;    /* body and secondary text; AA on canvas and white */
  --color-stone: #757575;       /* helper text on WHITE only (fails AA on canvas: 4.23) */

  /* Action: the only filled button colour */
  --color-action: #0075de;      /* primary button fill, links, focus ring */
  --color-action-hover: #005bab;
  --color-action-tint: #e6f3fe; /* ghost button fill, selected nav item */
  --color-action-ink: #005bab;  /* text on action-tint (#0075de on tint is only 4.05) */

  /* Accent tints: pills, tags and card fills only, never buttons */
  --color-marigold: #ffb110;      --color-marigold-tint: #fff1d1; --color-marigold-ink: #7a4d00;
  --color-coral: #f64932;         --color-coral-tint: #feeae6;    --color-coral-ink: #a3200f;
  --color-mocha: #b18164;         --color-mocha-tint: #f4ece6;    --color-mocha-ink: #6b4a35;
  --color-midnight: #02093a;      /* dark feature card, at most one per screen */

  /* Type */
  --font-sans: "Switzer", ui-sans-serif, system-ui, sans-serif;
  --font-serif: "Source Serif 4", ui-serif, Georgia, serif;

  /* Shape */
  --radius-sm: 4px;   /* inputs, outlined text buttons, small tags */
  --radius-md: 8px;   /* buttons, nav items, list rows */
  --radius-lg: 12px;  /* cards (maximum for rectangles) */

  /* Elevation: only the sticky nav and floating popovers get a shadow */
  --shadow-nav: 0 0.7px 1.5px rgb(0 0 0 / 0.015), 0 3px 9px rgb(0 0 0 / 0.03);
  --shadow-pop: 0 4px 12px rgb(0 0 0 / 0.10);
}

body { background: var(--color-canvas); color: var(--color-ink); font-family: var(--font-sans); }
```

All text/background pairs above were checked against WCAG AA (4.5:1 for body text) on 2026-10-22: ink on canvas 15.3, graphite on canvas 6.0, white on action 4.57, action-ink on action-tint 6.0, every `*-ink` on its `*-tint` ≥ 6.4.

## 2. Typography

- **Switzer** (Fontshare, ITF Free Font License, free for commercial use) for everything. Load in `web/index.html`:
  `<link href="https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&display=swap" rel="stylesheet">`
- **Source Serif 4** (Google Fonts, SIL OFL) only for short reflective moments: a page intro line, the "why it changed" sentence on a skill, a quote from the companion's summary. Never for labels, buttons, nav or tables.
  `<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400&display=swap" rel="stylesheet">`
- Both are logged in `docs/DECLARATION_LOG.md`.

App scale (an app, not a marketing site, so Notion's 54–96px display sizes are not used):

| Role | Tailwind | Size / line | Weight | Tracking |
|---|---|---|---|---|
| Page title | `text-[32px] leading-[1.15]` | 32 / 1.15 | 600 | `tracking-[-0.02em]` |
| Section heading | `text-[22px] leading-[1.27]` | 22 / 1.27 | 600 | `tracking-[-0.01em]` |
| Card title | `text-base` | 16 / 1.5 | 600 | normal |
| Body | `text-base` | 16 / 1.5 | 400 | normal |
| UI / table | `text-sm` | 14 / 1.43 | 400–500 | normal |
| Caption / label tag | `text-xs` | 12 / 1.33 | 500 | `tracking-[0.01em]` |
| Serif intro | `font-serif text-lg` | 18 / 1.56 | 400 | normal |

Hierarchy comes from size and weight, not colour. Use `tabular-nums` for every number in tables and counts.

## 3. Spacing and layout

- 4px base. Use Tailwind steps 1, 2, 3, 4, 5, 6, 8, 16, 20 (4–80px). Card padding `p-6` (24px), gaps inside cards `gap-2`/`gap-3`, between cards `gap-4`, between page sections `mt-12`–`mt-16`.
- Content max width `max-w-6xl` for list/grid pages; `max-w-3xl` for reading pages (Result, explanations).
- **Workspace / companion screen** (Perplexity borrow): this route alone uses a `max-w-[1440px]` container. A marigold **task strip** ("Your job: check the AI's draft, then decide" plus 4 steps that tick themselves) sits under the title. Below it, the work area is on the left (`lg:grid-cols-[minmax(0,1fr)_360px]`): the AI draft in serif, then a Side by side / Ledger / Bank switch (side by side from `xl` up) with descriptions that wrap, never truncate. Document chips open the `Drawer`. The companion is a sticky white side column on the right (`lg:sticky lg:top-20 lg:h-[calc(100svh-6rem)]`): avatar, help ladder, starter questions when empty, chat, "I'm stuck", and the decision pinned at the bottom. It stacks below the work area on phones. No other page uses a side column.
- **Evidence & assumptions** (HR): layer A (source) and layer B (assumption) as separate sections with provenance tags; the assumptions are one table (task × scenario) with edited cells highlighted in marigold.
- Shared pieces live in `web/src/ui.tsx` (`StatePill`, `ProvenanceTag`, `Tag`, `Card`, `PageHeader`, `SectionTitle`, `Loading`, `EmptyState`, `btn.*`). Use them instead of re-writing class strings.
- Top nav: sticky, `h-16`, `bg-surface/90 backdrop-blur`, `shadow-nav`, hairline bottom border.

## 4. Components (Tailwind recipes)

| Component | Classes |
|---|---|
| Primary button (one per view) | `bg-action hover:bg-action-hover text-white text-sm font-medium rounded-md px-4 py-1.5 transition-colors` |
| Ghost button | `bg-action-tint text-action-ink text-sm font-medium rounded-md px-4 py-1.5 hover:bg-[#d6eafd]` |
| Text button | `text-ink/90 text-sm font-medium rounded-md px-4 py-1.5 hover:bg-linen` |
| Outlined button | `border border-hairline-strong text-ink text-sm rounded-sm px-2.5 py-1 hover:bg-linen` |
| Nav link | `text-sm text-ink/60 rounded-md px-3 py-2 hover:text-ink` · active: `bg-action-tint text-action-ink font-medium` |
| Card | `bg-surface border border-hairline rounded-lg p-6` (no shadow, ever) |
| Accent card (path step, role tile) | `bg-marigold-tint rounded-lg p-6` (or coral/mocha/action tint; no border) |
| Dark card (one per screen max) | `bg-midnight text-white rounded-lg p-6` |
| Pill tag | `inline-flex items-center gap-1 rounded-full px-3 py-0.5 text-xs font-medium` + a state colour below |
| Input / select | `bg-surface border border-hairline-strong rounded-sm px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-action/40` |
| Table | header `text-xs font-medium text-graphite`, rows `border-t border-hairline`, selected row `bg-linen`, numbers right-aligned `tabular-nums` |
| Focus (all interactive) | `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action` |

Motion: **all animation goes through GSAP** via `web/src/motion.ts` (`useReveal`, `enter`, `pop`; 0.25 s, `power2.out`, 8px rise). Hover colour changes may stay CSS `transition-colors duration-200`. Everything is skipped under `prefers-reduced-motion`. No bounce (except the small `pop` on a ticked step), parallax, scroll effects or animated gradients. Mark page blocks with `data-reveal` and call `useReveal(rootRef, [loading])` before any early return.

### Page patterns (UI v2)
Every page follows the same rhythm, using the pieces in `web/src/ui.tsx`:
1. **Headline** (`PageHeader`): 40px title with **one** word wrapped in `<Highlight>`, put at the end of the phrase (a highlight followed by punctuation leaves a gap), plus a serif intro line.
2. **Count tiles** (`StatTile`): colour-filled tiles with a count and a label. Counts only, never a percentage or score.
3. **One dark next-step card** (`NextStepCard`, `bg-midnight`): the single most useful next action on the page, holding the page's only primary button. Other actions on the page are outlined.
4. Content cards and sections below.

Other shared pieces: `Drawer` (right slide-over for documents; Esc closes, focus is trapped and returned), `EmptyState` (also used for the role guard "Not available for this persona"), `Tag`, `StatePill`, `ProvenanceTag`.

### Six-screen reskilling flow
Profile (`/start`) → Signals (`/signals`) → Matches (`/future`) → Pathway (`/pathway?role=`) → SDG impact (`/impact?role=`) → Scenarios (`/scenarios`). Profile is the employees' home page (nav item "Profile", `HOME.employee = '/start'`). Each page starts with `<FlowSteps />` (`web/src/components/FlowSteps.tsx`), and "My future" stays highlighted in the nav on every step after Profile. Rules:
- **Scenarios** are labelled with `SCENARIO_LABEL` from `web/src/scenarios.ts` ("AI helps with routine work" / "AI does most routine work"), never "moderate/fast".
- **Fit** is a suitability indicator: never "/100" and never a "±" band. `ai_handled_share` is a layer-B assumption shown as a point value, not a range.
- **Profile.preferences** fields carry a "Saved · not used for ranking yet" tag until the engine reads them.
- Profile does not ask for self-ratings or interests (removed at the user's request); saving keeps the values already stored, which the ranking's confidence and interest factors still use. If interest chips come back, offer only options that match role tags: tag-less options lower every score.
- **SDG text comes from `GET /api/sdg`**, so goal names are never hard-coded. Pathway costs show the catalogue's own wording, with no HRD Corp badge unless a verified listing exists.
- Pathway ticks are a per-persona browser checklist, labelled "not evidence".
- Mockup numbers in `design/qart-flow/` are illustrative. Never copy them; see `docs/screens_gap_report.md`.

### Personas and roles
The nav changes with the persona (`web/src/persona.tsx`): employees get Start / Work queue / My skills / My future, HR gets HR summary / Evidence & assumptions, and the senior gets Companion updates. Use `useUserId()` for every per-person call; never hard-code a user or case id. The persona select and Reset demo sit at the right of the nav. "Synthetic · demo data" appears from `lg` up.

### Decision screens (humans decide)
Wherever a person makes a decision (case decision in the workspace, a senior approving or rejecting an optimiser proposal), the options are **equal outlined buttons**, so the UI does not nudge the choice. HR's "Approve as version N" is the one exception: it is a single action, not a choice between options.

## 5. Project-specific patterns (non-negotiable)

These encode the rules in `AGENTS.md` and `team/00_SHARED_CONTRACT.md`.

**Skill evidence states**: always a pill plus the *why* and the evidence trail; **never a percentage, score bar or progress ring** for mastery.

| `state` | Label | Pill classes | Icon (Lucide) |
|---|---|---|---|
| `demonstrated_independently` | Shown on your own | `bg-action-tint text-action-ink` | `BadgeCheck` |
| `observed_with_help` | Shown with help | `bg-marigold-tint text-marigold-ink` | `LifeBuoy` |
| `self_reported` | You said so | `bg-linen text-graphite` | `MessageSquareQuote` |
| `insufficient_evidence` | Not enough evidence yet | `border border-dashed border-hairline-strong text-graphite` | `CircleDashed` |

Progress toward a state is shown as counts in words ("1 of 2 independent successes"), never a bar.

**Number provenance labels**: every number shown carries one small tag (`text-xs`, pill):

| Kind | Tag text | Classes |
|---|---|---|
| Evidence (dated public source) | `Source · AEI, May 2026` (link to the source) | `bg-mocha-tint text-mocha-ink` |
| Assumption (company layer B / declared parameter) | `Assumption v3` | `bg-coral-tint text-coral-ink` |
| Synthetic | `Synthetic` | `bg-linen text-graphite` |

The global "Synthetic demo data" badge in the nav uses the synthetic style.

**Help levels** in the companion (0 none → 4 answer shown) are shown as named steps ("Question → Hint → Explanation → Answer"), with the current step in `action-ink` and the rest in `graphite`.

**HR views**: aggregates only. Suppressed cells (group under 5) show an em dash `—` in `text-stone` with a tooltip "Hidden: fewer than 5 people", never a zero.

**AI output** shown for review sits in a `bg-linen rounded-lg p-4` well with a small `Bot` icon and the label "AI draft". The person's decision buttons sit outside it, so the human decision is visually separate from the AI's claim.

## 6. Icons and graphics

- **Lucide only** (`lucide-react`, already installed, ISC licence). One style everywhere: `size={16}` inline with text, `size={20}` in buttons/cards, `strokeWidth={1.75}`, `currentColor`. Never draw or generate icons; if Lucide lacks one, pick the closest Lucide icon.
- Diagrams and charts (learning path, role matching, HR aggregates) are **inline SVG or React-rendered SVG**, using only the tokens above, with clean editable paths. No raster images in the UI.
- No illustrations, stock photos, gradients or emoji in the interface.

## 7. Copy rules

Studied 2026-10-22 from the first screens of Coursera, Pluralsight, Degreed and LinkedIn Learning (Duolingo's site could not be read without JavaScript). What the strong ones do:

- **Name the change, then the person's next step.** "AI is reshaping Data Analytics" · "Technology is ready. Is your workforce?" · "Start, switch, or advance your career". Headlines talk about the job changing, not about the product.
- **Short verb buttons**: "Get started", "Join for Free". Weak pattern seen: "Learn more", "Why Pluralsight".
- **One idea per screen.** One headline, one supporting line, one primary action.

Qart.ai rules built on that:

1. Talk to the person, in the second person, about their work: "Review this AI draft", not "Case review module".
2. Buttons are verb + object, at most 3 words: "Start practice", "Sign off", "Ask for a hint", "See why". Never "Submit", "Click here", "Learn more".
3. Headlines state what changes for the person: "Your next skill to practise", not "Recommendations".
4. Be honest about the system: say "recommends", never "decides"; say "based on 3 cases", never "AI-powered insights".
5. No AI-sounding words: delve, unlock, empower, leverage, seamless, journey, elevate, cutting-edge, revolutionise, supercharge, game-changer.
6. Plain English, short sentences (one idea each). Numbers in digits. Sentence case for every heading and button.
7. Mistakes are framed as learning: "Missed, then found with a hint", never "Failed".
8. Never name a specific industry in shared UI chrome (nav, empty states, onboarding); the job comes from the data.

## 8. Do / don't

Do: warm canvas under white cards · one blue primary action per view · hairline borders for separation · tints for status · real empty states ("No cases yet. Your first practice case appears here.") · visible focus rings · readable at 1280px and at 375px.

Don't: pure white page background · shadows on cards · more than one filled button colour · radius above 12px on rectangles · gradients · percentages for skills · raw Tailwind colours (`gray-*`, `indigo-*`, `green-*`) · serif for UI labels · finance-specific styling in shared UI.

## 9. Checklist before finishing a UI change

1. Only token colours used (`grep -nE '(gray|indigo|blue|green|red|amber|slate)-[0-9]' web/src` returns nothing new).
2. Every number has a provenance tag; no mastery percentages.
3. One primary button per view; buttons follow the copy rules.
4. Icons are Lucide at the standard sizes.
5. Empty, loading and error states exist and use the same tone.
6. `cd web && npm run build` passes; check the page in the browser at desktop and phone width.
