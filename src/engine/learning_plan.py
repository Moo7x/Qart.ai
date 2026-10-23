"""Learning plan (pathway.md §4): one pure, deterministic function, `build_learning_plan`.

The ordered skills gap of the chosen role (ranking.skills_gap) decides WHAT to learn and in which
order; this decides HOW (which course), WHEN (which weeks) and AT WHAT COST.
  1. Cost to the person (§4.1): free 0; free-if-eligible 0 for eligible people; HRD-claimable 0
     only when they are employed and their employer is HRD Corp-registered (approval is never
     promised); otherwise the listed price, or unknown. Unknown is never counted as free.
  2. Filters (§4.2): exclude a course only when a KNOWN answer breaks its eligibility ("Prefer not
     to say" keeps it, with a note); the budget; and the level the course starts from.
  3. Choice (§4.3): up to two courses per skill, a single one when it covers the whole step;
     a declared score (cost, format, certificate, language, self-paced, shorter), ties on cost,
     hours, id; the next two are kept as alternatives for "Swap".
  4. Order (§4.4): AI comfort at or below 3 puts an AI-literacy course first (AI untuk Rakyat only
     for people known to be eligible); otherwise the gap order, moved so a skill never comes
     before its prerequisites.
  5. Schedule (§4.5): hours × (1 + practice buffer) packed into weeks at the person's weekly hours,
     a hands-on milestone after each core skill and at least every 4 weeks, and every step past
     the timeframe kept in a "Next phase", never cut.
No I/O, no network, no randomness, no LLM: `plan_for_profile` (below) loads the inputs.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.contract import Course, Profile, SkillState
from src.engine.catalogue import CATALOGUE_DIR, SkillInfo, default_catalogue
from src.engine.questionnaire import Questionnaire, default_questionnaire
from src.engine.ranking import GapItem, ScoringConfig, default_scoring, rank_for_profile
from src.engine.resources import Milestone, MilestoneCatalogue, default_milestones, plan_courses

PLAN_PATH = CATALOGUE_DIR / "plan.json"
AI_LITERACY = "ai_literacy"
LEVEL_WORDS = {0.0: "none", 0.3: "heard of it", 0.7: "use sometimes", 1.0: "confident"}


class ScoreWeights(BaseModel):
    free: float
    cheap: float
    cheap_limit_myr: float
    format_match: float
    certificate: float
    language_match: float
    self_paced: float
    shorter_max: float
    employer_funded: float  # HRD-claimable, for people who asked their employer to pay


class PlanConfig(BaseModel):
    level_slack: float
    max_courses_per_skill: int
    alternatives: int
    max_overshoot: float  # × the gap's estimated hours
    score: ScoreWeights
    practice_buffer: float
    milestone_every_weeks: int
    ai_comfort_low: int
    formats: dict[str, str]  # questionnaire label -> course format id
    age_bands: dict[str, tuple[int, int]]


@lru_cache(maxsize=1)
def default_plan_config(path: Path = PLAN_PATH) -> PlanConfig:
    return PlanConfig.model_validate_json(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class PlanAnswers:
    """The questionnaire answers the plan reads."""

    weekly_hours: float
    timeframe_weeks: int
    timeframe_months: int
    ai_comfort: int | None = None
    formats: tuple[str, ...] = ()  # course format ids
    wants_certificate: bool = False
    language: str | None = None  # en / ms / either
    employment: str | None = None
    employer_hrd: str | None = None  # yes / no / not_sure
    budget: str | None = None  # free_only / up_to_200 / employer_pays
    budget_limit_myr: float = 200
    age_band: str | None = None
    malaysian: str | None = None  # yes / no / prefer_not


@dataclass(frozen=True)
class Cost:
    to_user: float | None  # None = no price known
    possibly_covered: float  # listed price an HRD-registered employer might cover
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanStep:
    order: int
    kind: str  # "course" | "milestone" | "no_resource"
    skill_ids: list[str]
    resource_id: str | None
    title: str
    provider: str | None
    url: str | None
    from_level: float | None
    to_level: float | None
    hours: float  # planned hours (course hours + practice buffer)
    start_week: int
    end_week: int
    in_timeframe: bool
    cost_to_user_myr: float | None
    cost_type: str | None
    hrd_claimable: bool
    certificate: bool | None
    formats: list[str]
    reasons: list[str]
    alternatives: list[str]
    last_verified: str | None
    status: str | None
    case_id: str | None = None
    date_to_confirm: bool = False


@dataclass(frozen=True)
class PlanSummary:
    total_hours: float
    weeks_needed: int
    fits_timeframe: bool
    timeframe_weeks: int
    cost_to_user_myr: float
    steps_with_unknown_cost: int
    cost_possibly_covered_by_employer_myr: float
    certificates: int
    free_steps: int
    hrd_claimable_steps: int


@dataclass(frozen=True)
class LearningPlan:
    role_id: str
    steps: list[PlanStep]
    summary: PlanSummary
    action_items: list[str] = field(default_factory=list)
    gaps_without_resources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Pick:
    course: Course
    skill_id: str
    from_level: float
    to_level: float
    cost: Cost
    score: float
    alternatives: list[str]
    reason_bits: list[str]


# --- 1. Cost and 2. filters ------------------------------------------------------------------


def eligibility_check(course: Course, a: PlanAnswers, cfg: PlanConfig) -> tuple[bool, list[str]]:
    """(allowed, notes). Only a KNOWN answer that breaks a limit excludes a course."""
    e, notes = course.eligibility, []
    if e.malaysian_only:
        if a.malaysian == "no":
            return False, []
        if a.malaysian != "yes":
            notes.append(f"{course.title} is for Malaysian citizens.")
    if e.min_age is not None or e.max_age is not None:
        band = cfg.age_bands.get(a.age_band or "")
        low, high = e.min_age or 0, e.max_age or 200
        if band is not None and (band[1] < low or band[0] > high):
            return False, []
        if band is None:
            notes.append(f"{course.title} is for people aged {low}–{high}.")
    if e.employment and a.employment is not None and a.employment not in e.employment:
        return False, []
    return True, notes


def eligible_known(course: Course, a: PlanAnswers, cfg: PlanConfig) -> bool:
    """True only when every limit is met by a known answer (used for AI untuk Rakyat)."""
    e = course.eligibility
    if e.malaysian_only and a.malaysian != "yes":
        return False
    if e.min_age is not None or e.max_age is not None:
        band = cfg.age_bands.get(a.age_band or "")
        if band is None or band[0] < (e.min_age or 0) or band[1] > (e.max_age or 200):
            return False
    return True


def cost_to_user(course: Course, a: PlanAnswers) -> Cost:
    """pathway.md §4.1, row by row."""
    listed = course.cost_myr
    kind = course.cost_type or "unknown"
    if kind == "free":
        return Cost(0.0, 0.0)
    if kind == "free_if_eligible":
        return Cost(0.0, 0.0, (f"Free if you are eligible: {course.cost_note or ''}".strip(),))
    if kind == "hrd_claimable":
        if a.employment == "employed" and a.employer_hrd == "yes":
            return Cost(
                0.0,
                listed or 0.0,
                (
                    "Covered by your employer's HRD Corp levy if approved. HR applies via "
                    "e-TRiS before the course starts.",
                ),
            )
        if a.employment == "employed" and a.employer_hrd == "not_sure":
            return Cost(
                listed,
                listed or 0.0,
                ("May be claimable. Ask your HR if your company is HRD Corp-registered.",),
            )
        return Cost(listed, 0.0)
    if kind == "low_cost":
        return Cost(listed, 0.0)
    return Cost(None, 0.0, (f"{course.title}: no price stated on its page.",))


def within_budget(course: Course, cost: Cost, a: PlanAnswers) -> bool:
    if a.budget is None:
        return True
    if a.budget == "free_only":
        return cost.to_user == 0
    if a.budget == "up_to_200":
        return cost.to_user is not None and cost.to_user <= a.budget_limit_myr
    if a.budget == "employer_pays":
        return cost.to_user == 0 or course.hrd_claimable
    return True


def covers(
    course: Course, skill_id: str, level: float, cfg: PlanConfig
) -> tuple[float, float] | None:
    """(from, to) of the course's step for this skill when it fits the person's level."""
    for s in course.skill_steps:
        if s.id == skill_id and s.from_level <= level + cfg.level_slack and s.to_level > level:
            return s.from_level, s.to_level
    return None


# --- 3. Choosing courses ----------------------------------------------------------------------


def _score(
    course: Course, cost: Cost, a: PlanAnswers, cfg: PlanConfig, shortest: float, longest: float
) -> tuple[float, list[str]]:
    w, bits, score = cfg.score, [], 0.0
    if cost.to_user == 0:
        score += w.free
        bits.append(
            "free if you are eligible" if course.cost_type == "free_if_eligible" else "free"
        )
    elif cost.to_user is not None and cost.to_user <= w.cheap_limit_myr:
        score += w.cheap
        bits.append(f"RM{cost.to_user:g}")
    wants_employer = a.budget == "employer_pays" and a.employment == "employed"
    if course.hrd_claimable and wants_employer and a.employer_hrd in ("yes", "not_sure"):
        score += w.employer_funded
        bits.append("employer-funded through HRD Corp, as you asked")
    matching = [f for f in course.format if f in a.formats]
    if matching:
        score += w.format_match
        bits.append(f"matches your {matching[0].replace('_', '-')} preference")
    if a.wants_certificate and course.certificate:
        score += w.certificate
        bits.append("certificate")
    if a.language in ("en", "ms") and a.language in course.language:
        score += w.language_match
        bits.append("in Bahasa Malaysia" if a.language == "ms" else "in English")
    if course.delivery == "self_paced":
        score += w.self_paced
    if longest > shortest:
        score += w.shorter_max * (longest - course.hours) / (longest - shortest)
    return round(score, 4), bits


def _candidates(
    skill_id: str,
    level: float,
    courses: Sequence[Course],
    a: PlanAnswers,
    cfg: PlanConfig,
    used: set[str],
) -> list[_Pick]:
    found = []
    for c in courses:
        step = covers(c, skill_id, level, cfg)
        if step is None:
            continue
        allowed, notes = eligibility_check(c, a, cfg)
        cost = cost_to_user(c, a)
        if not allowed or not within_budget(c, cost, a):
            continue
        found.append((c, step, Cost(cost.to_user, cost.possibly_covered, (*cost.notes, *notes))))
    if not found:
        return []
    hours = [c.hours for c, _, _ in found]
    picks = []
    for c, (frm, to), cost in found:
        score, bits = _score(c, cost, a, cfg, min(hours), max(hours))
        if c.id in used:  # a course already in the plan teaches this skill at no extra time
            score += 100
        picks.append(_Pick(c, skill_id, frm, to, cost, score, [], bits))
    picks.sort(key=_pick_order)
    return picks


def _pick_order(p: _Pick) -> tuple[float, float, float, str]:
    """Higher score first, then lower cost (unknown last), fewer hours, id A–Z."""
    price = math.inf if p.cost.to_user is None else p.cost.to_user
    return (-p.score, price, p.course.hours, p.course.id)


def choose_for_skill(
    item: GapItem,
    courses: Sequence[Course],
    a: PlanAnswers,
    cfg: PlanConfig,
    used: set[str],
    pin: str | None = None,
) -> list[_Pick]:
    """Up to `max_courses_per_skill` courses taking the skill to the required level, in order.
    A single course that reaches the level wins over a chain. `pin` (from "Swap") is a course the
    person chose for this skill: it is used first when it passes the filters."""
    chain: list[_Pick] = []
    level = item.current_level
    for _ in range(cfg.max_courses_per_skill):
        cands = _candidates(
            item.skill_id, level, courses, a, cfg, used | {p.course.id for p in chain}
        )
        cands = [p for p in cands if p.course.id not in {q.course.id for q in chain}]
        if not cands:
            break
        # A course far bigger than the need (e.g. a 180 h certificate for a 15 h gap) is used only
        # when nothing shorter covers the skill; it still shows up as an alternative.
        limit = cfg.max_overshoot * max(item.hours, 1.0)
        fitting = [p for p in cands if p.course.hours <= limit]
        if not fitting and chain:  # a second course must fit too; otherwise stop with a note
            break
        pool = fitting or cands
        reaching = [p for p in pool if p.to_level >= item.required_level]
        pinned = next((p for p in cands if p.course.id == pin), None) if not chain else None
        best = pinned or (
            reaching[0] if reaching else max(pool, key=lambda p: (p.to_level, p.score))
        )
        others = [p.course.id for p in cands if p is not best][: cfg.alternatives]
        chain.append(
            _Pick(
                best.course,
                best.skill_id,
                best.from_level,
                best.to_level,
                best.cost,
                best.score,
                others,
                best.reason_bits,
            )
        )
        level = best.to_level
        if level >= item.required_level:
            break
    return chain


# --- 4. Order ---------------------------------------------------------------------------------


def prerequisite_order(
    gap: Sequence[GapItem], vocabulary: Mapping[str, SkillInfo]
) -> list[GapItem]:
    """Keep the gap order, but never place a skill before a prerequisite that is also in the gap."""
    in_gap = {g.skill_id for g in gap}
    placed: list[GapItem] = []
    done: set[str] = set()
    pending = list(gap)
    while pending:
        for g in pending:
            needs = {p for p in vocabulary[g.skill_id].prerequisites if p in in_gap}
            if needs <= done:
                placed.append(g)
                done.add(g.skill_id)
                pending.remove(g)
                break
        else:  # a cycle (the vocabulary test forbids it): keep the remaining order
            placed.extend(pending)
            break
    return placed


def ai_literacy_first(courses: Sequence[Course], a: PlanAnswers, cfg: PlanConfig) -> _Pick | None:
    """At AI comfort ≤ 3: AI untuk Rakyat-style programmes only for people known to be eligible,
    otherwise the best AI-literacy course open to everyone (still within budget)."""
    if a.ai_comfort is None or a.ai_comfort > cfg.ai_comfort_low:
        return None
    pool = [c for c in courses if AI_LITERACY in c.tags]
    limited = [c for c in pool if c.eligibility.malaysian_only or c.eligibility.max_age is not None]
    eligible = [
        c for c in limited if eligible_known(c, a, cfg) and within_budget(c, cost_to_user(c, a), a)
    ]
    open_all = [c for c in pool if c not in limited and within_budget(c, cost_to_user(c, a), a)]
    chosen = eligible or open_all
    if not chosen:
        return None
    hours = [c.hours for c in chosen]
    ranked = sorted(
        chosen,
        key=lambda c: (
            -_score(c, cost_to_user(c, a), a, cfg, min(hours), max(hours))[0],
            c.hours,
            c.id,
        ),
    )
    c = ranked[0]
    step = c.skill_steps[0]
    score, bits = _score(c, cost_to_user(c, a), a, cfg, min(hours), max(hours))
    return _Pick(
        c,
        step.id,
        step.from_level,
        step.to_level,
        cost_to_user(c, a),
        score,
        [x.id for x in ranked[1:3]],
        bits,
    )


# --- 5. Schedule ------------------------------------------------------------------------------


def _word(level: float | None) -> str:
    return LEVEL_WORDS.get(round(level or 0, 1), f"{level:g}")


def _milestone_for(skill_id: str, catalogue: MilestoneCatalogue, used: set[str]) -> Milestone:
    for m in catalogue.milestones:
        if skill_id in m.skills and m.id not in used:
            return m
    return catalogue.default


@dataclass
class _Entry:
    """One thing to schedule: a chosen course, a gap with no course, or a milestone slot."""

    kind: str  # "course" | "no_resource" | "milestone_after"
    pick: _Pick | None = None
    item: GapItem | None = None
    skills: list[str] = field(default_factory=list)
    intro: bool = False


class _Clock:
    """Packs steps one after another into weeks of `weekly_hours` (a step may span weeks)."""

    def __init__(self, weekly_hours: float) -> None:
        self.weekly = weekly_hours
        self.hours = 0.0

    def place(self, hours: float) -> tuple[int, int]:
        start = int(self.hours // self.weekly) + 1
        self.hours += hours
        return start, max(start, math.ceil(self.hours / self.weekly))


def _no_resource_step(
    item: GapItem, order: int, clock: _Clock, a: PlanAnswers, cfg: PlanConfig
) -> PlanStep:
    """A gap item with no matching course stays visible, with its estimated hours (§4.2)."""
    hours = round(item.hours * (1 + cfg.practice_buffer), 1)
    start, end_week = clock.place(hours)
    return PlanStep(
        order=order,
        kind="no_resource",
        skill_ids=[item.skill_id],
        resource_id=None,
        title=f"{item.label}: no matching course in our catalogue yet",
        provider=None,
        url=None,
        from_level=item.current_level,
        to_level=item.required_level,
        hours=hours,
        start_week=start,
        end_week=end_week,
        in_timeframe=end_week <= a.timeframe_weeks,
        cost_to_user_myr=None,
        cost_type=None,
        hrd_claimable=False,
        certificate=None,
        formats=[],
        reasons=[f"Estimated ~{item.hours:g} h from the skill's learning-hours estimate."],
        alternatives=[],
        last_verified=None,
        status=None,
    )


def _course_step(
    entry: _Entry,
    order: int,
    clock: _Clock,
    a: PlanAnswers,
    cfg: PlanConfig,
    vocabulary: Mapping[str, SkillInfo],
) -> tuple[PlanStep, list[str], list[str]]:
    """The step, its action items and its cost notes, with template reasons (§4.7)."""
    pick = entry.pick
    assert pick is not None
    c = pick.course
    hours = round(c.hours * (1 + cfg.practice_buffer), 1)
    start, end_week = clock.place(hours)
    weeks = f"week {start}" if start == end_week else f"weeks {start}–{end_week}"
    takes = (
        f"takes {vocabulary[pick.skill_id].name} from '{_word(pick.from_level)}' "
        f"to '{_word(pick.to_level)}'"
    )
    detail = [*pick.reason_bits, takes, weeks]
    reasons = [" · ".join([detail[0][:1].upper() + detail[0][1:], *detail[1:]])]
    if entry.intro:
        reasons.append(f"Placed first: you rated your comfort with AI tools {a.ai_comfort}/10.")
    elif pick.alternatives:
        n = len(pick.alternatives)
        why = " and ".join(pick.reason_bits[:2]) or "it is the shortest fit"
        reasons.append(f"Chosen over {n} alternative{'s' if n > 1 else ''} because {why}.")
    actions = []
    if c.delivery == "scheduled":
        employed = c.hrd_claimable and a.employment == "employed"
        if employed and a.employer_hrd == "yes":
            actions.append(
                f"Ask HR to apply for the HRD Corp grant via e-TRiS before {c.title} starts."
            )
        elif employed and a.employer_hrd == "not_sure":
            actions.append(
                "Ask HR whether your company is HRD Corp-registered; if it is, ask them to apply "
                f"for the grant via e-TRiS before {c.title} starts."
            )
        else:
            actions.append(f"Register for the next intake of {c.title}.")
    step = PlanStep(
        order=order,
        kind="course",
        skill_ids=list(entry.skills),
        resource_id=c.id,
        title=c.title,
        provider=c.provider,
        url=c.url,
        from_level=pick.from_level,
        to_level=pick.to_level,
        hours=hours,
        start_week=start,
        end_week=end_week,
        in_timeframe=end_week <= a.timeframe_weeks,
        cost_to_user_myr=pick.cost.to_user,
        cost_type=c.cost_type,
        hrd_claimable=c.hrd_claimable,
        certificate=c.certificate,
        formats=list(c.format),
        reasons=reasons,
        alternatives=pick.alternatives,
        last_verified=c.last_verified,
        status=c.status,
        date_to_confirm=c.delivery == "scheduled",
    )
    return step, actions, list(pick.cost.notes)


def build_learning_plan(
    role_id: str,
    gap: Sequence[GapItem],
    answers: PlanAnswers,
    courses: Sequence[Course],
    vocabulary: Mapping[str, SkillInfo],
    milestones: MilestoneCatalogue,
    cfg: PlanConfig,
    pins: Mapping[str, str] | None = None,
) -> LearningPlan:
    """The ordered, week-by-week plan for one role. Pure and deterministic.
    `pins` maps a skill id to the course the person swapped in for it."""
    entries: list[_Entry] = []  # what to schedule, in order
    used: set[str] = set()
    notes: list[str] = []
    gaps_without: list[str] = []

    intro = ai_literacy_first(courses, answers, cfg)
    if intro:
        used.add(intro.course.id)
        entries.append(_Entry("course", pick=intro, skills=[intro.skill_id], intro=True))

    for item in prerequisite_order(gap, vocabulary):
        chain = choose_for_skill(item, courses, answers, cfg, used, (pins or {}).get(item.skill_id))
        if not chain:
            gaps_without.append(item.label)
            entries.append(_Entry("no_resource", item=item))
        for pick in chain:
            same = next((e for e in entries if e.pick and e.pick.course.id == pick.course.id), None)
            if same is not None:  # the same course covers another gap skill: no extra time
                same.skills.append(item.skill_id)
                continue
            used.add(pick.course.id)
            entries.append(_Entry("course", pick=pick, skills=[item.skill_id], item=item))
        if chain and chain[-1].to_level < item.required_level:
            notes.append(
                f"{item.name}: the catalogue takes you to '{_word(chain[-1].to_level)}', short of "
                f"'{_word(item.required_level)}'; practise on real work to close the rest."
            )
        if item.is_core:
            entries.append(_Entry("milestone_after", item=item))

    steps: list[PlanStep] = []
    action_items: list[str] = []
    clock = _Clock(answers.weekly_hours)
    last_milestone_end = 0.0
    used_milestones: set[str] = set()

    def add_milestone(skill_id: str) -> None:
        nonlocal last_milestone_end
        if steps and steps[-1].kind == "milestone":  # never two milestones in a row
            return
        m = _milestone_for(skill_id, milestones, used_milestones)
        used_milestones.add(m.id)
        start, end_week = clock.place(m.hours)
        last_milestone_end = clock.hours
        steps.append(
            PlanStep(
                order=len(steps) + 1,
                kind="milestone",
                skill_ids=list(m.skills),
                resource_id=m.id,
                title=m.title,
                provider="Qart practice case" if m.case_id else None,
                url=None,
                from_level=None,
                to_level=None,
                hours=m.hours,
                start_week=start,
                end_week=end_week,
                in_timeframe=end_week <= answers.timeframe_weeks,
                cost_to_user_myr=0.0,
                cost_type="free",
                hrd_claimable=False,
                certificate=None,
                formats=["hands_on"],
                reasons=["Hands-on practice to use what you just learned."],
                alternatives=[],
                last_verified=None,
                status=None,
                case_id=m.case_id,
            )
        )

    for entry in entries:
        if entry.kind == "milestone_after" and entry.item:
            add_milestone(entry.item.skill_id)
        elif entry.kind == "no_resource" and entry.item:
            steps.append(_no_resource_step(entry.item, len(steps) + 1, clock, answers, cfg))
        elif entry.pick:
            step, actions, cost_notes = _course_step(
                entry, len(steps) + 1, clock, answers, cfg, vocabulary
            )
            steps.append(step)
            action_items.extend(a for a in actions if a not in action_items)
            notes.extend(n for n in cost_notes if n not in notes)
            weeks_since = (clock.hours - last_milestone_end) / answers.weekly_hours
            if weeks_since >= cfg.milestone_every_weeks:
                add_milestone(entry.pick.skill_id)

    total = round(sum(s.hours for s in steps), 1)
    weeks_needed = max((s.end_week for s in steps), default=0)
    courses_only = [s for s in steps if s.kind == "course"]
    by_id = {c.id: c for c in courses}
    summary = PlanSummary(
        total_hours=total,
        weeks_needed=weeks_needed,
        fits_timeframe=weeks_needed <= answers.timeframe_weeks,
        timeframe_weeks=answers.timeframe_weeks,
        cost_to_user_myr=round(sum(s.cost_to_user_myr or 0 for s in courses_only), 2),
        steps_with_unknown_cost=sum(1 for s in courses_only if s.cost_to_user_myr is None),
        cost_possibly_covered_by_employer_myr=round(
            sum(
                cost_to_user(by_id[s.resource_id], answers).possibly_covered
                for s in courses_only
                if s.resource_id in by_id
            ),
            2,
        ),
        certificates=sum(1 for s in courses_only if s.certificate),
        free_steps=sum(1 for s in courses_only if s.cost_to_user_myr == 0),
        hrd_claimable_steps=sum(1 for s in courses_only if s.hrd_claimable),
    )
    return LearningPlan(role_id, steps, summary, action_items, gaps_without, notes)


# --- Loading the inputs (I/O lives here, outside the pure function) --------------------------


def plan_answers_for(
    profile: Profile, q: Questionnaire, scoring: ScoringConfig, cfg: PlanConfig
) -> PlanAnswers:
    prefs = profile.preferences
    months = prefs.timeframe_months or scoring.default_timeframe_months
    return PlanAnswers(
        weekly_hours=profile.weekly_learning_hours,
        timeframe_weeks=scoring.timeframe_weeks[str(months)],
        timeframe_months=months,
        ai_comfort=prefs.ai_comfort,
        formats=tuple(cfg.formats[f] for f in prefs.formats if f in cfg.formats),
        wants_certificate=bool(prefs.wants_certificate),
        language=prefs.language,
        employment=prefs.employment,
        employer_hrd=prefs.employer_hrd,
        budget=prefs.budget,
        budget_limit_myr=q.funding.budget_limit_myr,
        age_band=prefs.age_band,
        malaysian=prefs.malaysian,
    )


def plan_for_profile(
    profile: Profile,
    role_id: str | None = None,
    states: list[SkillState] | None = None,
    snapshot: Mapping[str, object] | None = None,
    scenario: str | None = None,
    include_drafts: bool | None = None,
    pins: Mapping[str, str] | None = None,
) -> LearningPlan | None:
    """The plan for `role_id` (default: the top-ranked role); None for an empty profile."""
    ranking = rank_for_profile(profile, states, snapshot, scenario)
    if ranking.empty_profile or not ranking.roles:
        return None
    role = next((r for r in ranking.roles if r.role_id == role_id), ranking.roles[0])
    catalogue = default_catalogue()
    cfg = default_plan_config()
    return build_learning_plan(
        role.role_id,
        role.gap,
        plan_answers_for(profile, default_questionnaire(), default_scoring(), cfg),
        plan_courses(catalogue, include_drafts),
        catalogue.vocabulary,
        default_milestones(),
        cfg,
        pins,
    )
