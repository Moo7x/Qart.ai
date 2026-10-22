import type { Scenario } from './types'

/** Plain-language labels for the contract's scenario enum (the mockups said "moderate / fast"). */
export const SCENARIO_LABEL: Record<Scenario, string> = {
  assistive: 'AI helps with routine work',
  agentic: 'AI does most routine work',
}

export const SCENARIOS: Scenario[] = ['assistive', 'agentic']
