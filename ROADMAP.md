# ROADMAP.md

## Document Purpose

This document is the active project roadmap for the Canvas Grading Assistant.

It answers:

- Where are we now?
- What has already been completed?
- What comes next?
- What is intentionally deferred?
- How do we know when a phase is complete?
- What should a new Claude Code session read before starting?
- What must happen before the repository becomes public?
- What defines the end-user alpha?
- What defines Version 1?

This document should be updated as phases are completed or priorities change.

Architecture belongs in `ARCHITECTURE.md`.

Repository work rules belong in `CLAUDE.md`.

User-facing project information belongs in `README.md`.

---

# Project Vision

Build a privacy-conscious, human-in-the-loop grading assistant for programming
assignments submitted through Canvas.

The system should help an instructor:

1. retrieve submissions;
2. prepare privacy-safe grading material;
3. compile and optionally execute student code locally;
4. gather objective evidence;
5. request an advisory model evaluation;
6. validate the structured result;
7. review scores and feedback;
8. approve final grades;
9. eventually post only explicitly approved results to Canvas.

The instructor remains the final authority.

The system must never quietly turn advisory AI output into a final grade.

---

# Finish Lines

The project has two major finish lines.

## Finish Line A — End-User Alpha

The alpha is complete when the application can:

1. configure Canvas, provider, toolchain, workspace, and assignment package;
2. validate required inputs before processing;
3. process one submission end to end;
4. reproduce the known working one-student report;
5. process multiple submissions sequentially;
6. isolate failures by submission;
7. resume without repeating completed work or paid provider requests;
8. generate an instructor review workbook;
9. import edited workbook data;
10. create validated, instructor-approved grade JSON;
11. preserve complete provenance and audit information;
12. stop before Canvas writeback.

The alpha does not post grades or feedback to Canvas.

## Finish Line B — Operational Version 1

Version 1 additionally provides:

- current Canvas grade-state reading;
- proposed change preview;
- explicit instructor confirmation;
- protected grade and feedback writeback;
- duplicate-post prevention;
- write audit logs;
- stable installation and setup;
- user documentation;
- recovery documentation;
- supported interface;
- tested retention and cleanup behavior.

---

# Current Status

## Overall Status

```text
Working prototype through Module 8
Active refactoring preparation
```

## Current Branches

```text
main
alpha-refactor
```

## Milestone Tag

```text
prototype-modules-1-through-8
```

The tag points to the proven Modules 1–8 prototype and must not be moved.

## Current Working Capability

The prototype can:

- connect to Canvas;
- inspect a course and assignment;
- list and anonymize submissions;
- download and safely extract one ZIP submission;
- create a privacy-safe source copy;
- remove comments and redact known identifiers;
- construct a grading package;
- compile the student program locally;
- optionally execute it with explicit permission and timeout;
- capture objective evidence;
- request one structured advisory model evaluation;
- validate and locally revalidate the result;
- restore identity locally;
- create a canonical one-student JSON report;
- create a readable one-student Markdown report;
- preserve `NOT_APPROVED` status;
- avoid Canvas writeback.

## Proven Calibration Run

A known successful submission produced:

```text
20 rubric items scored
200 / 200 advisory score
0 unresolved items
0 global deductions
0 manual-review flags
identity restored locally
Canvas contacted by Module 8: No
model provider contacted by Module 8: No
approval status: NOT_APPROVED
```

This run should become the foundation of a synthetic golden regression fixture.

---

# Current Phase

## Phase Name

```text
Phase 5 — Shared Domain Models
```

## Current Objective

Introduce shared, validated domain models incrementally, one artifact at a
time, without changing prototype behavior. **No shared-model extraction may
begin until the minimal `pytest` foundation and the relevant
characterization test for the specific behavior being extracted both
exist.** This requirement was decided 2026-07-23 (see "Decision Recorded
2026-07-23" below) and remains binding now that Phase 5 is the current
phase.

## Current Deliverables

- [x] Working Modules 1–8 prototype committed
- [x] Prototype milestone tag created
- [x] `main` branch established
- [x] `alpha-refactor` branch established
- [x] README replaced with project documentation
- [x] `CLAUDE.md` created
- [x] `ARCHITECTURE.md` created
- [x] `ROADMAP.md` created
- [x] Public-release safety audit completed
- [x] Read-only repository architecture inventory completed
- [x] Refactor sequence reviewed and approved
- [x] Artifact contracts inventoried
- [x] First shared domain-model decision made

The read-only inventory is recorded in `REPOSITORY_INVENTORY.md`. It was
reviewed and accepted on 2026-07-23. Its proposed extraction sequence (Part 4)
is the accepted basis for Phase 5 planning.

The public-release safety audit is recorded in `PUBLIC_RELEASE_AUDIT.md`. It
was reviewed and accepted on 2026-07-23. Its finding was **safe to publish**:
no credentials, tokens, `.env` contents, student names/Canvas IDs, private
manifests, submissions, ZIP files, generated output, or provider artifacts
containing protected data exist anywhere in the repository's full Git
history. The two non-blocking hygiene items it identified (a leaked,
unrelated debug trace in `SELF_TEST_VALIDATOR_PATCH.txt`, and a
`workspace/`/`runs/` `.gitignore` gap) have since been resolved.

The artifact contract inventory is recorded in `ARTIFACT_CONTRACTS.md`. It
documents 30 persisted/derived artifacts (the 27 required by Phase 4's
minimum list plus 3 additional diagnostic/preview artifacts found during
inspection) and records the accepted first-formalization order:
`PrivacyClassification`/`ArtifactMetadata` first, `Rubric`/
`RubricCriterion`/`RubricItem` next.

The domain-model-library decision (`OD-001`) is recorded in
`OD-001_DOMAIN_MODEL_LIBRARY.md`. It was **accepted on 2026-07-24**: Pydantic
v2 is the primary model system for persisted artifact contracts and
external/trust-boundary data; standard-library dataclasses remain
appropriate for small, transient, internal-only records; recursive
AI-safety/privacy scanning remains independent of Pydantic validation and is
not replaced by it; and `PrivacyClassification`/`ArtifactMetadata` is
confirmed as the first model target.

## Decision Recorded 2026-07-23

A minimal automated test foundation (a runnable `pytest` setup plus fixtures)
and characterization tests for the specific behavior being extracted must
exist **before or alongside** the first code extraction (Phase 5). No shared
model or service may be extracted from a prototype module that does not yet
have a passing characterization test proving the prototype's current
behavior. This closes the gap `REPOSITORY_INVENTORY.md` identified: zero
automated tests exist anywhere in the repository today. See the corresponding
rule added to Phase 5's Implementation Rules and to risk `R-002`. **This
requirement remains binding** and is restated in the Current Recommended Next
Task below.

## Current Phase Pointer

Phases 0 through 4 are complete: Freeze the Working Prototype,
Documentation Foundation, Public-Release Safety Audit, Read-Only Repository
Inventory, and Artifact Contract Inventory (including `OD-001`'s
domain-model-library decision). Phase 5 (Shared Domain Models) is now the
current phase. The next controlled work is, in order:

1. establish a minimal, runnable `pytest` foundation;
2. add synthetic fixtures (no real student data, per `CLAUDE.md`);
3. characterize the current Module 6 `validate_ai_manifest()` behavior as it
   operates on Module 5.1's `module_5_ai_package_manifest.json` shape;
4. only then begin introducing `PrivacyClassification`/`ArtifactMetadata`
   incrementally, per the accepted `OD-001` decision.

**No numbered module is to be deleted, renamed, moved, or retired during
this work.** Every numbered prototype script remains available and
unmodified until its replacement demonstrates parity, per `CLAUDE.md`'s
"Preserve the Working Prototype" rule and Architectural Decision AD-001.

Changing the repository's actual GitHub visibility to public remains a
separate, explicit, maintainer-owned action (see Phase 2's "Public Release
Decision" and the "Immediate Action List" below) and is not implied by this
documentation work.

## Current Recommended Next Task

A narrowly scoped Phase 5 **testing-foundation** increment — establishing
the ability to write and run characterization tests, not yet extracting or
replacing any prototype behavior:

1. Add `pytest` as an explicit, intentional development/test dependency
   (not yet done — no dependency has been added by any work to date).
2. Establish the minimum test directory and configuration needed to run
   `pytest` against this repository.
3. Create synthetic fixtures reproducing the current
   `module_5_ai_package_manifest.json` shape (Module 5.1's AI-safe package
   manifest, per `ARTIFACT_CONTRACTS.md` Artifact 7).
4. Write characterization tests proving the existing
   `module_6_build_grading_package.py`'s `validate_ai_manifest()` behavior,
   **before** extracting or replacing any of it — including:
   - successful and failing privacy-flag cases;
   - strict handling of missing, `true`, or non-boolean `contains_*`
     fields (the four required-`False` checks `validate_ai_manifest()`
     already enforces).
5. Perform no Canvas calls, no model-provider calls, and no student-code
   execution anywhere in this increment.
6. Modify no numbered module during this initial test-foundation increment
   — the tests characterize `module_6_build_grading_package.py` as it
   exists today; they do not change it.

No test, fixture, or model exists yet as of this roadmap update — this is
the next task to perform, not a completed one. **No extraction may proceed
without this foundation** — see the 2026-07-23 decision above, Phase 5's
Implementation Rules, and risk `R-002`.

## Exit Criteria for Current Phase

Phase 4's exit criteria (repository inventory exists; every major Modules
1–8 responsibility has a proposed destination; no production code moved
during the audit; public-release risks documented; artifact contracts
listed; first extraction sequence agreed upon; this roadmap updated) are
**all met** — see the detailed Phase 4 section below.

Phase 5, now current, is complete only when its own detailed exit criteria
(below, in the Phase 5 section) are met: selected model system documented;
first shared models implemented; current fixture artifacts load
successfully; validation tests pass; no prototype path broken. **None of
these are yet met.** Only the decision-making prerequisite (`OD-001`) is
complete; no model, fixture, or test has been implemented.

---

# Session Startup Protocol

At the beginning of each new Claude Code session:

1. Read `CLAUDE.md`.
2. Read `ARCHITECTURE.md`.
3. Read this `ROADMAP.md`.
4. Confirm the current branch.
5. Run `git status`.
6. Review recent commits relevant to the current phase.
7. Inspect the latest phase deliverables.
8. Determine what work has already been completed.
9. Do not repeat completed audits or migrations unless explicitly asked.
10. Summarize:
    - current phase;
    - completed work;
    - requested task;
    - intended change scope;
    - tests to run;
    - safety boundaries involved.

This startup review should be lightweight.

Its purpose is context recovery, not a full repository re-audit.

---

# Roadmap Overview

```text
Phase 0   Freeze Working Prototype                 COMPLETE
Phase 1   Documentation Foundation                 COMPLETE
Phase 2   Public-Release Safety Audit              COMPLETE
Phase 3   Read-Only Repository Inventory           COMPLETE
Phase 4   Artifact Contract Inventory              COMPLETE
Phase 5   Shared Domain Models                     PLANNED
Phase 6   Application Skeleton                     PLANNED
Phase 7   One-Submission Vertical Slice            PLANNED
Phase 8   Assignment Package Generalization        PLANNED
Phase 9   Workspace and Resumability               PLANNED
Phase 10  Module 8B Sequential Batch Processing    PLANNED
Phase 11  Module 8C Review Workbook                PLANNED
Phase 12  Module 8D Approved Grade Import          PLANNED
Phase 13  Alpha Hardening and Release              PLANNED
Phase 14  Module 9 Canvas Change Preview           FUTURE
Phase 15  Module 10 Canvas Writeback               FUTURE
Phase 16  User Interface                           FUTURE
Phase 17  Version 1 Hardening                      FUTURE
```

---

# Phase 0 — Freeze the Working Prototype

## Status

```text
COMPLETE
```

## Goals

- preserve the working Modules 1–8 implementation;
- create a stable recovery point;
- ensure later refactoring cannot erase the proven path.

## Completed Work

- [x] Modules 1–8 committed
- [x] Successful one-student run preserved
- [x] Prototype tag created
- [x] Tag pushed to GitHub
- [x] `main` established as default branch
- [x] `alpha-refactor` created
- [x] obsolete silly-named branch removed
- [x] prototype remains recoverable

## Exit Criteria

All met.

---

# Phase 1 — Documentation Foundation

## Status

```text
COMPLETE
```

## Goals

Create enough durable project context that work can continue across multiple
Claude Code sessions without relying on chat history.

## Deliverables

- [x] `README.md`
- [x] `CLAUDE.md`
- [x] `ARCHITECTURE.md`
- [x] `ROADMAP.md`

## Exit Criteria

- project purpose documented;
- current status documented;
- work rules documented;
- target architecture documented;
- phase sequence documented;
- public safety rules documented;
- session startup protocol documented.

All met.

---

# Phase 2 — Public-Release Safety Audit

## Status

```text
COMPLETE
```

## Goal

Determine whether the repository can be safely changed from private to public.

## Required Checks

### Current Working Tree

- [x] `.env` is not tracked
- [x] `.venv` is not tracked
- [x] generated `output/` is not tracked
- [x] future `workspace/` and `runs/` paths are ignored
- [x] downloaded ZIP files are not tracked
- [x] student submissions are not tracked
- [x] private manifests are not tracked
- [x] grading reports containing identity are not tracked
- [x] provider request/response files containing protected data are not tracked
- [x] no API keys are present
- [x] no Canvas token is present
- [x] no private URLs are present
- [x] no real student names or Canvas IDs are present

Verified across the complete Git history (not just the working tree) by
`PUBLIC_RELEASE_AUDIT.md`. `workspace/` and `runs/` did not previously exist
in the repository or its history; both are now explicit `.gitignore` entries
ahead of Phase 9 introducing that layout.

### Full Git History

Check all:

```text
branches
tags
commits
deleted files
renamed files
large blobs
GitHub Actions logs
GitHub Actions artifacts
```

All checked — methodology and results recorded in `PUBLIC_RELEASE_AUDIT.md`.
Two branches (`main`, `alpha-refactor`), one tag
(`prototype-modules-1-through-8`), all 12 commits, zero deletions, one
harmless directory-name-typo rename, no oversized/suspicious blobs, and no
GitHub Actions artifacts (none have ever existed) were reviewed.

### Documentation

- [x] README reflects the actual project
- [x] README warns against committing student data
- [x] README states prototype status
- [x] MIT license exists
- [x] privacy and instructor-review principles are public
- [x] current public limitations reviewed
- [ ] repository description updated on GitHub
- [ ] GitHub topics selected if desired

The last two are GitHub-side actions taken directly on github.com, not local
repository changes — left for the maintainer to do at publish time.

### Suggested Local Commands

```cmd
git status
git branch -a
git tag
git ls-files
git log --all -- .env
git log --all -- output
git log --all -- "*.zip"
git log --all -- "*.json"
git log --all -p -- .env
```

`PUBLIC_RELEASE_AUDIT.md` used a superset of this list, including a
full-history content-level secret scan (`git grep <pattern> $(git rev-list
--all)`) and a blob-size sweep — see that document for the exact commands
used.

## Public Release Decision

The repository may be made public when:

- all checks pass; — **met**, see `PUBLIC_RELEASE_AUDIT.md`.
- any discovered private data is removed from history; — **n/a**, none was
  found.
- documentation accurately represents current status; — **met**, confirmed
  by the audit.
- the instructor accepts the remaining prototype limitations. — instructor
  decision; not made by this audit.

## Exit Criteria

- documented audit result; — met, `PUBLIC_RELEASE_AUDIT.md`.
- no known secrets; — met.
- no known student data; — met.
- no unsafe generated artifacts; — met.
- GitHub branch protection/rules reviewed; — **not yet done** — this is a
  GitHub-side review, deferred to the actual visibility-change action below.
- visibility changed to public or consciously deferred. — **consciously
  deferred**: the safety audit is complete and found no blocker, but flipping
  actual GitHub visibility is a separate, explicit, maintainer-initiated
  action (see "Immediate Action List") not performed by this phase.

All met except the two GitHub-side items above, which belong to the visibility
change itself rather than to the safety audit.

---

# Phase 3 — Read-Only Repository Inventory

## Status

```text
COMPLETE
```

## Goal

Understand the current repository before moving code.

## Deliverable

Recommended file:

```text
REPOSITORY_INVENTORY.md
```

## Required Inventory Columns

```text
current file
symbol
responsibility
inputs
outputs
side effects
dependencies
artifacts consumed
artifacts produced
privacy classification
Canvas operations
provider operations
student-code execution
proposed destination
tests present
tests needed
notes
```

## Required Findings

- duplicate JSON loading/writing helpers;
- duplicate path handling;
- shared privacy checks;
- shared artifact metadata;
- Canvas connection duplication;
- assignment and submission identity handling;
- archive validation logic;
- sanitization logic;
- compiler discovery;
- compile/run evidence;
- prompt construction;
- provider adapters;
- result validation;
- score calculation;
- identity restoration;
- report rendering;
- current failure behavior.

## Restrictions

- no production code moves;
- no mass renaming;
- no framework adoption;
- no dependency changes;
- no prototype deletion;
- no provider calls;
- no Canvas calls;
- no student-code execution.

## Exit Criteria

- inventory complete;
- destination mapping reviewed;
- highest-risk couplings identified;
- duplicate logic identified;
- first safe extraction sequence proposed.

All met. Delivered as `REPOSITORY_INVENTORY.md`, reviewed and accepted
2026-07-23.

## Deviation Recorded

The inventory additionally found the repository has zero automated test
coverage anywhere. Per the 2026-07-23 decision recorded in the Current Phase
section above, this must be addressed before or alongside Phase 5, not
deferred to Phase 13 hardening as originally implied.

---

# Phase 4 — Artifact Contract Inventory

## Status

```text
COMPLETE
```

## Goal

Define the data contracts already used by the prototype before introducing
shared models.

## Required Artifact List

At minimum:

- Canvas course reference;
- Canvas assignment reference;
- private submission manifest;
- AI-safe submission manifest;
- private extraction manifest;
- AI-candidate manifest;
- privacy/sanitization report;
- AI-safe student material;
- grading package;
- compile evidence;
- execution evidence;
- output comparison evidence;
- provider request;
- provider response metadata;
- grading result;
- validation report;
- one-student grading report;
- Module 8 report manifest.

## Deliverable

Recommended file:

```text
ARTIFACT_CONTRACTS.md
```

or machine-readable schema inventory plus human documentation.

## Required Questions

For each artifact:

- Who creates it?
- Who consumes it?
- Is it private or AI-safe?
- Is `send_to_ai` explicit?
- What is its schema version?
- Which fields are required?
- Which fields are optional?
- What identifiers must match?
- Is it canonical or a rendering?
- Can it be regenerated?
- Is it safe to hash?
- Is it safe to commit?
- How should incompatible versions fail?

## Completed Work

- [x] `ARTIFACT_CONTRACTS.md` completed and accepted.
- [x] 30 persisted/derived artifacts documented (the 27 required by the
      minimum list above, plus 3 additional diagnostic/preview artifacts
      found during inspection and documented for completeness).
- [x] Inconsistent field names and schema-version gaps identified (three
      independent privacy-enforcement mechanisms; `schema_version`
      inconsistent even within a single Module 6 run; three same-named
      "validation report" artifacts with different pass/fail semantics; and
      other findings recorded in `ARTIFACT_CONTRACTS.md`'s cross-cutting
      sections).
- [x] Canonical, derived, rendered, temporary, and diagnostic artifacts
      distinguished, artifact by artifact.
- [x] Migration and historical-compatibility needs documented (Module 3
      v1/v2, Module 5/5.1, and other historical shapes catalogued in
      `ARTIFACT_CONTRACTS.md`'s "Compatibility Requirements for Saved
      Prototype Runs").
- [x] `PrivacyClassification`/`ArtifactMetadata` selected as the first
      contract to formalize, ahead of `Rubric`/`RubricCriterion`/
      `RubricItem`.
- [x] `OD-001` (domain-model-library decision) completed and accepted on
      2026-07-24 — see `OD-001_DOMAIN_MODEL_LIBRARY.md`.

## Exit Criteria

- all major artifacts documented;
- inconsistent field names identified;
- schema-version gaps identified;
- canonical versus derived artifacts identified;
- migration needs identified.

All met. Delivered as `ARTIFACT_CONTRACTS.md` and
`OD-001_DOMAIN_MODEL_LIBRARY.md`, both reviewed and accepted (2026-07-24).

---

# Phase 5 — Shared Domain Models

## Status

```text
PLANNED
```

## Goal

Introduce shared validated models without changing prototype behavior.

## Decision Required — RESOLVED (`OD-001`, accepted 2026-07-24)

The domain-model-library decision is complete. Full rationale, comparison,
and consequences are recorded in `OD-001_DOMAIN_MODEL_LIBRARY.md`. The
accepted policy:

- Pydantic v2 is the primary system for persisted artifact contracts and
  external/trust-boundary data (Canvas data once translated into domain
  models, provider requests/responses, and any artifact written to disk and
  later reloaded).
- Standard-library dataclasses remain appropriate for small, transient,
  internal-only records that never cross a process boundary as a defined,
  versioned contract.
- Pydantic becomes an explicit, intentional project dependency once Phase 5
  implementation begins — it is merely transitive today (present only
  because the `openai` SDK depends on it; not yet declared or imported by
  this project's own code).
- Models are introduced incrementally, one artifact at a time — no
  repository-wide conversion.
- Recursive AI-safety/privacy scanning (`assert_ai_safe`-style structural
  checking) remains independent of Pydantic model validation. A
  schema-valid model is not automatically treated as AI-safe; the recursive
  scan must still run.
- Pure business logic may accept validated Pydantic domain models as
  read-only typed inputs directly, but must not itself perform Pydantic
  boundary operations (`model_validate`, `model_dump`, `model_json_schema`,
  migration, or file/network I/O) — those remain at application
  boundaries.

## Initial Model Candidates

```text
CourseRef
AssignmentRef
SubmissionRef
SubmissionAttempt
AttachmentRef
PrivacyClassification
ArtifactMetadata
Rubric
RubricCriterion
RubricItem
SourceFileRecord
CompileEvidence
ExecutionEvidence
OutputComparisonEvidence
GradingRequest
ProviderResponse
RubricItemAssessment
GlobalRuleAssessment
GradingResult
ValidationReport
InstructorReport
ApprovalState
```

## Implementation Rules

- models should be introduced incrementally;
- existing JSON must remain loadable;
- schema generation should be available where useful;
- private and AI-safe models must remain distinguishable;
- model adoption should begin with pure, stable contracts;
- no repository-wide conversion in one step;
- a minimal automated test foundation (`pytest` plus fixtures) must exist
  before the first extraction, and a characterization test proving the
  current prototype behavior must exist for each specific function or
  module being extracted, before or alongside that extraction — decided
  2026-07-23, see Current Phase section.

## Accepted First Extraction

This is no longer an open choice between two candidates. The accepted first
target is:

```text
PrivacyClassification
ArtifactMetadata
```

The next target after that is:

```text
Rubric
RubricCriterion
RubricItem
```

The first characterization-test target is the **current**
`module_6_build_grading_package.py` `validate_ai_manifest()` behavior, as it
operates on Module 5.1's `module_5_ai_package_manifest.json` shape — this is
the artifact with the strictest current privacy enforcement in the
pipeline (four required-`False` `contains_*` checks), making it the best
available stress test for the new model's strictness/coercion policy before
it is applied to any other artifact. See `OD-001_DOMAIN_MODEL_LIBRARY.md`
Section 13 for the full reasoning.

## Exit Criteria

- selected model system documented;
- first shared models implemented;
- current fixture artifacts load successfully;
- validation tests pass;
- no prototype path broken.

---

# Phase 6 — Application Skeleton

## Status

```text
PLANNED
```

## Goal

Create the installable application structure without yet replacing the complete
prototype workflow.

## Deliverables

Potential structure:

```text
src/
└── canvas_grading_assistant/
    ├── cli.py
    ├── config/
    ├── domain/
    ├── workflows/
    ├── canvas/
    ├── submissions/
    ├── privacy/
    ├── execution/
    ├── grading/
    │   └── providers/
    ├── reporting/
    ├── review/
    └── storage/
```

Additional:

- `pyproject.toml`;
- package version;
- test configuration;
- logging configuration;
- domain exceptions;
- configuration loader;
- basic preflight command.

## Initial Commands

Possible first commands:

```text
cga doctor
cga inspect-config
```

Do not document these as available until implemented.

## `doctor` Checks

- Python version;
- package installation;
- workspace write access;
- Canvas configuration presence;
- provider profile presence;
- compiler availability;
- assignment-package path;
- no live call unless explicitly requested.

## Exit Criteria

- application installs locally;
- CLI starts;
- configuration loads;
- tests run;
- no grading behavior replaced yet;
- Windows environment supported.

---

# Phase 7 — One-Submission Vertical Slice

## Status

```text
PLANNED
```

## Goal

Refactor the proven Modules 1–8 path into direct Python services and workflows.

## Required Stages

```text
Canvas selection
submission discovery
attempt selection
download
safe extraction
sanitization
privacy validation
grading package
compilation
optional execution
output comparison
provider evaluation
response validation
score reconciliation
identity restoration
one-student report
```

## Rules

- no script-to-script subprocess orchestration;
- workflows call Python services directly;
- persisted artifacts remain inspectable;
- paid provider requests remain explicit;
- Canvas operations remain explicit;
- student execution remains explicit;
- each stage records status and provenance.

## Golden Parity Test

The refactored path should reproduce the known successful report semantics:

```text
20 items
200 / 200
0 unresolved items
0 deductions
NOT_APPROVED
```

Use synthetic identity and synthetic source fixtures in committed tests.

## Exit Criteria

- one command or application workflow processes one synthetic submission;
- output is equivalent to the prototype;
- no private data reaches provider-facing artifacts;
- no model total is trusted;
- no grade is approved;
- no Canvas write occurs;
- prototype scripts remain available.

---

# Phase 8 — Assignment Package Generalization

## Status

```text
PLANNED
```

## Goal

Remove Cars-assignment assumptions from reusable application services.

## Target Package

```text
assignment_package/
├── assignment.json
├── rubric.json
├── instructor_notes.md
├── package_config.json
├── starter_files/
├── reference_solution/
├── supporting_files/
└── tests/
```

## Required Capabilities

- create package;
- validate package;
- inspect package;
- snapshot package into a run;
- calculate package hash;
- reject inconsistent rubric totals;
- reject missing required files;
- define compile and execution policy;
- define output comparison policy;
- define global grading rules.

## Deterministic Input Paths

Support at least:

- canonical JSON;
- guided CLI entry;
- documented CSV rubric import.

A model provider must not be required to create canonical package data.

## Generalization Test

Create a second synthetic assignment package without changing reusable
application code.

## Exit Criteria

- two assignment packages validate;
- services contain no Cars-specific rules;
- language/toolchain details are profile-driven where practical;
- package creation is deterministic.

---

# Phase 9 — Workspace and Resumability

## Status

```text
PLANNED
```

## Goal

Create a stable run workspace and safe resume behavior.

## Target Layout

```text
workspace/
└── course_<id>/
    └── assignment_<id>/
        └── run_<id>/
            ├── run_manifest.json
            ├── assignment_package_snapshot/
            ├── submissions/
            ├── batch/
            └── logs/
```

## Required Stage States

```text
not_started
in_progress
complete
failed
blocked
skipped
requires_review
```

## Resume Rules

Before repeating a stage, check:

- stage status;
- input hashes;
- output validity;
- package hash;
- provider request hash;
- source changes;
- retry safety;
- duplicate-cost risk.

## Critical Safety Rule

Restarting the application must not duplicate a paid provider request when a
valid saved response already exists.

## Exit Criteria

- interrupted synthetic run resumes;
- completed stages are skipped;
- invalidated inputs trigger appropriate rerun;
- provider requests are not duplicated;
- stage history remains auditable.

---

# Phase 10 — Module 8B: Sequential Batch Processing

## Status

```text
PLANNED
```

## Goal

Process several or all submissions sequentially.

## Required Behavior

- discover eligible submissions;
- skip ineligible submissions with reason;
- process one submission at a time;
- isolate failures;
- continue after one failure;
- retry failed stages;
- resume completed runs;
- save one canonical report per submission;
- summarize usage, duration, failures, and review needs.

## Batch Outputs

```text
batch_run_manifest.json
batch_run_summary.json
batch_run_summary.md
```

## Summary Fields

- total discovered;
- total eligible;
- completed;
- skipped;
- failed;
- blocked;
- requires review;
- provider requests;
- token usage;
- estimated provider cost when available;
- elapsed time.

## Exit Criteria

- synthetic class set processed;
- one failing submission does not stop batch;
- reports remain isolated;
- resume works;
- no duplicate paid requests;
- no Canvas writes.

---

# Phase 11 — Module 8C: Instructor Review Workbook

## Status

```text
PLANNED
```

## Goal

Create an instructor-friendly workbook from canonical one-student reports.

## Inputs

Only canonical Module 8 report JSON.

Do not consume raw provider responses directly.

## Recommended Sheets

```text
Summary
Rubric Detail
Review Flags
Run Information
```

## Editable Fields

- instructor item points;
- instructor feedback;
- instructor notes;
- approval status.

## Protected Fields

- Canvas user ID;
- anonymous label;
- assignment ID;
- rubric item ID;
- maximum points;
- run ID;
- report hash;
- source artifact hashes.

## Workbook Rules

- use validation lists for approval states;
- clearly distinguish editable cells;
- formulas may assist review;
- formulas are not authoritative;
- all values are revalidated during import.

## Exit Criteria

- workbook generated from synthetic reports;
- every student and rubric item represented;
- protected fields cannot be casually overwritten;
- edits round-trip through a test workbook;
- no private provider call occurs.

---

# Phase 12 — Module 8D: Approved Grade Import

## Status

```text
PLANNED
```

## Goal

Read the edited workbook and create validated instructor-approved grade JSON.

## Approval Values

```text
APPROVED
NEEDS_REVIEW
DO_NOT_POST
```

## Required Validation

- workbook manifest;
- run ID;
- assignment ID;
- student identity;
- report hash;
- rubric item IDs;
- maximum points;
- score ranges;
- duplicate rows;
- missing rows;
- total consistency;
- explicit approval;
- feedback presence where required.

## Outputs

```text
approved_grades/
├── submission_001.json
├── submission_002.json
└── approved_grade_batch_manifest.json
```

## Important Boundary

No Canvas write occurs.

## Exit Criteria

- approved records created deterministically;
- tampering tests rejected;
- non-approved rows excluded from postable set;
- totals recalculated locally;
- provenance preserved.

---

# Phase 13 — Alpha Hardening and Release

## Status

```text
PLANNED
```

## Goal

Turn the completed workflow into a usable end-user alpha.

## Required Work

- command consistency;
- configuration documentation;
- assignment-package documentation;
- setup instructions;
- sample synthetic package;
- error-message review;
- logging review;
- cleanup behavior;
- resume documentation;
- privacy checklist;
- provider-cost reporting;
- test suite stabilization;
- release notes;
- version number;
- tagged alpha release.

## Alpha Release Candidate Checks

- [ ] fresh clone works;
- [ ] setup instructions work;
- [ ] no real student data;
- [ ] no secrets;
- [ ] synthetic demo works;
- [ ] one-submission workflow works;
- [ ] batch workflow works;
- [ ] workbook workflow works;
- [ ] approved-grade import works;
- [ ] Canvas writeback absent;
- [ ] known limitations documented.

## Exit Criteria

Finish Line A reached.

---

# Phase 14 — Module 9: Canvas Change Preview

## Status

```text
FUTURE
```

## Goal

Show exactly what would change in Canvas without making changes.

## Inputs

- approved-grade records;
- current Canvas state.

## Output

For each student:

```text
current score
proposed score
current feedback state
proposed feedback
change type
conflicts
warnings
```

## Exit Criteria

- preview complete;
- mismatches blocked;
- no writes;
- instructor can inspect every proposed change.

---

# Phase 15 — Module 10: Canvas Writeback

## Status

```text
FUTURE
```

## Goal

Post only explicitly approved and previewed changes.

## Required Gates

- approved-grade artifact;
- successful preview;
- course match;
- assignment match;
- Canvas user match;
- explicit instructor confirmation;
- duplicate-post protection;
- audit logging.

## Exit Criteria

- controlled write test completed in safe environment;
- duplicate protection verified;
- partial failure recovery verified;
- write audit preserved.

---

# Phase 16 — User Interface

## Status

```text
FUTURE
```

## Goal

Provide an instructor-friendly interface over stable application services.

## Candidate Approaches

- PySide/PyQt desktop;
- local web application;
- browser frontend with Python backend.

## Decision Timing

Do not select the final GUI until:

- workflow inputs are stable;
- artifact contracts are stable;
- batch behavior is stable;
- workbook behavior is stable;
- error states are understood.

## Likely GUI Areas

- setup and preflight;
- assignment-package builder;
- submission-run dashboard;
- provider and toolchain settings;
- per-student review;
- workbook export/import;
- approval review;
- Canvas preview;
- Canvas commit confirmation.

---

# Phase 17 — Version 1 Hardening

## Status

```text
FUTURE
```

## Potential Work

- installer;
- upgrade process;
- schema migration;
- retention policy;
- workspace cleanup;
- encrypted secret integration;
- hardened execution environment;
- local-model provider;
- additional language profiles;
- performance improvements;
- accessibility review;
- institutional deployment guidance;
- backup and recovery;
- support documentation.

## Exit Criteria

Finish Line B reached.

---

# Public Repository Milestone

## Target

Make the repository public after the public-release safety audit passes.

## Desired Timing

Before the next class demonstration, when practical.

## Public Message

The repository should be represented as:

```text
A working privacy-conscious Canvas grading-assistant prototype through
one-student reporting, currently being refactored into an end-user alpha.
```

It must not be represented as:

```text
production-ready
autonomous grading
hardened sandbox
automatic Canvas grader
```

---

# Decision Log Summary

Accepted architectural decisions are documented in `ARCHITECTURE.md`.

Current high-impact decisions include:

- preserve prototype until parity;
- alpha stops before Canvas writeback;
- instructor approval is separate;
- CLI before GUI;
- sequential batch processing first;
- deterministic rubric format;
- provider-neutral core;
- local revalidation;
- local score calculation;
- identity restoration after provider activity;
- current repository continues through alpha;
- domain model library (`OD-001`, accepted 2026-07-24 — see
  `OD-001_DOMAIN_MODEL_LIBRARY.md`).

Open decisions include:

- CLI framework;
- final user interface;
- hardened execution environment;
- local model provider;
- retention policy;
- cross-language expansion.

---

# Risk Register

## R-001 — Context Rot Across Claude Sessions

Mitigation:

- `CLAUDE.md`;
- `ARCHITECTURE.md`;
- `ROADMAP.md`;
- lightweight session startup;
- small commits;
- phase deliverables.

## R-002 — Refactor Breaks Proven Behavior

Mitigation:

- prototype tag;
- preserve numbered scripts;
- golden fixtures;
- parity tests;
- incremental extraction;
- minimal automated test foundation plus characterization tests required
  before or alongside each extraction (decided 2026-07-23; no extraction
  proceeds against untested behavior).

## R-003 — Private Data Enters Git History

Mitigation:

- public-release audit;
- `.gitignore`;
- synthetic fixtures;
- secret scan;
- history scan;
- private workspace separation.

## R-004 — Private Data Reaches Model Provider

Mitigation:

- private versus AI-safe contracts;
- explicit `send_to_ai`;
- privacy validation;
- outbound preview;
- identity restoration only after provider activity.

## R-005 — Student Code Damages Local System

Mitigation:

- explicit execution permission;
- timeout;
- separate compile and run;
- future sandbox decision;
- clear prototype warning.

## R-006 — Paid Provider Requests Are Duplicated

Mitigation:

- saved provider runs;
- request hashes;
- local revalidation;
- resumable stage state;
- no implicit retry.

## R-007 — Model Invents Deductions

Mitigation:

- objective evidence;
- `requires_local_evidence`;
- local domain validation;
- local score calculation;
- instructor review.

## R-008 — Workbook Tampering Corrupts Grades

Mitigation:

- protected identifiers;
- report hashes;
- deterministic import;
- score-range validation;
- explicit approval values.

## R-009 — Canvas Grades Are Posted Accidentally

Mitigation:

- alpha contains no writeback;
- separate preview;
- separate commit workflow;
- explicit confirmation;
- duplicate-post protection.

## R-010 — Architecture Becomes Overengineered

Mitigation:

- extract only proven responsibilities;
- defer GUI;
- defer parallelism;
- defer extra languages;
- avoid frameworks until complexity requires them;
- use small reviewable phases.

---

# Change Management Rules

When a phase is completed:

1. mark its status `COMPLETE`;
2. check completed deliverables;
3. record important deviations;
4. update the Current Phase section;
5. update Current Recommended Next Task;
6. commit the roadmap update with the phase work;
7. do not leave stale “next task” language.

When a phase changes materially:

- record why;
- preserve completed history;
- update architecture when boundaries change;
- update README when public behavior changes.

---

# Suggested Commit Pattern

Examples:

```text
Document repository inventory
Add shared rubric domain models
Extract submission attempt selector service
Add synthetic full-credit regression fixture
Implement application preflight command
Add resumable run manifest
Implement sequential batch workflow
Generate instructor review workbook
Validate approved-grade workbook import
```

Prefer one conceptual change per commit.

---

# Definition of Phase Completion

A phase is not complete merely because code exists.

A phase is complete when:

- deliverables exist;
- tests pass;
- safety boundaries remain intact;
- documentation matches behavior;
- artifacts remain traceable;
- no private data was added;
- no unintended Canvas or provider call occurred;
- the next phase can begin without guessing.

---

# Immediate Action List

## Before Public Release

1. [x] Commit and push `ROADMAP.md`
2. [x] Perform full repository privacy and secret audit
3. [x] Review `.gitignore`
4. [x] Review GitHub Actions logs and artifacts
5. [x] Confirm no real student data in history
6. [x] Confirm no credentials in history
7. [ ] Review repository description
8. [ ] Decide whether to enable Issues and Discussions
9. [ ] Change visibility to public
10. [ ] Recheck branch protection and rules after visibility change

Items 2–6 are documented in `PUBLIC_RELEASE_AUDIT.md` (reviewed and accepted
2026-07-23). Items 7–10 are GitHub-side actions for the maintainer to take
when actually publishing.

## Phase 5 Startup Checklist

1. [x] Start a fresh Claude Code session.
2. [x] Run the lightweight Session Startup Protocol.
3. [x] Complete Phase 4 — Artifact Contract Inventory.
4. [x] Review and accept `ARTIFACT_CONTRACTS.md`.
5. [x] Resolve and accept `OD-001`.
6. [ ] Establish the minimal `pytest` foundation.
7. [ ] Add characterization tests for the first extraction target.
8. [ ] Begin Phase 5 model extraction only after those tests pass.

Items 1–5 are complete: `ARTIFACT_CONTRACTS.md` and
`OD-001_DOMAIN_MODEL_LIBRARY.md` were reviewed and accepted (2026-07-24).
Items 6–8 remain — see "Current Recommended Next Task" above for the
detailed testing-foundation increment. This checklist does not repeat the
repository inventory or public-release audit, both already complete and
accepted (`REPOSITORY_INVENTORY.md`, `PUBLIC_RELEASE_AUDIT.md`).

---

# First Phase 5 Claude Code Startup Prompt

A recommended startup-only prompt for a new session beginning Phase 5 work.
This prompt is read-only and confirmatory — it does not authorize
implementation:

```text
Read CLAUDE.md, ARCHITECTURE.md, ROADMAP.md, ARTIFACT_CONTRACTS.md,
OD-001_DOMAIN_MODEL_LIBRARY.md, and README.md.

Confirm the current Git branch and run git status.

Review the latest commits relevant to the current phase.

Summarize the current Phase 5 state: what is complete (Phases 0-4, the
OD-001 domain-model-library decision), what the accepted first model
target is (PrivacyClassification / ArtifactMetadata), and what the
testing-foundation increment requires before any extraction begins.

Identify the testing-foundation increment (pytest setup, synthetic
Module 5.1 AI-package-manifest fixtures, and characterization tests for
Module 6's validate_ai_manifest()) as the next task.

Make no edits, commits, dependency changes, Canvas calls, model-provider
calls, or student-code execution.

Stop for Doug and Sam to review before any implementation begins.
```

---

# Closing Direction

The project does not need to reach every future phase to be worthwhile.

The immediate objective is to move safely from:

```text
working artifact-driven prototype
```

to:

```text
coherent, testable, privacy-conscious end-user alpha
```

At every step, preserve:

- instructor control;
- student privacy;
- objective evidence;
- deterministic validation;
- auditability;
- recoverability;
- the proven working path.

When we are uncertain about the next action, return to this question:

```text
What is the smallest safe step that moves the project toward the alpha
without weakening privacy, evidence, validation, or instructor control?
```
