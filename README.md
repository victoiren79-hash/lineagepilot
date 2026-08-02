# LineagePilot

**An agent that understands *why* a schema change breaks your code — not just that it does.**

Built for [Build with DataHub: The Agent Hackathon](https://datahub.devpost.com/).

## The Problem

DataHub's lineage graph already shows you the blast radius of a schema change — which downstream tables, models, and pipelines depend on a column. What it doesn't do is explain *why* a given change is safe or dangerous for each of those consumers, generate the actual fix, or coordinate getting that fix reviewed and merged. That gap is still a manual, error-prone process today.

**LineagePilot closes that gap, automatically.** A watcher process listens to DataHub's live event stream. The moment it detects a column rename, it runs the full pipeline on its own — no one has to tell it what changed or which script to run:

1. Detects the change via DataHub's Actions Framework, and infers that it's a rename (see "How rename detection works" below for exactly how)
2. Walks DataHub's column-level lineage to find every downstream consumer
3. Uses an LLM (via Groq) to reason about *how* each consumer uses the changed column — a simple reference, a join key, part of an aggregation — and classifies the risk accordingly
4. Generates the actual corrected code for each consumer
5. Opens a GitHub Pull Request with the fix — **auto-merging low-risk changes**, and **leaving high-risk changes for human review** with the reasoning attached
6. Writes a permanent migration history record back into DataHub, so the next person or agent who looks at that entity inherits the full context of what changed and why

## Why AI, not a script

A plain script can find where a string appears. It can't tell that a column used inside a `JOIN` or `GROUP BY` needs a different, more careful fix than a column that's just selected and displayed — or that the same textual change (a rename) carries very different risk depending on how it's used downstream. LineagePilot's reasoning step reads the actual downstream code alongside the lineage context and makes that judgment call, then explains it in plain English.

## Architecture

```
Schema change on any tracked table (DataHub)
        |
        v
watcher.py -- listens to DataHub's Actions Framework event stream,
              infers whether the change is a rename (see below)
        |
        v  (auto-triggered, no manual step)
main.py: run_pipeline() orchestrates the rest --
        |
        v
Lineage lookup (lineage_lookup.py) --> finds downstream datasets via DataHub GraphQL
        |
        v
Reasoning engine (reasoning_engine.py) --> Groq LLM classifies risk per file
        |
        v
Diff generator (diff_generator.py) --> produces the corrected file + diff
        |
        v
GitHub PR poster (github_pr.py) --> opens PR, auto-merges if LOW risk
        |
        v
DataHub write-back (write_back.py) --> saves migration history to the entity
```

`watcher.py` is the entry point for real usage — start it once and leave it
running; it calls everything else automatically. `main.py` can also be run
directly for a one-off manual test against a known column, but that's not
the intended normal workflow.

## How rename detection works (and its real limitation)

DataHub's schema-change events don't have a native "this was a rename"
concept — only "a field was added" and "a field was removed." `watcher.py`
infers a rename when it sees **exactly one field added and one field
removed on the same table in the same event**, and treats those as the
old and new name of the same column. If a schema change doesn't fit that
pattern (multiple fields changing at once, a pure add, or a pure delete),
the watcher prints what it saw but does **not** guess at a rename — because
acting on an incorrect guess is worse than asking a human to run it
manually with the correct column names. This mirrors the same
confidence-based philosophy as the risk-based PR auto-merge: act
automatically when confident, defer when not.

Fix generation itself is scoped to the two downstream files this demo
dataset tracks (`models/stg_orders_v2.sql` and `models/fct_revenue_v2.sql`,
mapped via `URN_TO_FILE` in `main.py`). Detection works across your whole
DataHub instance; automatic fixing is currently limited to consumers this
demo knows about. Extending `URN_TO_FILE` to be driven by DataHub's own
metadata instead of a hardcoded map is the natural next step — see
"What's next" in the project story.

## Demo Data

This project uses a small hand-built demo dataset rather than DataHub's official `showcase-ecommerce` datapack, because that datapack's CLI loader currently has a [known bug on Windows](https://github.com/datahub-project/datahub/issues/11107). `seed_datahub.py` creates three tables locally with real column-level lineage:

- `raw_orders_v2` (source)
- `stg_orders_v2` (references `user_id` as a simple select — the "safe" case)
- `fct_revenue_v2` (uses `user_id` as a join key + in a `GROUP BY` — the "risky" case)

Two matching SQL files under `models/` represent the actual downstream code that gets fixed.

## Setup

Requires Python 3.11, Docker, and a local DataHub instance.

1. **Install dependencies:**
   ```bash
   py -3.11 -m pip install -r requirements.txt
   ```

2. **Start DataHub locally:**
   ```bash
   py -3.11 -m datahub docker quickstart
   ```
   Confirm it's running at `localhost:9002` (login: `datahub` / `datahub`).

3. **Seed the demo data:**
   ```bash
   py -3.11 seed_datahub.py
   ```

4. **Set up your own API keys:**
   - Copy `.env.example` to `.env`
   - Get a free Groq API key at [console.groq.com](https://console.groq.com) and add it as `GROQ_API_KEY`
   - Generate a GitHub personal access token (Settings → Developer settings → Personal access tokens → Tokens classic, `repo` scope only) and add it as `GITHUB_TOKEN`

5. **Point the app at your own test repo:**
   - Open `github_pr.py`, change `REPO_NAME` to your own `username/repo`

## Running the Demo

1. **Start the watcher** in its own terminal, and leave it running:
   ```bash
   py -3.11 watcher.py
   ```

2. **In a second terminal, trigger a real schema change.** Edit `seed_datahub.py`, rename any column on `raw_orders_v2` (e.g. `order_total` to `order_sum`), then re-run it:
   ```bash
   py -3.11 seed_datahub.py
   ```

3. **Watch the watcher's terminal.** It detects the rename and automatically runs the full pipeline — no other command needed. You'll see it:
   - Find both downstream datasets via lineage
   - Classify one file as **LOW risk** and the other as **HIGH risk**
   - Generate a fix for each
   - Open a PR for each — the low-risk one auto-merges, the high-risk one stays open for review with the reasoning attached as a comment
   - Write the full migration record back to the `raw_orders_v2` entity in DataHub, visible under its **Properties** tab

## What This Demonstrates for the Hackathon Challenge

- **Metadata-Aware Code Generation:** the generated fixes are real, correct code changes based on actual DataHub schema and lineage data, delivered as reviewable PRs — not just a report.
- **Use of DataHub beyond reading:** the pipeline reads column-level lineage and *writes back* a structured migration history record, so the graph accumulates institutional knowledge over time.

## License

Apache 2.0 — see [LICENSE](LICENSE).
