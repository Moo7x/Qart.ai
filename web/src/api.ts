/**
 * API client. Calls the real backend by default; set VITE_USE_MOCKS=true to use the
 * local sample data so the frontend runs standalone without a backend.
 */
import axios from 'axios';
import type {
  Case,
  MarketPulseSnapshot,
  Role,
  SdgMap,
  SkillSignalsSnapshot,
  UserSignals,
  CompanionMessageResponse,
  CompanyAssumptions,
  DecisionResponse,
  HRSummaryData,
  IngestResult,
  OptimizerProposal,
  OptimizerStatus,
  PlaybookInfo,
  SnapshotDiff,
  NextCase,
  SearchResponse,
  PathPlan,
  Profile,
  Recommendation,
  SkillState,
  Snapshot, Questionnaire, RankingResponse, ScenarioName, AiTrend, HiringNow, LearningPlanResponse, HeldSkill } from './types';

const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? 'false') === 'true';
const BASE = import.meta.env.VITE_API_URL ?? '';

// ── Mock data ──────────────────────────────────────────────────────────────────

const MOCK_CASE: Case = {
  id: 'case_003',
  title: 'Oct bank reconciliation – Kopi Kita Sdn Bhd',
  mode: 'practice',
  difficulty: 2,
  scenario_variant: 'assistive',
  ledger: [
    { row_id: 'L1', date: '2026-10-01', description: 'Opening balance', amount: 48000, currency: 'MYR' },
    { row_id: 'L2', date: '2026-10-03', description: 'Rent – Oct 2026', amount: -3200, currency: 'MYR', doc_ref: 'INV-1001' },
    { row_id: 'L3', date: '2026-10-05', description: 'Utilities – Tenaga Nasional', amount: -800, currency: 'MYR', doc_ref: 'INV-1002' },
    { row_id: 'L4', date: '2026-10-14', description: 'Supplier payment – Beans Co', amount: -1520, currency: 'MYR', doc_ref: 'INV-1043' },
    { row_id: 'L5', date: '2026-10-18', description: 'Petty cash replenishment', amount: -500, currency: 'MYR', doc_ref: 'PCF-001' },
    { row_id: 'L6', date: '2026-10-25', description: 'Salary advance – Oct', amount: -2500, currency: 'MYR', doc_ref: 'SA-001' },
    { row_id: 'L7', date: '2026-10-31', description: 'Bank service charges', amount: -100, currency: 'MYR', doc_ref: 'BC-001' },
  ],
  bank: [
    { row_id: 'B1', date: '2026-10-01', description: 'Opening balance', amount: 48000, currency: 'MYR' },
    { row_id: 'B2', date: '2026-10-03', description: 'RENT OCT 2026', amount: -3200, currency: 'MYR' },
    { row_id: 'B3', date: '2026-10-05', description: 'TNB PAYMENT', amount: -800, currency: 'MYR' },
    { row_id: 'B4', date: '2026-10-18', description: 'PETTY CASH', amount: -500, currency: 'MYR' },
    { row_id: 'B5', date: '2026-10-25', description: 'SALARY ADVANCE', amount: -2500, currency: 'MYR' },
    { row_id: 'B6', date: '2026-10-15', description: 'TRF BEANS CO', amount: -1250, currency: 'MYR' },
    { row_id: 'B7', date: '2026-10-31', description: 'BANK CHARGES', amount: -100, currency: 'MYR' },
  ],
  documents: [
    { doc_ref: 'INV-1043', type: 'invoice', text: 'Beans Co Sdn Bhd\nInvoice No: INV-1043\nDate: 14 Oct 2026\nTotal: RM1,250.00' },
    { doc_ref: 'INV-1001', type: 'invoice', text: 'Selamat Property\nOct 2026 Rental\nAmount: RM3,200.00' },
    { doc_ref: 'INV-1002', type: 'invoice', text: 'Tenaga Nasional\nOct 2026 electricity\nAmount: RM800.00' },
    { doc_ref: 'PCF-001', type: 'form', text: 'Petty Cash Form PCF-001\nReplenishment\nAmount: RM500.00' },
    { doc_ref: 'SA-001', type: 'form', text: 'Salary Advance SA-001\nEmployee advance Oct\nAmount: RM2,500.00' },
    { doc_ref: 'BC-001', type: 'statement', text: 'Maybank Monthly Statement\nOct 2026 service charges: RM100.00' },
  ],
  ai_output: {
    claim: 'Account reconciles. Difference RM0.00 after adjustment ADJ-7.',
    proposed_adjustments: [{ id: 'ADJ-7', amount: 270, reason: 'rounding difference' }],
  },
};

const MOCK_SKILLS: SkillState[] = [
  {
    user_id: 'u_aina',
    skill_id: 'unsupported_adjustment',
    state: 'observed_with_help',
    why: '1 of 2 independent successes needed. case_006 solved after a question (help 1).',
    next_to_confirm: 'checkin_002 (later session)',
    evidence_trail: [
      { event_id: 'ev_0001', case_id: 'case_003', outcome: 'missed_then_found', help_level: 2 },
      { event_id: 'ev_0002', case_id: 'case_006', outcome: 'success', help_level: 1 },
      { event_id: 'ev_0003', case_id: 'checkin_001', outcome: 'success', help_level: 0 },
    ],
    counted_events: 3,
    independent_successes: 1,
    self_confidence: 0.8,
    provisional_estimate: 0.58,
    estimate_note: 'internal only; parameters are provisional assumptions',
    last_updated: '2026-10-22T10:40:00+08:00',
  },
  {
    user_id: 'u_aina',
    skill_id: 'transposition_check',
    state: 'observed_with_help',
    why: 'Caught in case_003 after a hint (help 2). Needs an independent success in a check-in.',
    next_to_confirm: 'checkin_003 (different session)',
    evidence_trail: [
      { event_id: 'ev_0001', case_id: 'case_003', outcome: 'missed_then_found', help_level: 2 },
    ],
    counted_events: 1,
    independent_successes: 0,
    self_confidence: 0.75,
    provisional_estimate: 0.35,
    estimate_note: 'internal only; parameters are provisional assumptions',
    last_updated: '2026-10-22T10:40:00+08:00',
  },
  {
    user_id: 'u_aina',
    skill_id: 'ai_output_review',
    state: 'insufficient_evidence',
    why: 'Only 1 counted event so far. Need at least 2.',
    next_to_confirm: null,
    evidence_trail: [
      { event_id: 'ev_0001', case_id: 'case_003', outcome: 'missed_then_found', help_level: 2 },
    ],
    counted_events: 1,
    independent_successes: 0,
    self_confidence: 0.7,
    provisional_estimate: 0.28,
    estimate_note: 'internal only; parameters are provisional assumptions',
    last_updated: '2026-10-22T10:40:00+08:00',
  },
  {
    user_id: 'u_aina',
    skill_id: 'escalation_judgment',
    state: 'self_reported',
    why: 'Only intake self-report so far. No practice cases attempted.',
    next_to_confirm: null,
    evidence_trail: [],
    counted_events: 0,
    independent_successes: 0,
    self_confidence: 0.6,
    provisional_estimate: 0.2,
    estimate_note: 'internal only; parameters are provisional assumptions',
    last_updated: null,
  },
];

const MOCK_RECOMMENDATION: Recommendation = {
  user_id: 'u_aina',
  scenario: 'assistive',
  snapshot_id: 'snap_aei_2026_05',
  assumptions_version: 3,
  roles: [
    {
      role_id: 'ai_finops_analyst',
      rank: 1,
      score: 0.52,
      title: 'AI Finance Operations Analyst',
      factors: { coverage: 0.60, confidence: 0.50, interest: 0.60, effort: 0.40 },
      formula: '0.55×coverage + 0.20×confidence + 0.10×interest − 0.15×effort',
      gap: [
        { skill_id: 'variance_analysis', state: 'insufficient_evidence', weight: 0.20 },
        { skill_id: 'ai_output_review', state: 'insufficient_evidence', weight: 0.27 },
      ],
      requirement_card: {
        tasks: [
          { task: 'Review AI-prepared reconciliations', onet: '13-2051.00', allocation: 'ai_drafts_human_reviews' },
          { task: 'Sign off on adjusted entries', onet: '43-3031.00', allocation: 'human' },
        ],
        weights: [
          { skill_id: 'ai_output_review', base: 0.15, scenario: 0.27, because: 'Assistive: matching moves to AI drafts → 50% of execution weight shifts to oversight (assumption v3)' },
        ],
        evidence: [
          { label: 'AEI May 2026, SOC 43-3031 usage 0.32', url: 'https://huggingface.co/datasets/Anthropic/EconomicIndex', kind: 'evidence' },
          { label: 'O*NET 13-2051.00', url: 'https://www.onetonline.org/link/summary/13-2051.00', kind: 'evidence' },
        ],
      },
      sources: [
        { label: 'O*NET 13-2051.00', url: 'https://www.onetonline.org/link/summary/13-2051.00' },
        { label: 'AEI release 2026-05 (CC-BY)', url: 'https://huggingface.co/datasets/Anthropic/EconomicIndex' },
      ],
      sdg_targets: ['4.4', '8.2'],
      score_note: 'Suitability indicator, not a probability',
      fit: 0.72,
      time_to_ready: { hours: 14, weeks_at_current_budget: 4 },
      close_match: true,
      outlook: {
        ai_handled_share: 0.79,
        oversight_share: 0.85,
        label: 'being transformed',
        because: 'Sample data: most task weight is drafted by AI; most skill weight is oversight.',
        basis: 'derived from company assumptions (layer B); not a headcount forecast',
      },
    },
  ],
};

const MOCK_PATH: PathPlan = {
  user_id: 'u_aina',
  target_role_id: 'ai_finops_analyst',
  weekly_hours: 4,
  robust_across: ['assistive', 'agentic'],
  steps: [
    { order: 1, type: 'checkin', ref: 'checkin_002', title: 'Confirmation check-in: unsupported adjustments', hours: 0.5, skills: ['unsupported_adjustment'], cost: 'free', because: 'You have 1 independent success; one more confirms demonstrated_independently' },
    { order: 2, type: 'course', ref: 'course_12', title: 'Variance Analysis – Google Sheets (Coursera audit)', hours: 3, skills: ['variance_analysis'], url: 'https://www.coursera.org/learn/business-analysis-spreadsheets', cost: 'free', sdg_targets: ['4.4'] },
    { order: 3, type: 'practice_case', ref: 'case_007', title: 'AI false-alarm case: deposit in transit', hours: 1, skills: ['ai_output_review', 'cutoff_timing'], cost: 'free' },
  ],
  total_hours: 18,
  weeks: 5,
  worst_case_gap: 0.22,
};

// A small slice of catalogue/questionnaire.json (same shape as GET /api/questionnaire).
const MOCK_QUESTIONNAIRE: Questionnaire = {
  funding: {
    employment: [{ id: 'employed', label: 'Employed' }, { id: 'job_seeking', label: 'Job seeking' }],
    employer_hrd: [{ id: 'yes', label: 'Yes' }, { id: 'no', label: 'No' }, { id: 'not_sure', label: 'Not sure' }],
    budget: [{ id: 'free_only', label: 'Free only' }],
    budget_limit_myr: 200,
    language: [{ id: 'en', label: 'English' }, { id: 'either', label: 'Either' }],
    age_band: [{ id: 'prefer_not', label: 'Prefer not to say' }],
    malaysian: [{ id: 'prefer_not', label: 'Prefer not to say' }],
  },
  industries: ['Finance & accounting', 'Other'],
  education: [{ label: "Bachelor's degree", level: 'bachelor' }],
  education_order: ['secondary', 'certification', 'diploma', 'bachelor', 'master'],
  levels: [
    { id: 'heard', label: 'Heard of it', value: 0.3 },
    { id: 'sometimes', label: 'Use sometimes', value: 0.7 },
    { id: 'confident', label: 'Confident', value: 1.0 },
  ],
  default_level: 'sometimes',
  tools: [
    { label: 'Excel', skills: ['spreadsheet_modelling'], exclusive: false },
    { label: 'SQL', skills: ['sql_basics'], exclusive: false },
    { label: 'None of these', skills: [], exclusive: true },
  ],
  current_roles: [
    { id: 'reconciliation_associate', name: 'Reconciliation Associate', family: 'finance_ops', catalogue_role_id: 'recon_associate', typical_skills: ['spreadsheet_modelling', 'recon_to_source'] },
  ],
  tasks: [
    { id: 'query_database', label: 'Pull data from a database', skills: ['sql_basics'], families: ['finance_ops'] },
  ],
  skills: [
    { id: 'spreadsheet_modelling', name: 'Spreadsheet modelling', category: 'Finance tools' },
    { id: 'recon_to_source', name: 'Reconcile to source', category: 'Finance practice' },
    { id: 'sql_basics', name: 'SQL basics', category: 'Data' },
  ],
};

// The signal snapshots have no mock: in mock mode these calls fail at once (no request) and the
// pages show their "no signal data" state.
const NO_MOCK_SIGNALS = () => Promise.reject(new Error('signal snapshots are not mocked'));

const MOCK_PROFILE: Profile = {
  id: 'u_aina',
  display_name: 'Aina',
  current_role_id: 'recon_associate',
  years_experience: 0.5,
  skills_self_reported: [
    { skill_id: 'recon_to_source', confidence: 0.6 },
    { skill_id: 'duplicate_detection', confidence: 0.5 },
    { skill_id: 'cutoff_timing', confidence: 0.5 },
    { skill_id: 'unsupported_adjustment', confidence: 0.8 },
    { skill_id: 'fx_conversion', confidence: 0.4 },
    { skill_id: 'transposition_check', confidence: 0.75 },
    { skill_id: 'escalation_judgment', confidence: 0.6 },
    { skill_id: 'ai_output_review', confidence: 0.7 },
  ],
  interests: ['analysis', 'automation'],
  weekly_learning_hours: 4,
  language: 'en',
  team: 'finops_kl',
};

const MOCK_SNAPSHOTS: Snapshot[] = [
  {
    id: 'snap_aei_2026_05',
    source: 'Anthropic Economic Index (CC-BY)',
    release_date: '2026-05',
    period: 'retrieved 2026-10-21',
    url: 'https://huggingface.co/datasets/Anthropic/EconomicIndex',
  },
];

const MOCK_HR_SUMMARY: HRSummaryData = {
  team: 'finops_kl',
  group_size: 12,
  min_group_size: 5,
  suppressed: false,
  skills: [
    { skill_id: 'unsupported_adjustment', counts: { demonstrated_independently: null, observed_with_help: 5, self_reported: null, insufficient_evidence: 6 } },
    { skill_id: 'transposition_check', counts: { demonstrated_independently: null, observed_with_help: null, self_reported: 6, insufficient_evidence: 5 } },
  ],
  training_demand: [
    { scenario: 'assistive', skills: [{ skill_id: 'unsupported_adjustment', people_without_demonstration: 12, max_role_weight: 0.23 }] },
  ],
  note: 'Sample data. Groups and cells under 5 people are suppressed.',
};

// ── API functions ──────────────────────────────────────────────────────────────

export async function listCases(): Promise<Case[]> {
  if (USE_MOCKS) return [MOCK_CASE];
  const { data } = await axios.get<Case[]>(`${BASE}/api/cases`);
  return data;
}

export async function getCase(id: string): Promise<Case> {
  if (USE_MOCKS) return MOCK_CASE;
  const { data } = await axios.get<Case>(`${BASE}/api/cases/${id}`);
  return data;
}

export async function postProfile(profile: Omit<Profile, 'id'>): Promise<{ profile: Profile; skills: SkillState[] }> {
  if (USE_MOCKS) return { profile: { ...profile, id: 'u_aina' }, skills: MOCK_SKILLS };
  const { data } = await axios.post(`${BASE}/api/profile`, profile);
  return data;
}

export async function getSkills(userId: string): Promise<SkillState[]> {
  if (USE_MOCKS) return MOCK_SKILLS;
  const { data } = await axios.get<SkillState[]>(`${BASE}/api/skills/${userId}`);
  return data;
}

export async function getNextCase(userId: string): Promise<NextCase> {
  if (USE_MOCKS) {
    return { case_id: 'case_006', because: 'Sample data: case_006 practises the skill you missed in case_003.' };
  }
  const { data } = await axios.get<NextCase>(`${BASE}/api/next-case/${userId}`);
  return data;
}

export async function getRecommendation(userId: string, scenario: string): Promise<Recommendation> {
  if (USE_MOCKS) return { ...MOCK_RECOMMENDATION, scenario: scenario as 'assistive' | 'agentic' };
  const { data } = await axios.get<Recommendation>(`${BASE}/api/recommendations/${userId}`, { params: { scenario } });
  return data;
}

// Without roleId / weeklyHours the server uses the best role across both scenarios and the
// weekly hours from the employee's intake.
export async function getPath(userId: string, roleId?: string | null, weeklyHours?: number): Promise<PathPlan> {
  if (USE_MOCKS) return MOCK_PATH;
  const params: Record<string, string | number> = {};
  if (roleId) params.role_id = roleId;
  if (weeklyHours) params.weekly_hours = weeklyHours;
  const { data } = await axios.get<PathPlan>(`${BASE}/api/path/${userId}`, { params });
  return data;
}

const MOCK_SEARCH: SearchResponse = {
  query: 'sample',
  engine: 'keyword',
  note: 'Sample data.',
  results: [],
};

export async function getResources(skillId: string, k = 3): Promise<SearchResponse> {
  if (USE_MOCKS) return MOCK_SEARCH;
  const { data } = await axios.get<SearchResponse>(`${BASE}/api/resources/${skillId}`, { params: { k } });
  return data;
}

export async function searchResources(q: string, kinds?: string[], k = 5): Promise<SearchResponse> {
  if (USE_MOCKS) return { ...MOCK_SEARCH, query: q };
  const { data } = await axios.get<SearchResponse>(`${BASE}/api/search`, {
    params: { q, k, kinds },
    paramsSerializer: { indexes: null },
  });
  return data;
}

export async function postMessage(
  sessionId: string,
  caseId: string,
  userMessage: string,
  userId = 'u_aina',
  scenario = 'assistive',
): Promise<CompanionMessageResponse> {
  if (USE_MOCKS) {
    return {
      reply: "I'm here to help. Take your time reviewing the reconciliation.",
      help_level: 0,
      ui_actions: [{ type: 'show_check', check: 'recompute_totals', result: 'Ledger 39380 vs Bank 39650 → difference -270' }],
      trace: ['checking totals'],
    };
  }
  const { data } = await axios.post<CompanionMessageResponse>(`${BASE}/api/companion/${sessionId}/message`, {
    user_message: userMessage,
    case_id: caseId,
    user_id: userId,
    scenario,
  });
  return data;
}

export async function postDecision(
  sessionId: string,
  caseId: string,
  decision: string,
  flaggedRows: string[],
  userId = 'u_aina',
  scenario = 'assistive',
): Promise<DecisionResponse> {
  if (USE_MOCKS) {
    const correct = decision === 'correct';
    return {
      // event is null for a wrong practice decision (missed_then_found flow)
      event: correct ? {
        id: 'ev_mock_001',
        user_id: userId,
        case_id: caseId,
        mode: 'practice' as const,
        scenario: 'assistive' as const,
        timestamp: new Date().toISOString(),
        self_confidence_before: 0.8,
        help_level_max: 0,
        help_steps: [],
        checks_used: [],
        user_decision: decision as 'sign_off' | 'correct' | 'escalate',
        decision_correct: true,
        issue_found_by: flaggedRows.length > 0 ? 'user' : 'companion',
        skills_evidence: [],
        cause_if_wrong: null,
        companion_version: 'playbook_v1',
        duration_sec: 120,
        difficulty: 2,
        session_id: sessionId,
        flags: { companion_error: false, ambiguous_case: false, data_issue: false },
      } : null,
      decision_correct: correct,
      explanation: correct
        ? 'Correct! Ledger keyed 1,520 instead of 1,250. ADJ-7 was hiding the transposition error.'
        : "Not quite. The account doesn't reconcile cleanly — look more closely at the adjustments.",
      affected_rows: ['L4', 'ADJ-7'],
      correct_decision: 'correct' as const,
      missed_and_walking_back: !correct,
    };
  }
  const { data } = await axios.post<DecisionResponse>(`${BASE}/api/companion/${sessionId}/decision`, {
    decision,
    case_id: caseId,
    flagged_rows: flaggedRows,
    user_id: userId,
    scenario,
  });
  return data;
}

export async function getProfile(userId: string): Promise<Profile> {
  if (USE_MOCKS) return MOCK_PROFILE;
  const { data } = await axios.get<Profile>(`${BASE}/api/profile/${userId}`);
  return data;
}

// Role ranking (pure function on the server). No mock: mock mode shows the "could not load" state.
export async function getRanking(userId: string, scenario: ScenarioName): Promise<RankingResponse> {
  if (USE_MOCKS) return Promise.reject(new Error('the ranking is not mocked'));
  const { data } = await axios.get<RankingResponse>(`${BASE}/api/ranking/${userId}`, { params: { scenario } });
  return data;
}

export async function getLearningPlan(userId: string, roleId?: string | null, swaps: Record<string, string> = {}): Promise<LearningPlanResponse> {
  if (USE_MOCKS) return Promise.reject(new Error('the learning plan is not mocked'));
  const params = new URLSearchParams();
  if (roleId) params.set('role_id', roleId);
  Object.entries(swaps).forEach(([skill, course]) => params.append('swap', `${skill}:${course}`));
  const { data } = await axios.get<LearningPlanResponse>(`${BASE}/api/learning-plan/${userId}`, { params });
  return data;
}

// The person's skills from the questionnaire, raised by practice evidence (contract v2.4).
export async function getHeldSkills(userId: string): Promise<HeldSkill[]> {
  if (USE_MOCKS) return [];
  const { data } = await axios.get<HeldSkill[]>(`${BASE}/api/held-skills/${userId}`);
  return data;
}

export async function getQuestionnaire(): Promise<Questionnaire> {
  if (USE_MOCKS) return MOCK_QUESTIONNAIRE;
  const { data } = await axios.get<Questionnaire>(`${BASE}/api/questionnaire`);
  return data;
}

export async function getRoles(): Promise<Role[]> {
  if (USE_MOCKS) return [];
  const { data } = await axios.get<Role[]>(`${BASE}/api/roles`);
  return data;
}

// Future Skills Radar: the server reads saved snapshots only (works offline).
export async function getSkillSignals(): Promise<SkillSignalsSnapshot> {
  if (USE_MOCKS) return NO_MOCK_SIGNALS();
  const { data } = await axios.get<SkillSignalsSnapshot>(`${BASE}/api/signals/skills`);
  return data;
}

export async function getMarketPulse(): Promise<MarketPulseSnapshot> {
  if (USE_MOCKS) return NO_MOCK_SIGNALS();
  const { data } = await axios.get<MarketPulseSnapshot>(`${BASE}/api/signals/market-pulse`);
  return data;
}

export async function getAiTrend(region?: string, granularity: 'week' | 'month' = 'week'): Promise<AiTrend> {
  if (USE_MOCKS) return NO_MOCK_SIGNALS();
  const { data } = await axios.get<AiTrend>(`${BASE}/api/signals/ai-trend`, { params: { region, granularity } });
  return data;
}

export async function getHiringNow(region = 'malaysia_singapore'): Promise<HiringNow> {
  if (USE_MOCKS) return NO_MOCK_SIGNALS();
  const { data } = await axios.get<HiringNow>(`${BASE}/api/signals/hiring-now`, { params: { region } });
  return data;
}

export async function getUserSignals(userId: string): Promise<UserSignals> {
  if (USE_MOCKS) return NO_MOCK_SIGNALS();
  const { data } = await axios.get<UserSignals>(`${BASE}/api/signals/for-user/${userId}`);
  return data;
}

export async function getSdg(): Promise<SdgMap> {
  if (USE_MOCKS) return { about: 'Sample data.', retrieved: '', targets: [], roles: {}, skills: {} };
  const { data } = await axios.get<SdgMap>(`${BASE}/api/sdg`);
  return data;
}

export async function getSnapshots(): Promise<Snapshot[]> {
  if (USE_MOCKS) return MOCK_SNAPSHOTS;
  const { data } = await axios.get<Snapshot[]>(`${BASE}/api/snapshots`);
  return data;
}

export async function getHRSummary(team: string): Promise<HRSummaryData> {
  if (USE_MOCKS) return MOCK_HR_SUMMARY;
  const { data } = await axios.get<HRSummaryData>(`${BASE}/api/hr/summary`, { params: { team } });
  return data;
}

// ── Demo, flags, HR evidence, optimiser ───────────────────────────────────────

export async function resetDemo(): Promise<void> {
  if (USE_MOCKS) return;
  await axios.post(`${BASE}/api/demo/reset`);
}

export async function flagSession(
  sessionId: string,
  flag: 'companion_error' | 'ambiguous_case' | 'data_issue',
  userId: string,
): Promise<void> {
  if (USE_MOCKS) return;
  await axios.post(`${BASE}/api/companion/${sessionId}/flag`, { flag, user_id: userId });
}

export async function getAssumptions(): Promise<CompanyAssumptions> {
  const { data } = await axios.get<CompanyAssumptions>(`${BASE}/api/assumptions`);
  return data;
}

export async function putAssumptions(update: CompanyAssumptions): Promise<CompanyAssumptions> {
  const { data } = await axios.put<CompanyAssumptions>(`${BASE}/api/assumptions`, update);
  return data;
}

export async function ingestNextSnapshot(): Promise<IngestResult> {
  const { data } = await axios.post<IngestResult>(`${BASE}/api/ingest/run`);
  return data;
}

export async function getSnapshotDiff(): Promise<SnapshotDiff | null> {
  try {
    const { data } = await axios.get<SnapshotDiff>(`${BASE}/api/snapshots/diff`);
    return data;
  } catch {
    return null; // fewer than two snapshots ingested yet
  }
}

export async function getProposals(): Promise<OptimizerProposal[]> {
  const { data } = await axios.get<OptimizerProposal[]>(`${BASE}/api/optimizer/proposals`);
  return data;
}

export async function decideProposal(id: string, decision: 'approve' | 'reject', decidedBy: string): Promise<OptimizerProposal> {
  const { data } = await axios.post<OptimizerProposal>(`${BASE}/api/optimizer/proposals/${id}/decision`, {
    decision,
    decided_by: decidedBy,
  });
  return data;
}

export async function rollbackProposal(id: string): Promise<PlaybookInfo> {
  const { data } = await axios.post<PlaybookInfo>(`${BASE}/api/optimizer/proposals/${id}/rollback`);
  return data;
}

export async function getPlaybook(): Promise<PlaybookInfo> {
  const { data } = await axios.get<PlaybookInfo>(`${BASE}/api/optimizer/playbook`);
  return data;
}

export async function startOptimizer(): Promise<OptimizerStatus> {
  const { data } = await axios.post<OptimizerStatus>(`${BASE}/api/optimizer/run`);
  return data;
}

export async function getOptimizerStatus(): Promise<OptimizerStatus> {
  const { data } = await axios.get<OptimizerStatus>(`${BASE}/api/optimizer/status`);
  return data;
}
