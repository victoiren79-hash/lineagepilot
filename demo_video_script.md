# LineagePilot — Demo Video Script (under 3 minutes)

Target pace: ~170 words/minute. Total script is ~440 words, leaving room for
screen-recording pauses (loading, scrolling) within the 3-minute limit.

---

## ⚠️ PRE-RECORDING CHECKLIST — do this BEFORE you hit record

You already ran this pipeline during testing, so DataHub and GitHub are
currently in an "already fixed" state. If you record without resetting,
the live demo will look broken (nothing to fix) or confusing (duplicate
PRs). Reset first:

1. **Revert `seed_datahub.py`**: make sure `raw_orders_v2` still has
   `"user_id"`, not `"customer_id"` (should already be reverted from
   earlier — double check before running).
2. **Run the reset seed**:
   ```bash
   py -3.11 seed_datahub.py
   ```
   This puts `raw_orders_v2` back to its original `user_id` state in
   DataHub — your clean "before."
3. **Revert `stg_orders_v2.sql` on GitHub**: open it in your repo, edit
   directly on `main`, change `customer_id as user_id` back to plain
   `user_id`, commit. This undoes the previously auto-merged fix so the
   live run produces a real, new change instead of a no-op.
4. **Close/delete old test PR branches** in your repo so only fresh PRs
   from this recording appear afterward.
5. **Confirm Docker Desktop is running** and DataHub is up
   (`py -3.11 -m datahub docker quickstart` if not already started).

Once all 5 are done, you're in a genuinely clean "before" state — now
follow the script below and everything you show on screen is real,
first-time execution, not a replay.

---

## [0:00–0:20] Cold open — the problem (screen: DataHub UI, raw_orders_v2 dataset page)

**On screen:** DataHub UI showing `raw_orders_v2` with its Lineage tab open,
showing 2 downstream datasets.

**Narration:**
"Every data team has felt this: someone renames a column upstream, and two
pipelines silently break. DataHub can show you the blast radius — but
someone still has to figure out *why* it breaks, fix the code, and get it
reviewed. That's what LineagePilot does automatically."

---

## [0:20–0:40] Trigger the change (screen: terminal, editing seed_datahub.py)

**On screen:** Show the line changing `"user_id"` to `"customer_id"` in
`seed_datahub.py`, then running it:
```bash
py -3.11 seed_datahub.py
```

**Narration:**
"Here, `user_id` on `raw_orders_v2` gets renamed to `customer_id`. DataHub
picks up the schema change instantly through its Actions Framework."

---

## [0:40–1:10] Run the pipeline (screen: terminal running `main.py`)

**On screen:**
```bash
py -3.11 main.py
```
showing the 5-step output live.

**Narration:**
"Now I run LineagePilot. It pulls column-level lineage from DataHub to find
every downstream consumer. For each one, it reads the actual code and
reasons about how that column is used — not just that it's referenced."

**On screen:** Pause on the terminal output showing:
`Risk: LOW - ...` for stg_orders_v2
`Risk: HIGH - ... join and GROUP BY aggregation ...` for fct_revenue_v2

**Narration (continued):**
"One file just selects the column — low risk. The other uses it as a join
key inside a revenue aggregation — high risk. Same rename, two different
judgment calls, made automatically."

---

## [1:10–1:50] Show the generated fixes (screen: terminal diff output, then GitHub)

**On screen:** Scroll to the diff output in the terminal, then cut to GitHub
showing the two Pull Requests.

**Narration:**
"LineagePilot generates the actual corrected code for each file and opens a
real GitHub Pull Request. The low-risk fix gets auto-merged immediately.
The high-risk one stays open, with the reasoning written directly into the
PR so a human reviewer knows exactly why it needs a second look before it
touches revenue numbers."

**On screen:** Click into the high-risk PR, show the comment with the
reasoning text.

---

## [1:50–2:20] The write-back (screen: DataHub UI, Properties tab on raw_orders_v2)

**On screen:** Navigate to `raw_orders_v2` in DataHub, click the Properties
tab, show the `migrationHistory` JSON.

**Narration:**
"And this is the part that matters most: LineagePilot writes the full
migration record — what changed, which files were affected, links to both
PRs, and the risk reasoning — directly back into DataHub. The next
engineer, or the next agent, who looks at this table doesn't start from
zero. They inherit the whole story."

---

## [2:20–2:50] Closing — why this matters (screen: architecture diagram or DataHub lineage view)

**Narration:**
"DataHub tells you what breaks. LineagePilot tells you why, fixes it, and
remembers. It's built entirely on DataHub's own lineage graph, Actions
Framework, and metadata write-back — turning a static map of dependencies
into something that actually closes the loop."

---

## [2:50–3:00] End card (screen: repo URL / title card)

**On screen:** "LineagePilot — github.com/victoiren79-hash/lineagepilot"

**Narration:**
"Thanks for watching."

---

## Recording notes
- Keep terminal font large enough to read on a recording (14-16pt minimum)
- Record the DataHub UI and GitHub views at 1080p minimum
- If any step is slow in real time (e.g. Docker startup), cut it in editing —
  don't pad with dead air on camera
- Do NOT show the pre-recording checklist steps on camera — those happen
  before you hit record, so the video opens directly on a clean state
