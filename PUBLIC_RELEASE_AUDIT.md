# PUBLIC_RELEASE_AUDIT.md

## Purpose

This is the Phase 2 ("Public-Release Safety Audit") deliverable called for by
`ROADMAP.md`. It is a read-only inspection of the **complete Git history** —
every commit, branch, tag, and object in the local repository — for
credentials, tokens, private student data, and other material that must not
become public when this repository's visibility changes from private to
public.

**Nothing was rewritten, deleted, or pushed during this audit.** No network
calls were made, Canvas and the model provider were not contacted, and no
student code was executed. Every command below reads existing local Git
objects only.

Audited at commit `3a6091c` on branch `alpha-refactor`, 2026-07-23.

---

## Commands and Methods Used

### 1. Repository topology

```bash
git branch -a
git tag -l
git remote -v
git log --all --oneline --graph --decorate
```

Confirms every ref that exists (local and remote-tracking) and the full
commit graph, so later checks can honestly claim "all history" rather than
just the current branch.

### 2. Full historical file inventory

```bash
git rev-list --objects --all | awk '{print $2}' | sort -u
git log --all --diff-filter=D --name-status --pretty=format:"COMMIT %h %ad %s" --date=short
git log --all --diff-filter=R --name-status --pretty=format:"COMMIT %h %ad %s" --date=short
```

Lists every path that has ever existed in any commit reachable from any ref
(not just what's checked out today), and separately every file that was ever
**deleted** or **renamed** — the classic way sensitive files hide from a
casual `git ls-files` look but remain fully recoverable from history.

### 3. Targeted pathspec history checks

```bash
git log --all --full-history --name-status -- .env .env.local '*.env.*'
git log --all --full-history --name-only -- '*.zip'
git log --all --full-history --name-only -- output output/*
git log --all --full-history --name-only -- canvas_exports canvas_exports/*
git log --all --full-history --name-only -- .github .github/*
git log --all --full-history --name-only -- workspace workspace/* runs runs/*
git rev-list --objects --all | grep -iE "submission|private|manifest|grading_request|model_run"
```

Directly checks the exact categories `ROADMAP.md` Phase 2 names: `.env`
contents, ZIP files, generated `output/`/`canvas_exports/` directories,
GitHub Actions, and any future `workspace/`/`runs/` paths, plus a filename
sweep for anything that sounds like a private manifest or a captured
submission.

### 4. Content-level secret scan across every commit

```bash
git grep -nIE "sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer [A-Za-z0-9_\-\.]{20,}" $(git rev-list --all) --
git grep -nE "CANVAS_TOKEN[[:space:]]*=|OPENAI_API_KEY[[:space:]]*=" $(git rev-list --all) --
git grep -nE "OPENAI_API_KEY[[:space:]]*=[[:space:]]*[\"']?[A-Za-z0-9]|password[[:space:]]*[:=]|verifier=[A-Za-z0-9]{10,}|instructure\.com/files/[0-9]+/download\?verifier=" $(git rev-list --all) --
```

`git grep <pattern> $(git rev-list --all)` runs the pattern against the
**full file contents of every commit** on every reachable ref, not just the
current working tree — this is the difference between a real history scan
and just looking at `HEAD`. Patterns cover: OpenAI-style API keys, AWS-style
access keys, PEM private key headers, generic long bearer tokens, literal
`CANVAS_TOKEN=`/`OPENAI_API_KEY=` assignments, password fields, and live
Canvas file-download `verifier=` query tokens (the signed-URL mechanism
Canvas uses for attachment downloads).

### 5. Blob size sweep

```bash
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$1=="blob"{print $3,$2,$4}' | sort -rn | head -20
```

Ranks every blob ever stored, by size, regardless of whether it's reachable
from the current branch — the standard way to catch an accidentally
committed ZIP, binary, or large data dump that text-based `git log`
searches could miss.

### 6. `.gitignore` evolution

```bash
git log --all --follow -p -- .gitignore
```

Shows every version of `.gitignore` since the initial commit, so a gap in
coverage (a rule added *after* the risky file type could have been
committed) can be identified even if no leak actually occurred.

### 7. Repository integrity / stray objects

```bash
git count-objects -v
git fsck --full --no-progress
git cat-file -t / -s / -p <object>   # for any object fsck flags
```

Fully local, offline integrity check. Used to catch dangling or unreachable
objects that a plain `git log` walk (which only follows reachable history)
would never show.

### 8. Working-tree state

```bash
git status
```

Confirms nothing sensitive is currently staged/untracked in the working
directory outside of what this session itself produced.

---

## Findings

### Credentials, API keys, and tokens — none found

- No match for OpenAI-style (`sk-...`), AWS-style (`AKIA...`), PEM private
  key, or generic long bearer-token patterns anywhere in the full history
  (command set 4, first query — zero results across all commits).
- Every `CANVAS_TOKEN=` / `OPENAI_API_KEY=` occurrence in history is either
  `os.getenv("CANVAS_TOKEN")` (reading the env var by name, not a value) or
  an explicit placeholder string (`your_canvas_api_token`,
  `your_api_token_here`, `your_token_here`) in `.env.example`, `README.md`,
  or `TROUBLESHOOTING.md`. No literal token value was ever committed.
- No `password=`/`password:` field, and no Canvas signed-URL `verifier=`
  token, appears anywhere in history.

### `.env` file — never committed

- The only env-related path ever added in any commit is `.env.example`
  (added in the Initial commit `b44e9e5`, containing only placeholder
  values). An initial broad pathspec match against `.env` briefly looked
  like it implicated a real `.env` file; re-running with `--name-status`
  showed the actual match was `.env.example` (the glob `*.env.*` used in
  the same query incidentally substring-matches `.env.example`). Confirmed
  directly with an exact-path search
  (`git rev-list --objects --all | awk '{print $2}' | grep -E "^\.env$|/\.env$"`)
  — **no literal `.env` file exists anywhere in history.**

### Canvas tokens, student names, Canvas user IDs, private manifests

- No file matching submission/private/manifest-style naming was ever added
  or deleted outside the two tracked, synthetic-content modules
  (`module_3_list_submissions.py`, `module_3_list_submissions_v2.py`,
  `module_4_download_submission.py`) — these are the *scripts* that
  *produce* private manifests at runtime under `output/`, not committed
  manifest data itself. `output/` has been `.gitignore`d since the second
  commit (`857352c`, before Module 3/4 existed), and the full-history
  pathspec check for `output`/`output/*` returns zero commits — nothing was
  ever written there.
- No real student names, Canvas user IDs, or course/institution-identifying
  values were found in any tracked file (this cross-checks the file-by-file
  reading already performed for `REPOSITORY_INVENTORY.md`, which covered
  every tracked file's content directly). All example data (student
  "Melissa Bott" in `module_5_1`'s docstring, course IDs like `3572383` in
  usage examples) reads as synthetic/illustrative, consistent with
  `README.md`'s own instruction that fixtures must use synthetic data.

### Submissions and ZIP files — none found

- Full-history pathspec search for `*.zip` returns zero commits.
- Full-history blob-content scan (`git rev-list --objects --all | grep -iE
  "\.zip$"`) returns zero blobs.
- `*.zip` has been in `.gitignore` since commit `9031e80`. Module 4 (the
  only script that downloads a ZIP) was introduced one commit *earlier*
  (`863bb6a`), which could have been a coverage gap — but `output/` (where
  Module 4 always writes its ZIP, under
  `output/assignment_<id>/<label>/original/submission.zip`) was already
  ignored since `857352c`, well before Module 4 existed. No gap in practice;
  confirmed empirically by the zero-blob result above.

### Generated output — none found

- `output/` and `canvas_exports/` both return zero commits for
  `--full-history` pathspec searches. Both are `.gitignore`d from very early
  in history (`857352c` and the Initial commit, respectively).

### Provider artifacts containing protected data — none found

- No `grading_request/`, `model_runs/`, or provider-response-shaped file was
  ever committed (covered by the same `output/` full-history check, since
  Module 6/7's runtime artifacts are always written under
  `output/assignment_<id>/<label>/grading_request/...`).

### Deleted or renamed sensitive files

- **Deletions:** `git log --all --diff-filter=D` returns **zero** results —
  no file has ever been deleted from this repository's history. There is
  nothing hiding behind a deletion.
- **Renames:** Exactly one rename event exists, in commit `53e6034`: a
  directory-name typo fix, `grading_assets/cars_engines_steerting/` →
  `grading_assets/cars_engines_steering/`, across all 13 files in that
  directory. This is instructor-authored, non-sensitive assignment content
  (already reviewed file-by-file in `REPOSITORY_INVENTORY.md`) — harmless.

### Large or suspicious blobs — none found

The 20 largest blobs ever stored (by content size) are all ordinary tracked
source/documentation files, topping out at ~51 KB
(`module_6_build_grading_package.py`) and ~43 KB (`ARCHITECTURE.md`). No
binary, archive, or unexpectedly large blob exists anywhere in the object
database. `git count-objects -v` shows a total pack size of 34 KB
(compressed) across 24 packed objects plus a small number of loose objects
— a repository this size cannot be hiding a submission archive or bulk data
export.

### Repository integrity check

`git fsck --full --no-progress` found the object database otherwise sound,
with one informational note:

- **One dangling blob** (`f691576...`, 55,064 bytes, unreachable from any
  ref). Inspected directly with `git cat-file -p` — its content is an
  **earlier draft of this session's own `REPOSITORY_INVENTORY.md`**, from
  before a wording fix was applied to the Module 5/5.1 section a few
  minutes ago in this same session. It was never staged, never committed,
  and is not reachable from `main`, `alpha-refactor`, or the tag.
  **Dangling objects are never transmitted by `git push`, `git fetch`, or
  `git clone`** (Git only transfers objects reachable from the refs being
  transferred), so this poses **no public-release risk** as-is. It can be
  cleared later with routine garbage collection (`git gc`) at the user's
  discretion; this audit did not run `git gc` or any pruning command, since
  that would be a write/destructive operation outside this audit's
  read-only scope.

### `.gitignore` coverage

Current `.gitignore` (evolved across 3 commits, full diff history reviewed
above) covers: `.env`/`.env.local`/`.env.*.local`, standard Python
build/cache artifacts, virtual environments (`venv/`, `.venv`, etc.), IDE
files, OS files, `canvas_exports/`, `output/`, and `*.zip`.

- **Covered and verified effective:** `.env`, `output/` (and everything
  nested under it, including future `grading_request/`/`model_runs/`
  subdirectories, since git ignore patterns without a leading `/` match at
  any depth), `canvas_exports/`, `*.zip`.
- **Gap — forward-looking, not a current leak:** `ARCHITECTURE.md`'s target
  workspace layout (`workspace/course_<id>/assignment_<id>/run_<id>/...`)
  uses a **top-level `workspace/`** directory name, and `ROADMAP.md`'s own
  Phase 2 checklist explicitly asks whether `workspace/` and `runs/` are
  ignored. Neither name is currently in `.gitignore`. This directory does
  not exist yet anywhere in the repository or its history (confirmed above
  — zero commits touch `workspace/*` or `runs/*`), so there is **no current
  leak**, but `.gitignore` should gain explicit `workspace/` and `runs/`
  entries before or when Phase 9 (Workspace and Resumability) introduces
  that directory, not after.
- **Minor gap:** `config/model_profiles.json` is tracked (not ignored) and
  currently contains no secret (`api_key_env` names an environment variable,
  never a literal key — confirmed in `REPOSITORY_INVENTORY.md`). Nothing in
  `.gitignore` would stop a future contributor from pasting a literal API
  key directly into that tracked file instead of `.env`. Recommend adding a
  short comment in the file itself (or in `README.md`'s setup section)
  warning against this, rather than un-tracking a file that's meant to be
  committed with non-secret defaults.

### GitHub Actions / CI artifacts

- No `.github/` directory exists currently, and the full-history pathspec
  search (`git log --all --full-history -- .github .github/*`) returns zero
  commits — no workflow file, Action, secret reference, or CI configuration
  has ever existed in this repository. There is nothing to review here; a
  future CI setup should be reviewed against `CLAUDE.md`'s Testing
  Requirements and Security rules when it's introduced.

### Working tree at time of audit

`git status` shows the working tree clean apart from this session's own
documentation work: `ROADMAP.md` modified and `REPOSITORY_INVENTORY.md`
untracked (both from the accepted Phase 3 work earlier in this session,
still uncommitted). Nothing unexpected or sensitive is present.

---

## Files Requiring Cleanup

None are **required** for safety (no secret or private data needs to be
scrubbed from history). One item is recommended for polish before publishing:

- **`SELF_TEST_RESULT.txt`** and **`SELF_TEST_VALIDATOR_PATCH.txt`**
  (tracked since commits `9031e80`/module-7-era work; both currently in
  `HEAD`) contain a leaked, unrelated internal-tooling stack trace mixed
  into their narrative self-test output (paths under
  `/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/...`, `RemoteError:
  hydrateCrdtFromProto requires an empty collaborative document`). This was
  already flagged in `REPOSITORY_INVENTORY.md`. It contains **no secrets,
  tokens, or private data** — confirmed again by this audit's content-level
  secret scan, which covers these files along with everything else in
  history. It is a hygiene/professionalism issue, not a safety blocker:
  recommend regenerating clean self-test output (or removing the stray
  trace lines) before or shortly after the repository goes public.

---

## Blockers

**None.** No credential, token, `.env` content, student name, Canvas user
ID, private manifest, submission file, ZIP archive, generated output, or
provider artifact containing protected data was found anywhere in the
repository's full history, on any branch or tag.

---

## Non-Blocking Hygiene Issues

1. `SELF_TEST_RESULT.txt` / `SELF_TEST_VALIDATOR_PATCH.txt` contain an
   unrelated leaked debug trace (see "Files Requiring Cleanup" above) — cosmetic, no data exposure.
2. `.gitignore` should gain explicit `workspace/` and `runs/` entries before
   Phase 9 introduces those directories, to keep pace with
   `ARCHITECTURE.md`'s target workspace layout rather than relying solely on
   `output/` continuing to be the umbrella directory.
3. `config/model_profiles.json` is tracked-by-design with non-secret
   defaults; consider a one-line comment warning future contributors not to
   paste a literal key into it.
4. One dangling, unreachable local blob exists in the object database (an
   earlier local draft of `REPOSITORY_INVENTORY.md` from this session,
   never committed). Not transmitted by push/fetch/clone; safe to leave or
   clear with routine `git gc` at the user's discretion — not acted on here
   since pruning is outside this audit's read-only scope.
5. (Carried over from `REPOSITORY_INVENTORY.md`, restated here because it
   bears on public messaging, not because it's a new finding): the
   repository currently has zero automated test coverage. This does not
   block a public *release* the way a leaked credential would, but
   `ROADMAP.md`'s own public-release documentation checklist calls for
   public docs to accurately represent current limitations —
   `README.md`already does this correctly (`> Working prototype through
   Module 8. Active refactoring toward an end-user alpha.`), so no
   documentation change is required on this point; flagged only so it isn't
   lost between this audit and the Phase 5 decision already recorded in
   `ROADMAP.md`.

---

## Final Recommendation

## SAFE TO PUBLISH

No blocking issue was found anywhere in the repository's full Git history —
every commit, both branches, the one tag, and the full object database were
checked, not just the current working tree. No credentials, tokens, `.env`
contents, student identity, private manifests, submission files, ZIP
archives, generated output, or provider artifacts containing protected data
exist anywhere in history, reachable or otherwise.

The two non-blocking items worth doing **before or shortly after** flipping
visibility to public are cosmetic: cleaning the leaked debug trace out of
the two `SELF_TEST_*.txt` files, and adding `workspace/`/`runs/` to
`.gitignore` proactively. Neither involves exposed data and neither should
delay publication if the maintainers prefer to handle them after the switch.

This recommendation covers safety only. `ROADMAP.md` Phase 2's own checklist
also includes non-safety housekeeping items (updating the GitHub repository
description, choosing topics, reviewing branch protection rules after
visibility changes) that remain the maintainers' judgment calls, not this
audit's concern.

---

## Summary

**Files changed by this audit:** One new file,
`PUBLIC_RELEASE_AUDIT.md` (this document). No other file was created,
modified, deleted, or moved. No Git history was rewritten. No commits were
created, amended, or pushed.

**Tests run:** None — this was a read-only forensic audit. No Canvas call,
no model-provider call, and no student code execution occurred at any point.

**Unresolved concerns:** None blocking. Two cosmetic items remain open (the
leaked debug trace in the `SELF_TEST_*.txt` files; the forward-looking
`workspace/`/`runs/` `.gitignore` gap) — both are tracked above as
non-blocking hygiene issues, not required before publishing.

**Exact next actions:**
1. Review and, if you agree with this audit's findings, mark Phase 2
   complete in `ROADMAP.md` (checking the corresponding boxes in the Phase 2
   "Required Checks" list and the Current Deliverables list) — not done
   automatically here, per the same "completed and accepted" pattern used
   for Phase 3.
2. Decide whether to clean `SELF_TEST_RESULT.txt`/`SELF_TEST_VALIDATOR_PATCH.txt`
   now or after publishing (non-blocking either way).
3. Decide whether to add `workspace/`/`runs/` to `.gitignore` now (cheap,
   proactive) or defer to Phase 9 when that directory is actually
   introduced.
4. When ready, change the GitHub repository visibility to public and revisit
   branch protection rules afterward, per `ROADMAP.md`'s own Phase 2 exit
   criteria.
5. `ROADMAP.md` and `REPOSITORY_INVENTORY.md` remain uncommitted in the
   working tree from this session (`git status` above) — commit them
   whenever you're ready; not done automatically since committing wasn't
   requested.
