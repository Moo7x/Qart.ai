"""Exact version of the robust path selection with OR-Tools CP-SAT (same model as planner.py).

  x_i ∈ {0,1};  Σ hours_i·x_i ≤ budget;  x_course ≤ x_prerequisite
  g_{sc,k} ≥ remaining_k − Σ_i gain_{i,k}·x_i,  g ≥ 0
  z ≥ Σ_k w_{sc,k}·g_{sc,k}  for each scenario
  minimise z, then total hours (so ties use less of the employee's time)
CP-SAT needs integers, so values are scaled (SCALE) and rounded; results are compared with the
greedy plan in tests. Greedy stays the default because it is easier to explain step by step.
"""

from collections.abc import Sequence

from ortools.sat.python import cp_model

from src.contract import SCENARIOS
from src.engine.planner import PlanInputs, Resource

SCALE = 1000  # 3 decimals of precision for gaps, gains and weights
HOUR_SCALE = 10  # hours are multiples of 0.1 in the catalogue
SOLVER_TIME_LIMIT_SECONDS = 5.0  # small model; the limit only guards the demo


def cpsat_select(
    inputs: PlanInputs, resources: Sequence[Resource], budget_hours: float
) -> list[Resource]:
    """Optimal selection under the scaled integer model (falls back to [] if infeasible)."""
    model = cp_model.CpModel()
    x = {r.id: model.new_bool_var(f"x_{r.id}") for r in resources}
    model.add(
        sum(round(r.hours * HOUR_SCALE) * x[r.id] for r in resources)
        <= round(budget_hours * HOUR_SCALE)
    )
    for r in resources:
        for prerequisite in r.prerequisites:
            if prerequisite in x:
                model.add_implication(x[r.id], x[prerequisite])

    skills = sorted({k for sc in SCENARIOS for k in inputs.weights[sc]})
    gaps = {}
    for k in skills:
        remaining = round(inputs.remaining.get(k, 0.0) * SCALE)
        gap = model.new_int_var(0, SCALE, f"g_{k}")
        covered = sum(round(r.gains.get(k, 0.0) * SCALE) * x[r.id] for r in resources)
        model.add(gap >= remaining - covered)
        gaps[k] = gap
    worst = model.new_int_var(0, SCALE * SCALE, "worst")
    for sc in SCENARIOS:
        model.add(
            worst >= sum(round(inputs.weights[sc].get(k, 0.0) * SCALE) * gaps[k] for k in skills)
        )
    total_hours = sum(round(r.hours * HOUR_SCALE) * x[r.id] for r in resources)
    max_hours = sum(round(r.hours * HOUR_SCALE) for r in resources) + 1
    model.minimize(worst * max_hours + total_hours)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []
    return [r for r in resources if solver.boolean_value(x[r.id])]
