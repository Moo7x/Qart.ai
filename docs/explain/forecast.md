# Qart's own forecast (src/forecast/)

**What it answers:** which GBS finance roles and skills are growing, transforming, shrinking or
emerging, under moderate or fast AI adoption, with the evidence and the method behind each.

## The three parts

1. **Task-level AI-use model** (`task_model.py`). The Anthropic Economic Index tells us, for about
   2,700 O*NET tasks, what share of AI conversations about the task are *automation-style* (the AI
   does the task) rather than *augmentation-style* (the AI helps a person). Most tasks of our
   occupations are not in that list. The model learns from the observed tasks how wording relates
   to that share, and predicts it for the 320 task statements of our 17 occupations.
   - Features: each task statement turned into a BGE-M3 vector on RunPod (TF-IDF word features when
     RunPod is unavailable; the version records which).
   - Candidates: ridge regression, random forest, gradient boosting, LightGBM, XGBoost, and the
     average as a baseline. 5-fold cross-validation scores each by mean absolute error. The best
     one is used only if it beats the baseline by 5%.
   - Observed values always come first; a predicted value is shown as an estimate.
   - Stored per version (`task_model_version`, `task_prediction`), re-fitted only when the data
     change; the pipeline runs it after collection.
2. **Demand** (reuses `src/evidence/forecast.py`). Each DOSM occupation group's share of
   employees is forecast two years ahead by the model that won a rolling backtest against keeping
   the last value (naive, drift, linear, damped, smoothing, theta, gradient boosting).
3. **Industry view** (`industry.py`). Each of the 26 roles in `industry_roles.yaml` is measured
   through its O*NET occupation:
   - AI pressure = three kinds kept apart: AI use (importance-weighted, scaled by the scenario),
     ILO exposure, TalentCorp impact. *Transforming* needs two of them to agree.
   - *Shrinking* = transforming and its job group forecast to fall by more than 0.2 points.
   - *Growing* = not transforming, and its group forecast to rise or MyCOL lists it as hard to fill.
   - *Emerging* = TalentCorp's emerging roles. *Stable* = otherwise.
   - Skills: a skill's demand is the weighted demand of the roles that need it; its AI use is the
     mean over the tasks linked to it. Routine skills that AI already does are *declining*,
     AI-complementing skills are *rising*.

## How to answer the judges

- "Is this a real prediction?" Yes: a trained model with a measured error (shown on screen), and
  backtested time-series forecasts. Both are labelled estimates.
- "Change the data": a new Economic Index month re-fits the model; a new DOSM year re-forecasts
  demand; both change categories. Switching to fast AI moves roles at once.
- "Why only two years?" The DOSM series is comparable from 2016, about ten points per group.
