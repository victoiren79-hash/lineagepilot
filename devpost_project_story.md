# LineagePilot — Project Story

## Inspiration

DataHub already shows teams the blast radius of a schema change — which
downstream tables, dashboards, and pipelines depend on a column. But
knowing *what* breaks isn't the same as knowing *why* it breaks, or having
it actually fixed. That gap between "here's a list of affected systems"
and "here's a working fix, reviewed and ready to merge" is still closed by
hand today, usually under time pressure, right when something's on fire.
LineagePilot exists to close that gap automatically, using DataHub's own
lineage graph as the source of truth.

## What it does

LineagePilot watches a DataHub instance for schema changes — a column
rename, in this demo. When one happens, it doesn't just find what breaks —
it figures out *how* each downstream consumer depends on the changed
column, and responds differently to each one.

In our test run, the same rename produced two different, independently
justified outcomes: one file got a fix that was auto-merged immediately,
the other got a fix that was flagged and held for human review — because
the agent understood that one usage was a harmless display column and the
other was a join key sitting inside a revenue calculation.

Concretely, LineagePilot:

1. Detects the schema change the moment it happens, via DataHub's Actions Framework
2. Walks DataHub's column-level lineage to find every downstream consumer
3. Reads each downstream file alongside its lineage context and reasons
   about how that specific consumer depends on the changed column. Instead
   of blindly replacing every reference to a renamed column, it distinguishes
   a simple `SELECT` reference — safe to alias automatically — from a `JOIN`
   key or an aggregation, which gets a higher risk score and is routed for
   human review instead. That distinction is the core of the project: the
   fix isn't templated, it's justified.
4. Generates the actual corrected code for each affected file
5. Opens a real GitHub Pull Request per fix — low-risk fixes auto-merge
   immediately, high-risk fixes stay open for review with the reasoning
   written directly into the PR
6. Writes a permanent migration history record back into the DataHub
   entity itself, so the next person or agent who looks at that table
   inherits the full story instead of starting from zero

## How we built it

LineagePilot connects six systems into one loop: DataHub's schema-change
events, its lineage graph, an LLM reading real downstream code, generated
fixes, GitHub's PR workflow, and DataHub's own metadata store for the
write-back. Detection runs off DataHub's Actions Framework listening to
its Kafka event stream. Lineage traversal and the write-back both go
through DataHub's own APIs — GraphQL for reading, the Python SDK emitter
for writing. The only place an LLM is used is where genuine judgment is
required: reading a downstream file's actual code next to its lineage
context and deciding how much risk a given change carries there. Every
other step — the lineage query, the diff generation, the PR routing, the
write-back — is deterministic code, not model output. Fix generation and
PR automation, including the auto-merge/review-required split, are driven
directly off that one judgment call.

## Challenges we ran into

The DataHub CLI's datapack loading command turned out to have a confirmed,
open bug specific to Windows, which meant pivoting from the official
sample dataset to a small hand-built demo dataset seeded directly through
the Python SDK — which ended up giving tighter control over the exact
lineage scenarios (a safe simple-reference case and a risky join-key case)
needed to demonstrate the reasoning step clearly. Locally, getting the
Actions Framework listener working correctly required tracking down the
right Kafka topic name and the correct internal schema-registry URL DataHub
actually uses (routed through GMS rather than a standalone service), since
neither is obvious from a first read of the docs. Getting Docker itself
running also required enabling virtualization support that wasn't on by
default.

## DataHub integration and why it matters

Without DataHub, an agent trying to do this would have to grep repositories
for a column name, guess at which files are actually related, and miss any
pipeline that isn't obviously named — the exact way these breakages happen
in real teams today. **With DataHub, the agent already has the dependency
graph.** It doesn't need to guess what's connected to what; it queries it.

DataHub isn't a passive data source here — it's the backbone the whole
pipeline runs on. The **Actions Framework** is the trigger: schema changes
are detected the moment they happen, not on a polling schedule.
**Column-level lineage**, queried through DataHub's GraphQL API, is what
makes it possible to know exactly which downstream files are affected and
how, rather than pattern-matching on names. And critically, the pipeline
**writes back** into DataHub rather than only reading from it — each
migration's full story is saved directly onto the entity as a structured
record. That write-back is what turns DataHub from a static map of "what
depends on what" into something that actually accumulates institutional
knowledge over time — the next engineer, or the next agent, inherits real
context instead of having to reconstruct it. In other words: DataHub
provides the agent's memory and context, while LineagePilot provides the
decision-making and execution.

## Accomplishments that we're proud of

This connects six separate systems into a single working loop: DataHub's
schema-change events, its lineage graph, an LLM reading and reasoning
about real code, generated fixes, GitHub's PR workflow, and DataHub's own
metadata store for the write-back. Getting all six wired together and
running reliably, end to end, against a real DataHub instance is the
actual achievement here — and the clearest proof it works is that the same
rename produced two different, correctly justified outcomes in a single
run: one auto-merged, one flagged for review, with no manual intervention
deciding which was which.

## What we learned

How much of DataHub's real power is in the parts that aren't visible from
the UI alone — the Actions Framework's event model, and just how much
context column-level lineage carries once you can actually query it
programmatically. Also a fair amount about the gap between "the docs say
this should work" and what actually runs cleanly on a given OS.

## What's next for LineagePilot

Expanding beyond dbt-style SQL to Airflow DAGs and raw pipeline scripts as
first-class fix targets, broadening the risk model beyond join-keys and
aggregations (test coverage, downstream metric definitions, ownership),
and exploring meaningful open-source contributions back to DataHub itself
around the schema-change event filtering patterns this project relies on.
