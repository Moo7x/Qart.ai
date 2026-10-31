# Agents: the resource scout

**What it does.** For one skill the person still needs, the scout finds the exact part of a
checked video or article that serves it: a YouTube link that starts at the right second, or an
article link that opens at the right passage (`#:~:text=`). It finds and points; it does not
teach. Open it from My plan: the AI-brain button beside each video and each checked article (web
pages and sites that refuse readers get no button, `TrackArticle.is_article`).

**How it works.** One agent on `AGENT_MODEL` (gpt-4.1-mini) with four code tools
(`src/agents/scout.py`):
1. `list_resources`: the videos and articles the pack has checked for the skill;
2. `read_video`: captions (youtube-transcript-api) cut into 30–90 s segments, ranked for the skill
   by bge-reranker-v2-m3 on RunPod (`src/agents/segments.py`);
3. `read_article`: page text (trafilatura) cut into passages, ranked the same way; sign-up and
   cookie banners are dropped;
4. `finish`: up to three parts, each with a one-line reason.

The agent only chooses what to read and writes the reasons. Code fetches, cuts and ranks, keeps
only parts a tool really returned, drops any reason containing a number, and builds every link.
Limits: 8 tool calls, 45 s (`src/params.py`). Every step is stored (`agent_run`, `agent_step`) as
it happens and the window reads it every 0.8 s, so the person watches the agent work.

**Character.** The agent's voice and rules live in `data/agents/scout.character.yaml`, in the
spirit of ElizaOS character files (who it is, its style, what it must and must never do, example
exchanges). `src/agents/character.py` checks the file and builds the system prompt from it. The
model is not fine-tuned.

**Fallbacks, each labelled.** No language model, or no valid picks: the best-ranked part of each
resource ("ranking only"). No RunPod: word-overlap ranking. YouTube often refuses caption requests
from cloud servers, so `python -m src.agents.scout --cache` pre-checks every skill from a normal
connection and stores times, link anchors and reasons in `data/agents/scout_cache.yaml`; a refused
live run uses them, labelled "checked on <date>". No caption or article text is stored.

## The progress check

**What it does.** A senior GBS finance reviewer (character:
`data/agents/progress_check.character.yaml`) asks two to four questions, one at a time, about work
the person has done, then proposes a level. The API (`/api/profiles/{id}/checks`) remains, but no
page opens it since 2026-11-01 (removed from the Overview at the user's request).

**How a level is proposed** (`src/agents/check.py`). The model judges each level above the
current one as yes / partly / no and quotes the person's words; it never writes the level. Code
keeps a judgement only if its quote really is in the answers, then rises one level at a time
while the next level is "yes" ("partly" stops the climb), at most two levels. The person keeps
the proposed level or their current one; a kept level is stored as a claim with source
`agent_check`, the quotes as evidence, the time and the model, never as "verified". Three checks
per skill per day, so it cannot be retried until it agrees. Until owner B publishes per-skill
level descriptions (`levels.yaml`), it judges against the general level meanings and says so.

**Measured.** A live check on Reporting and Documentation (claimed level 2) asked four questions,
judged level 3 "partly" and level 4 "no" with the person's own quotes, so the level stayed at 2.

**Judge questions.** *Is this real?* Every link opens the original resource at that point; the
resources are the pack's checked list. *Can it invent a video or a timestamp?* No: picks the
tools did not return are dropped, and times and links come from code. *Measured?* A live run on
Reporting and Documentation read two videos and an article in about 50 s and returned three parts.
