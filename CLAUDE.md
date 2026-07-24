# CLAUDE.md

## Purpose

This file provides repository-level instructions for Claude Code and other
repository-aware coding agents working on the Canvas Grading Assistant.

Read this file before proposing or making changes.

The project is a privacy-conscious, human-in-the-loop grading assistant for
programming assignments submitted through Canvas. It retrieves submissions,
creates AI-safe grading material, gathers local compilation and execution
evidence, requests an advisory model evaluation, validates the response, and
creates instructor-facing reports.

The AI does not assign the final grade. The instructor remains the final
authority.

---

## Current Project Status

The repository contains a working development prototype through Module 8.

The milestone tag:

```text
prototype-modules-1-through-8
```

marks the known working prototype.

Current branches:

- `main` — stable project history and integrated work
- `alpha-refactor` — active refactoring toward an end-user alpha

The numbered prototype modules intentionally create inspectable artifacts at
each stage. They must remain available until their replacements reproduce the
same behavior through automated tests.

Do not treat the current scripts as disposable merely because they are being
refactored.

---

## Immediate Refactoring Goal

The current goal is to transform the working Modules 1–8 prototype into a
coherent application architecture without changing proven behavior.

The first alpha should support:

1. Canvas course and assignment configuration
2. Submission discovery and retrieval
3. Safe ZIP download and extraction
4. Privacy-safe source preparation
5. Deterministic grading-package construction
6. Local compilation
7. Optional local execution with explicit consent and timeout
8. Provider-neutral advisory model evaluation
9. Structured-response validation
10. One-student instructor grading reports
11. Sequential multi-submission processing
12. Instructor review workbook generation
13. Import of instructor-approved grade records

The alpha must stop before Canvas grade writeback.

Canvas writeback belongs to a later, separate workflow with an explicit preview
and approval step.

---

## Non-Negotiable Project Principles

### 1. Preserve the Working Prototype

- Do not delete, rename, or substantially rewrite a numbered prototype module
  until its replacement is implemented and tested.
- Refactor incrementally.
- Prefer extracting reusable code over rewriting from scratch.
- Preserve the milestone tag and its historical value.
- Every refactoring step must leave the repository in a testable state.
- Do not combine unrelated architectural changes into one large patch.

### 2. Human Review Is Mandatory

- Model output is advisory only.
- Never describe an AI-generated score as final.
- Never automatically approve a grade.
- Never automatically post a grade or feedback to Canvas.
- Preserve explicit states such as:

```json
{
  "approval": {
    "status": "NOT_APPROVED",
    "final_score": null
  }
}
```

- Instructor approval must remain a separate, auditable action.

### 3. Privacy Boundaries Must Not Be Weakened

Private Canvas data and AI-facing material must remain separate.

Never send the following to a model provider:

- student names
- Canvas user IDs
- private attachment URLs
- original submission ZIP filenames
- private submission manifests
- grading reports with restored identities
- credentials or secrets
- information not required for grading

Student identity may be restored only after provider activity has completed and
the response has been saved and validated locally.

Any artifact containing restored identity must be marked private and:

```json
{
  "send_to_ai": false
}
```

Do not remove privacy checks to simplify a workflow or make a test pass.

### 4. Student Code Is Untrusted

Compilation and execution are different operations.

- Compilation may occur without executing the program.
- Student code may execute only when explicitly enabled.
- Preserve a hard execution timeout.
- Capture return code, stdout, stderr, timeout state, compiler information, and
  command details.
- Never silently execute student code.
- Do not claim the current local execution method is a hardened sandbox.
- Do not weaken path, archive, file-count, file-size, or extraction safeguards.

### 5. Objective Evidence Has Priority

Local objective evidence is stronger than inference from source code.

Examples include:

- compiler and compiler version
- compilation command
- return code
- warnings and errors
- runtime result
- timeout result
- stdout and stderr
- output comparison
- source-file inventory
- artifact inventory

A lack of local evidence is not evidence of failure.

When an item cannot be scored without missing local evidence, preserve:

```json
{
  "assessment_status": "requires_local_evidence",
  "suggested_points": null,
  "manual_review_needed": true
}
```

Do not convert uncertainty into an invented deduction.

### 6. Deterministic Validation Is Required

Do not use an AI model to convert required project data into the canonical
internal format.

Rubrics, grading packages, model responses, validation reports, and instructor
reports must use deterministic, versioned contracts.

Prefer:

- shared typed models
- JSON Schema
- explicit schema versions
- deterministic import and export
- strict validation
- clear migration rules

Do not rely on directory names, filenames, prompt text, or loosely structured
dictionaries when a shared contract can represent the same information.

### 7. Provider-Specific Code Must Stay Isolated

The grading workflow must remain provider-neutral.

Provider-specific behavior belongs behind an abstraction such as:

```text
grading/providers/
```

Do not spread OpenAI-specific request fields, response parsing, or configuration
throughout the application.

A provider implementation may adapt the shared request and result contracts,
but it must not redefine grading semantics.

### 8. Canvas Writes Must Be Explicitly Isolated

Current development through the alpha is read-only with respect to grades.

- Do not add Canvas grade or comment writeback to existing read workflows.
- Do not place read and write behavior in the same service method.
- Any future writeback must require:
  - validated instructor-approved grade records
  - a proposed-change preview
  - explicit confirmation
  - course and assignment identity checks
  - duplicate-post protection
  - an audit log

Never perform Canvas write operations during tests.

---

## Repository Work Rules

### Before Changing Code

1. Read `README.md`.
2. Read `ARCHITECTURE.md` when it exists.
3. Read `ROADMAP.md` when it exists.
4. Inspect the relevant prototype module and its artifacts.
5. Identify existing tests, fixtures, schemas, and call sites.
6. State the proposed scope before making broad changes.
7. Prefer the smallest change that advances the current phase.

Do not begin with a repository-wide rewrite.

### Task Scope Declaration

Before beginning a task, state:

- the exact files expected to change;
- the behavior being changed or preserved;
- the tests that will be added or run;
- actions that are explicitly out of scope;
- the condition at which work must stop for review.

Do not expand the task because adjacent cleanup appears convenient.
Do not modify files outside the stated scope without explicit approval.
Stop after completing the requested increment. Do not automatically begin the next roadmap task.

### For Repository Audits

When asked to audit or map the repository:

- inspect the full tracked repository
- do not modify production code unless explicitly asked
- identify responsibilities, inputs, outputs, side effects, and dependencies
- map existing functions and classes to proposed destinations
- identify duplication and shared contracts
- identify hidden coupling between modules
- identify privacy and write boundaries
- identify missing tests
- identify public-release risks
- produce findings before proposing large moves

### Change Size

Prefer small, reviewable steps.

Good:

- extract one parser
- introduce one typed model
- move one provider adapter
- add one integration test
- replace one prototype dependency with a service

Bad:

- redesign the whole repository in one commit
- rename every module while also changing behavior
- replace working validation with a new framework without regression tests
- delete prototype scripts before parity is proven

### Behavior Preservation

When refactoring, preserve:

- command-line behavior unless intentionally changed
- artifact contents and semantics
- privacy classifications
- schema validation behavior
- execution safety controls
- provider `store=false` behavior where supported
- Canvas-contact reporting
- instructor-review requirements
- score calculation rules
- failure messages that communicate safety state

If behavior must change, document why and add tests.

---

## Artifact and Storage Rules

Every important persisted artifact should contain, where appropriate:

```json
{
  "artifact_type": "descriptive_type",
  "schema_version": "1.0"
}
```

Artifacts should be:

- deterministic
- versioned
- independently validatable
- traceable to their source
- suitable for hashing
- explicit about privacy classification
- explicit about whether Canvas or a provider was contacted

Do not pass artifacts between application stages by launching prototype scripts
through subprocess calls.

Application workflows should call Python services directly and exchange typed
objects. Serialization is for persistence, inspection, resume, and audit.

Do not store private and AI-safe artifacts in the same undifferentiated
structure.

Generated student data and private run artifacts must remain outside version
control.

---

## Target Architectural Areas

The final layout may evolve, but responsibilities should remain separated into
areas resembling:

```text
config
domain
workflows
canvas
submissions
privacy
execution
grading
grading/providers
reporting
review
storage
```

Suggested responsibility boundaries:

### `domain`

Shared models, enums, identifiers, validation rules, and domain exceptions.

### `workflows`

Application-level orchestration. Workflows coordinate services but should not
contain provider, Canvas, ZIP, compiler, or spreadsheet implementation details.

### `canvas`

Canvas API access and translation between Canvas data and domain models.

Separate read services from future write services.

### `submissions`

Attempt selection, download, archive validation, extraction, and source
inventory.

### `privacy`

Anonymization, comment removal, exact-identifier redaction, PII scanning, and
privacy reports.

### `execution`

Compiler discovery, compilation, optional execution, timeout handling, and
output comparison.

### `grading`

Grading-package construction, prompt construction, shared response contracts,
domain validation, and provider abstractions.

### `reporting`

Canonical one-student reports and readable renderings.

### `review`

Future workbook generation, workbook import, and approved-grade records.

### `storage`

Workspace layout, run manifests, artifact storage, hashing, resume state, and
retention behavior.

---

## Testing Requirements

Tests must not contact Canvas or a model provider unless explicitly marked as
live integration tests.

Default tests must use local fixtures and mocks.

Preserve and expand regression coverage for:

1. known successful full-credit submission
2. compilation failure
3. compiler unavailable
4. missing source file
5. invalid archive
6. runtime timeout
7. runtime failure
8. output normalization
9. malformed provider response
10. schema-valid but domain-invalid response
11. missing local evidence
12. hallucinated evidence path
13. privacy leak
14. identity restoration
15. altered rubric IDs
16. invalid score totals
17. resume without duplicate provider requests
18. future workbook tampering

The known successful Modules 6–8 run should become a golden end-to-end fixture,
with private identity values replaced by synthetic data before being committed.

Tests must verify that:

- no Canvas write occurred
- no unexpected provider request occurred
- private data is absent from AI-facing artifacts
- score totals are calculated locally
- approval remains `NOT_APPROVED`
- errors fail safely

Do not use real student data in committed fixtures.

---

## Security and Public Repository Rules

This repository is intended to become public.

Never commit:

- `.env`
- API keys
- Canvas tokens
- provider secrets
- downloaded student submissions
- original submission ZIP files
- private manifests
- student names or Canvas user IDs
- private grading reports
- live model request or response files containing protected data
- generated `output`, `workspace`, or run directories

Do not inspect or quote sensitive local files unless the user explicitly asks
for that exact task.

Before making changes that affect `.gitignore`, secrets handling, or artifact
storage, consider the full Git history and public-release implications.

Use synthetic data in examples and tests.

---

## Configuration Rules

Configuration must distinguish among:

1. application settings
2. Canvas connection settings
3. provider profiles
4. compiler and toolchain profiles
5. assignment-package settings
6. run-specific choices

Secrets must come from environment variables or an approved secret store.

Do not place secrets in:

- source files
- JSON configuration committed to Git
- Markdown documentation
- test fixtures
- logs
- exception messages

Configuration errors should fail before a grading run begins.

The eventual application should perform a preflight check before processing
submissions.

---

## Logging and Error Handling

Errors should be specific, actionable, and safe.

Every stage should communicate:

- what failed
- which artifact or stage was involved
- whether Canvas was contacted
- whether a model provider was contacted
- whether student code was executed
- whether partial output was preserved
- whether retry or resume is safe

Do not expose credentials, authorization headers, private URLs, or student
identity in logs intended for public issue reports.

Prefer domain-specific exceptions over generic exceptions when the distinction
helps recovery.

One failed submission must not eventually stop an entire assignment batch.

---

## Documentation Rules

Update documentation when behavior, architecture, commands, artifacts, or
safety boundaries change.

Public documentation must clearly distinguish among:

- working behavior
- prototype behavior
- planned alpha behavior
- future goals

Do not document commands or interfaces as available before they exist.

Important architectural decisions should be recorded in `ARCHITECTURE.md` or an
appropriate architecture decision record rather than living only in chat or
commit messages.

---

## Code Quality Expectations

- Use Python type hints.
- Prefer small functions with one responsibility.
- Avoid unnecessary inheritance.
- Use dataclasses or validated models when they clarify contracts.
- Use `pathlib.Path` for filesystem paths.
- Keep I/O at system boundaries.
- Separate pure calculation from persistence and network access.
- Avoid global mutable state.
- Preserve clear command-line error messages.
- Do not add dependencies without explaining the benefit.
- Keep Windows compatibility in mind.
- Do not assume a Unix-only shell or filesystem layout.
- Keep line lengths and formatting consistent with the existing project unless
  a formatter is intentionally adopted.
- Follow PEP 8 for new and modified Python code unless an established project
  convention or generated format requires otherwise.
- Prefer readability over mechanical rule compliance.
- Do not reformat unrelated files or perform repository-wide style changes
  without explicit approval.
- New or modified code should pass the project's configured formatter and
  linter once those tools are adopted.

---

## Git and Commit Practices

Work on the branch specified by the user.

Do not commit directly to `main` unless explicitly instructed.

Before declaring a task complete:

1. inspect the diff
2. run relevant tests
3. report files changed
4. report tests run
5. report unresolved concerns
6. confirm no private files were added
7. confirm no Canvas or provider call occurred unless explicitly requested

Prefer descriptive, focused commits.

Do not rewrite published Git history, move tags, force-push, or delete branches
without explicit user approval.

---

## Definition of Done for a Refactoring Step

A refactoring step is complete only when:

- the intended responsibility has a clear home
- behavior is preserved or the intentional change is documented
- relevant tests pass
- privacy boundaries remain intact
- execution safety remains intact
- provider isolation remains intact
- Canvas write boundaries remain intact
- artifacts remain valid and traceable
- public documentation is accurate
- the prototype path remains recoverable

“Code moved” is not sufficient.

---

## Prohibited Shortcuts

Do not:

- rewrite the entire project in one pass
- delete working prototype scripts prematurely
- combine Canvas reads and writes
- send private artifacts to a provider
- infer final approval from an AI score
- execute student code without explicit authorization
- remove timeouts or archive limits
- convert missing evidence into lost points
- trust a model-generated total without local calculation
- use AI to create canonical rubric data at runtime
- silently change artifact formats
- hardcode the Cars assignment into reusable application services
- hardcode OpenAI assumptions into shared grading logic
- create a GUI before the internal workflow and input contracts stabilize
- claim success without tests
- expose secrets or student data in logs, examples, fixtures, or commits

---

## Session Startup Protocol

At the beginning of every new working session:

1. Read CLAUDE.md.
2. Read ARCHITECTURE.md and ROADMAP.md when they exist.
3. Confirm the current Git branch.
4. Run git status.
5. Review recent commits relevant to the current phase.
6. Inspect existing tests, artifacts, and documentation related to the requested task.
7. Determine what work has already been completed before proposing changes.
8. Do not repeat a completed audit, migration, or refactoring step unless explicitly asked to verify or update it.
9. Summarize the current state and intended scope before making broad changes.

This startup review should be lightweight. Its purpose is to restore context and prevent duplicated, conflicting, or obsolete work.

---

## Current Project Phase

Phases 0 through 4 are complete: Freeze the Working Prototype, Documentation
Foundation, Public-Release Safety Audit, Read-Only Repository Inventory, and
Artifact Contract Inventory (including the OD-001 domain-model-library
decision). See `ROADMAP.md` for full phase detail.

**Phase 5 — Shared Domain Models is the current phase.**

The immediate next increment is the testing foundation, not model
extraction:

- add `pytest` as an intentional test dependency;
- establish minimal test configuration and directories;
- add synthetic Module 5.1 AI-package-manifest fixtures;
- characterize the current Module 6 `validate_ai_manifest()` behavior.

No shared-model extraction may begin until the relevant characterization
tests pass. `PrivacyClassification`/`ArtifactMetadata` is the accepted first
model target (see `ARTIFACT_CONTRACTS.md` and
`OD-001_DOMAIN_MODEL_LIBRARY.md`).

No numbered module may be deleted, renamed, moved, retired, or modified
during the initial testing-foundation increment. That increment makes no
Canvas calls, no model-provider calls, and executes no student code.

---

## Final Instruction

When convenience conflicts with privacy, validation, auditability, instructor
control, or preservation of proven behavior, choose the safer and more
traceable design.

Ask for explicit approval before any action that could:

- contact Canvas
- contact a model provider
- execute student code
- modify grades or feedback
- delete or overwrite private artifacts
- rewrite Git history
- remove a working prototype path
