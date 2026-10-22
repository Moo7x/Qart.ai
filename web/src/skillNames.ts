/** Display names for catalogue skill ids (catalogue/skills.json), shared by every screen. */
export const SKILL_NAMES: Record<string, string> = {
  recon_to_source: 'Reconcile to source',
  duplicate_detection: 'Duplicate detection',
  cutoff_timing: 'Cut-off & timing',
  unsupported_adjustment: 'Unsupported adjustment',
  fx_conversion: 'FX conversion',
  transposition_check: 'Transposition check',
  escalation_judgment: 'Escalation judgment',
  ai_output_review: 'AI output review',
  variance_analysis: 'Variance analysis',
  data_quality: 'Data quality',
  controls_design: 'Controls design',
  process_automation: 'Process automation',
  stakeholder_communication: 'Stakeholder comms',
  forecasting: 'Forecasting',
  spreadsheet_modelling: 'Spreadsheet modelling',
  sql_basics: 'SQL basics',
}

export function skillName(skillId: string): string {
  return SKILL_NAMES[skillId] ?? skillId.replace(/_/g, ' ')
}
