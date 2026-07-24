# ARCHITECTURE.md

## Document Purpose

This document describes the architecture of the Canvas Grading Assistant.

It records:

- the current working prototype;
- the target end-user alpha;
- system boundaries;
- privacy and trust boundaries;
- artifact flow;
- major components and responsibilities;
- provider abstraction;
- execution safety;
- storage and resumability;
- instructor review and approval boundaries;
- architectural decisions already made;
- important decisions still open.

This document describes how the system is designed.

Repository work rules for Claude Code and other coding agents belong in
`CLAUDE.md`.

Project sequencing and phase completion belong in `ROADMAP.md`.

---

## Project Summary

The Canvas Grading Assistant is a privacy-conscious, human-in-the-loop grading
assistant for programming assignments submitted through Canvas.

The system is intended to:

1. inspect a Canvas course and assignment;
2. discover and retrieve student submissions;
3. safely extract submitted archives;
4. create an AI-safe copy of student source code;
5. construct a deterministic grading package;
6. gather local compilation and execution evidence;
7. request an advisory grading evaluation from a configured model provider;
8. validate the structured response;
9. create instructor-facing reports;
10. support instructor review and approval;
11. eventually post approved grades and feedback to Canvas through a separate,
    explicit write workflow.

The model provider is advisory only.

The instructor remains the final grading authority.

---

## Current Architecture Status

The repository contains a working prototype through Module 8.

The milestone tag:

```text
prototype-modules-1-through-8
```

marks the known working development state.

The prototype is intentionally artifact-driven:

```text
Module 1
  produces artifacts consumed by Module 2

Module 2
  produces artifacts consumed by Module 3

...

Module 8
  produces a private one-student grading report
```

This approach has been valuable because it makes each stage:

- inspectable;
- testable in isolation;
- easy to debug;
- easy to rerun;
- auditable;
- resistant to hidden state.

The alpha refactor must preserve those advantages while replacing script-to-
script command execution with direct Python service calls and typed contracts.

---

## Architectural Goals

The target alpha should provide:

- a coherent application rather than a collection of loosely coordinated
  scripts;
- reusable services;
- shared domain models;
- deterministic artifact schemas;
- explicit privacy boundaries;
- explicit execution controls;
- provider-neutral grading;
- resumable workflows;
- auditability;
- local score calculation;
- instructor review;
- sequential batch processing;
- separation between advisory output, instructor approval, and Canvas writes.

---

## Non-Goals for the Initial Alpha

The initial alpha will not attempt to provide:

- autonomous grading;
- automatic grade approval;
- automatic Canvas writeback;
- hardened hostile-code sandboxing;
- parallel batch processing;
- arbitrary document-to-rubric conversion through AI;
- arbitrary programming-language support;
- production-grade institutional deployment;
- a full graphical user interface;
- invisible or irreversible background behavior.

These may become later goals, but they must not distort the first alpha.

---

## Architectural Principles

### Human-in-the-Loop

The system may suggest scores and feedback.

It must not:

- declare grades final;
- approve grades automatically;
- post grades automatically;
- suppress instructor review;
- treat model confidence as instructor approval.

### Privacy by Separation

Private identity-bearing data and AI-safe grading data are separate domains.

The model provider should receive only the minimum information needed to assess
the submission.

### Deterministic Contracts

Critical inputs and outputs use explicit, versioned schemas.

The system must not depend on an AI model to create canonical rubric or grading
data.

### Objective Evidence Before Inference

Compiler, runtime, and artifact evidence outrank assumptions derived from source
inspection alone.

Missing evidence is not proof of failure.

### Fail Safely

When data is invalid, evidence is missing, identity cannot be resolved, or a
workflow stage fails, the system should stop or isolate the failure without
inventing a result.

### Preserve Proven Behavior

The alpha refactor must reproduce the working prototype before the prototype
scripts are retired.

---

## System Context

```text
+------------------+
| Instructor       |
|                  |
| - configures run |
| - supplies rubric|
| - reviews result |
| - approves grade |
+---------+--------+
          |
          v
+------------------------------+
| Canvas Grading Assistant     |
|                              |
| - Canvas integration         |
| - submission handling        |
| - privacy transformation     |
| - local evidence             |
| - model evaluation           |
| - validation                 |
| - reporting                  |
| - review workflow            |
+----+--------------------+----+
     |                    |
     v                    v
+-----------+      +----------------+
| Canvas    |      | Model Provider |
|           |      |                |
| course    |      | advisory only  |
| assignment|      | no identity    |
| submission|      | structured JSON|
+-----------+      +----------------+

Additional local dependency:

+----------------+
| Local Toolchain|
|                |
| compiler       |
| runtime        |
| output compare |
+----------------+
```

---

## Trust Boundaries

The project has five important trust zones.

### Zone 1 — Private Canvas Data

Contains:

- student names;
- Canvas user IDs;
- attachment IDs;
- private URLs;
- course identifiers;
- assignment identifiers;
- submission metadata;
- original filenames;
- late or missing status;
- private manifests.

This zone is local and private.

Artifacts in this zone must be marked:

```json
{
  "send_to_ai": false
}
```

### Zone 2 — Original Student Submission

Contains the exact downloaded submission.

It is:

- private;
- untrusted;
- potentially malformed;
- potentially hostile;
- preserved separately from transformed copies.

The original must not be modified in place.

### Zone 3 — AI-Safe Grading Material

Contains only the information approved for provider use.

This may include:

- anonymized source files;
- assignment specification;
- rubric;
- instructor grading notes;
- reference files;
- safe supporting files;
- local compilation and execution evidence;
- output comparison evidence.

This zone must exclude student identity and private Canvas details.

### Zone 4 — Provider Boundary

The provider receives an advisory grading request.

Provider behavior must be treated as external and untrusted.

The returned response must be:

- parsed;
- schema-validated;
- domain-validated;
- reconciled locally;
- treated as advisory.

### Zone 5 — Private Instructor Report

After provider activity is complete, the local system may restore the student's
identity and create a private instructor report.

This report must not be sent back to a model provider.

It remains unapproved until the instructor explicitly approves it.

---

## High-Level Data Flow

```text
Canvas configuration
        |
        v
Course and assignment selection
        |
        v
Private submission discovery
        |
        v
Attempt selection
        |
        v
ZIP download
        |
        v
Archive validation and extraction
        |
        +------------------------------+
        |                              |
        v                              v
Original private copy           AI-candidate copy
                                       |
                                       v
                           Comment removal and redaction
                                       |
                                       v
                           Privacy validation and preview
                                       |
                                       v
                            Grading package construction
                                       |
                       +---------------+---------------+
                       |                               |
                       v                               v
               Local compilation              Static source review
                       |
                       v
               Optional execution
                       |
                       v
               Output comparison
                       |
                       +---------------+
                                       |
                                       v
                           Provider-neutral request
                                       |
                                       v
                           Model provider response
                                       |
                                       v
                        Schema and domain validation
                                       |
                                       v
                          Local score reconciliation
                                       |
                                       v
                     Identity restoration from private map
                                       |
                                       v
                        One-student instructor report
```

Future alpha continuation:

```text
One-student reports
        |
        v
Sequential assignment processing
        |
        v
Instructor review workbook
        |
        v
Edited workbook import
        |
        v
Approved grade JSON
```

Later version 1:

```text
Approved grade JSON
        |
        v
Canvas change preview
        |
        v
Explicit instructor confirmation
        |
        v
Canvas writeback
        |
        v
Write audit log
```

---

## Current Prototype Modules

The exact implementation may evolve, but the working prototype responsibilities
are approximately:

### Module 1 — Canvas Course Exploration

Responsibilities:

- connect to Canvas;
- retrieve course information;
- verify configuration;
- establish read access.

### Module 2 — Assignment Inspection

Responsibilities:

- identify a target assignment;
- retrieve assignment metadata;
- inspect assignment configuration.

### Module 3 — Submission Discovery

Responsibilities:

- list submissions;
- create anonymous labels;
- create private and AI-safe manifests;
- preserve identity mapping locally.

### Module 4 — Submission Download and Extraction

Responsibilities:

- select the latest valid attempt;
- retrieve one submitted ZIP;
- validate archive limits;
- extract safely;
- preserve original filenames and paths;
- produce a private extraction manifest.

### Module 5 / 5.1 — AI-Candidate Preparation

Responsibilities:

- create a separate candidate copy;
- remove C/C++ comments;
- redact known identifiers;
- preserve useful line positions;
- create privacy reports and outbound previews;
- avoid modifying the original submission.

### Module 6 — Grading Package Construction

Responsibilities:

- load assignment assets;
- load rubric and notes;
- collect student material;
- collect local objective evidence;
- construct provider-neutral grading data;
- validate the package;
- emit request artifacts.

### Module 7 — Model Evaluation and Validation

Responsibilities:

- select a provider profile;
- construct one structured request;
- send exactly one grading request;
- save provider response;
- validate JSON, schema, identity, and domain rules;
- preserve provider metadata;
- support local revalidation without another provider call.

### Module 8 — One-Student Instructor Report

Responsibilities:

- require a valid Module 7 result;
- calculate rubric totals locally;
- apply global adjustments deterministically;
- restore student identity locally;
- produce canonical JSON;
- produce readable Markdown;
- retain `NOT_APPROVED` status;
- contact neither Canvas nor a model provider.

---

## Target Package Architecture

The target layout may evolve during audit and implementation, but the following
areas represent the intended responsibility boundaries.

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

---

## Component Responsibilities

### `config`

Responsible for:

- application settings;
- environment loading;
- Canvas connection configuration;
- provider profiles;
- compiler and toolchain profiles;
- assignment package configuration;
- run-specific options;
- preflight validation.

It should not contain:

- Canvas API logic;
- grading calculations;
- provider request code;
- student data.

### `domain`

Responsible for:

- shared domain models;
- enums;
- identifiers;
- schema versions;
- validation rules;
- domain exceptions;
- score and approval semantics.

Examples:

```text
CourseRef
AssignmentRef
SubmissionRef
SubmissionAttempt
Rubric
RubricCriterion
RubricItem
CompileEvidence
ExecutionEvidence
GradingResult
InstructorReport
ApprovalStatus
```

The domain layer should avoid direct network and filesystem operations.

### `workflows`

Responsible for application-level orchestration.

Examples:

```text
inspect_assignment
process_one_submission
process_assignment
create_review_workbook
import_approved_grades
preview_canvas_changes
commit_canvas_changes
```

Workflows coordinate lower-level services.

They should not contain:

- raw Canvas API details;
- ZIP extraction implementation;
- compiler subprocess implementation;
- provider-specific request fields;
- spreadsheet cell formatting internals.

### `canvas`

Responsible for Canvas API integration.

Possible services:

```text
CourseService
AssignmentService
SubmissionService
GradeReadService
GradeWriteService
```

Read and write responsibilities must remain separate.

Canvas records should be translated into domain models at the boundary.

### `submissions`

Responsible for:

- attempt selection;
- attachment selection;
- secure download;
- archive validation;
- safe extraction;
- source inventory;
- original-submission preservation.

Archive validation must protect against:

- path traversal;
- absolute paths;
- excessive file count;
- excessive extracted size;
- compression bombs;
- oversized individual files;
- unsupported archive structure.

### `privacy`

Responsible for:

- anonymization;
- known-identifier removal;
- C/C++ comment removal;
- line preservation;
- PII scanning;
- privacy classification;
- outbound approval reports;
- private versus AI-safe artifact separation.

Privacy checks must be explicit and independently testable.

### `execution`

Responsible for:

- compiler discovery;
- compiler version capture;
- compile-command construction;
- compilation;
- warning and error capture;
- explicit execution permission;
- runtime timeout;
- stdout and stderr capture;
- return-code capture;
- output normalization;
- output comparison.

The alpha should treat student code as untrusted and should not claim to provide
a hardened sandbox.

### `grading`

Responsible for:

- grading-package construction;
- prompt construction;
- response schema;
- rubric semantics;
- evidence representation;
- local result validation;
- local score reconciliation;
- global deduction and cap handling.

Shared grading code must remain provider-neutral.

### `grading/providers`

Responsible for provider adapters.

Each adapter should implement a shared conceptual interface such as:

```python
class GradingProvider:
    def evaluate(
        self,
        request: GradingRequest,
    ) -> ProviderResponse:
        ...
```

The provider layer may adapt:

- authentication;
- endpoint details;
- model selection;
- structured-output fields;
- usage metadata;
- provider-specific errors.

It must not redefine:

- rubric meaning;
- score semantics;
- approval semantics;
- privacy policy;
- local validation rules.

### `reporting`

Responsible for:

- canonical one-student report generation;
- readable Markdown or HTML rendering;
- report validation;
- provenance;
- hashing;
- identity restoration after provider activity;
- explicit advisory and approval status.

The canonical JSON report is authoritative.

Readable formats are renderings.

### `review`

Responsible for future:

- instructor review workbook generation;
- workbook protection;
- editable versus immutable fields;
- workbook import;
- tamper detection;
- approved-grade record creation.

Workbook data must never become authoritative merely because Excel calculated a
formula.

All important values must be validated again during import.

### `storage`

Responsible for:

- workspace layout;
- artifact persistence;
- run identifiers;
- submission-stage status;
- resume behavior;
- source hashes;
- manifests;
- audit records;
- retention and cleanup.

Storage should make every run traceable and restartable.

---

## Application Workflow Boundaries

### Inspect Assignment Workflow

Inputs:

- Canvas configuration;
- course selection;
- assignment selection.

Outputs:

- assignment summary;
- assignment reference;
- initial package guidance.

Side effects:

- Canvas read operations only.

### Process One Submission Workflow

Inputs:

- assignment reference;
- submission reference;
- grading asset package;
- provider profile;
- toolchain profile;
- execution policy;
- workspace.

Outputs:

- validated one-student instructor report.

Major stages:

```text
discover
download
extract
sanitize
package
compile
execute
compare
evaluate
validate
report
```

Each stage should have an explicit status.

### Process Assignment Workflow

Inputs:

- assignment reference;
- grading asset package;
- run policy.

Outputs:

- one report per submission;
- batch manifest;
- failure summary;
- usage summary.

The alpha should process submissions sequentially.

One submission failure must not terminate the entire assignment run.

### Review Workbook Workflow

Inputs:

- canonical one-student reports.

Outputs:

- instructor review workbook;
- workbook manifest;
- source hashes.

### Approved Grade Import Workflow

Inputs:

- edited workbook;
- workbook manifest;
- original report set.

Outputs:

- approved-grade JSON per student;
- approved-grade batch manifest;
- validation report.

No Canvas write occurs.

### Canvas Change Preview Workflow

Future version 1.

Inputs:

- approved-grade records;
- current Canvas grade state.

Outputs:

- proposed change set.

No write occurs.

### Canvas Commit Workflow

Future version 1.

Inputs:

- validated proposed change set;
- explicit instructor confirmation.

Outputs:

- write results;
- audit log;
- duplicate-post protection record.

---

## Artifact Architecture

Artifacts should use explicit metadata.

Recommended common envelope:

```json
{
  "artifact_type": "grading_result",
  "schema_version": "1.0",
  "created_at_utc": "2026-07-24T00:00:00Z",
  "privacy": {
    "classification": "AI-safe",
    "send_to_ai": true
  }
}
```

Not every artifact requires exactly the same fields, but important artifacts
should be self-describing.

---

## Important Artifact Types

### Private Submission Manifest

Contains:

- anonymous label;
- Canvas user ID;
- student name;
- assignment ID;
- attempt metadata;
- attachment metadata;
- private URLs where required.

Classification:

```text
PRIVATE
send_to_ai = false
```

### AI-Safe Submission Manifest

Contains only non-identifying submission metadata needed for workflow.

Classification:

```text
AI-safe
send_to_ai = true
```

### Extraction Manifest

Contains:

- archive properties;
- extracted file inventory;
- hashes;
- safety decisions;
- selected attempt;
- local paths.

Classification:

```text
PRIVATE
send_to_ai = false
```

### AI-Safe Student Material

Contains:

- sanitized source files;
- relative paths;
- line information;
- safe file inventory;
- sanitization metadata.

Classification:

```text
AI-safe
send_to_ai = true
```

### Grading Package

Contains:

- assignment specification;
- rubric;
- instructor notes;
- reference material;
- supporting files;
- objective evidence;
- grading policy.

Classification:

```text
AI-safe
send_to_ai = true
```

### Grading Result

Contains:

- rubric item assessments;
- suggested points;
- rationale;
- evidence;
- confidence;
- global rule assessments;
- draft feedback;
- instructor summary;
- review flags.

Classification:

```text
AI-safe until identity is restored
```

### Validation Report

Contains:

- JSON parse status;
- schema status;
- anonymous-label status;
- domain-validation status;
- errors;
- warnings;
- overall validity.

### One-Student Instructor Report

Contains:

- restored identity;
- authoritative rubric totals;
- advisory score;
- evidence;
- feedback draft;
- provenance;
- source hashes;
- explicit unapproved state.

Classification:

```text
PRIVATE
send_to_ai = false
```

### Approved Grade Record

Future alpha artifact.

Contains:

- student identity;
- final instructor score;
- approved feedback;
- approval metadata;
- source report hashes;
- workbook provenance.

Classification:

```text
PRIVATE
send_to_ai = false
```

---

## Artifact Contract Rules

Every artifact contract should specify:

- required fields;
- optional fields;
- schema version;
- privacy classification;
- allowed state transitions;
- validation behavior;
- canonical serialization;
- migration strategy;
- hash behavior.

Artifacts should not be silently reinterpreted.

When a schema changes:

1. increment the schema version;
2. document the change;
3. provide deterministic migration when practical;
4. preserve older fixtures;
5. reject incompatible artifacts clearly.

---

## Identity and Anonymity Model

The system assigns each submission an anonymous label:

```text
submission_001
submission_002
submission_003
```

The private identity map links the anonymous label to Canvas identity.

The model provider sees only the anonymous label.

The report layer may restore identity after:

1. provider response is saved;
2. provider activity is complete;
3. the result is validated;
4. the correct private manifest is loaded;
5. assignment and attempt identity are reconciled.

Identity restoration must fail if:

- the anonymous label has no match;
- multiple private records match;
- assignment identifiers conflict;
- attempt identifiers conflict;
- the manifest is not explicitly private.

---

## Score Architecture

The model does not own the total score.

The provider returns item-level advisory assessments.

The local application calculates:

```text
rubric item scores
        |
        v
criterion totals
        |
        v
base score
        |
        v
approved global deductions
        |
        v
approved score caps
        |
        v
advisory total
```

For Module 8, the deductions and caps are still model recommendations, but the
calculation itself is local and deterministic.

Future instructor approval may override individual points or feedback.

The final approved score must be recalculated from approved item values and
validated locally.

---

## Missing Evidence Semantics

When evidence required for a rubric item is unavailable, the valid state is:

```json
{
  "assessment_status": "requires_local_evidence",
  "suggested_points": null,
  "manual_review_needed": true
}
```

The system should preserve:

- known scored subtotal;
- unresolved item IDs;
- missing evidence explanation;
- review requirement.

It should not invent:

- a zero;
- partial credit;
- a full-credit assumption;
- a final total.

---

## Global Rule Architecture

Global grading rules may include:

- noncompiling cap;
- missing-file deduction;
- incorrect-filename deduction;
- missing-ZIP deduction;
- composition-failure cap or deduction.

Each rule assessment should contain:

```json
{
  "rule_id": "noncompiling_cap",
  "applicable": false,
  "recommended_action": "none",
  "recommended_value": 0,
  "rationale": "...",
  "manual_review_needed": false
}
```

Supported actions should be explicit:

```text
none
deduction
score_cap
```

The local application validates rule consistency and calculates the resulting
advisory total.

---

## Provider Architecture

The system must support multiple model providers without spreading provider
logic across the application.

Shared provider input:

```text
GradingRequest
```

Shared provider output:

```text
ProviderResponse
```

Shared validated result:

```text
GradingResult
```

A provider adapter is responsible for:

- model naming;
- authentication;
- request translation;
- structured-output configuration;
- usage metadata;
- provider status;
- error translation.

A provider adapter is not responsible for:

- restoring identity;
- calculating final scores;
- approving grades;
- deciding privacy policy;
- posting to Canvas.

---

## Provider Request Lifecycle

```text
Validated grading package
        |
        v
Prompt builder
        |
        v
Provider-neutral request
        |
        v
Provider adapter
        |
        v
External model provider
        |
        v
Raw provider response
        |
        v
Structured response extraction
        |
        v
Schema validation
        |
        v
Domain validation
        |
        v
Saved grading result
```

Every paid request should be recorded with:

- provider;
- requested model;
- resolved model if available;
- response ID;
- elapsed time;
- token usage;
- request hashes;
- response hashes;
- validation status;
- whether data storage was disabled where supported.

A saved response should be locally revalidatable without another provider call.

---

## Canvas Architecture

Canvas access should be divided by capability.

### Read Capabilities

- get course;
- list assignments;
- inspect assignment;
- list submissions;
- retrieve submission history;
- retrieve attachment information;
- download attachment;
- read current grade and feedback state.

### Write Capabilities

Future only:

- post grade;
- post feedback;
- update rubric assessment if supported;
- record write result.

Read and write credentials may be the same token operationally, but code paths
must remain separate.

The alpha should provide no grade-write workflow.

---

## Canvas Write Safety

Future Canvas writeback must require:

1. approved-grade artifact;
2. matching course ID;
3. matching assignment ID;
4. matching Canvas user ID;
5. current-state read;
6. proposed-change preview;
7. explicit instructor confirmation;
8. duplicate-write detection;
9. write result capture;
10. audit log.

The system must never infer approval from:

- workbook presence;
- model confidence;
- report completion;
- a non-null suggested score;
- batch success.

---

## Local Execution Architecture

Student code is untrusted.

Compilation and execution must remain distinct.

### Compilation Stage

Captures:

- compiler path;
- compiler name;
- compiler version;
- language standard;
- command;
- working directory;
- return code;
- stdout;
- stderr;
- timeout if compilation is limited;
- source-file list.

### Execution Stage

Requires explicit enablement.

Captures:

- executable path;
- command;
- working directory;
- return code;
- stdout;
- stderr;
- timeout;
- elapsed time;
- input files;
- environment restrictions where implemented.

### Output Comparison Stage

May support:

- exact comparison;
- normalized whitespace comparison;
- normalized nonblank line comparison;
- instructor-configured tolerances.

Comparison policy belongs in the assignment package.

---

## Assignment Package Architecture

The application must generalize beyond the Cars assignment.

A grading asset package should resemble:

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

### `assignment.json`

Contains:

- package ID;
- title;
- language;
- expected standard;
- assignment description;
- required source patterns;
- submission expectations.

### `rubric.json`

Contains deterministic rubric structure:

- rubric ID;
- schema version;
- maximum points;
- criteria;
- items;
- item maximums;
- evidence expectations.

### `instructor_notes.md`

Contains grading guidance that supplements but does not override the rubric
unless explicitly defined.

### `package_config.json`

Contains:

- compile policy;
- execution policy;
- output comparison policy;
- file expectations;
- global grading rules;
- provider prompt settings;
- safe supporting-file configuration.

Assignment packages should be validated before a grading run begins.

---

## Deterministic Rubric Input

The application should eventually support:

1. guided CLI entry;
2. graphical form entry;
3. canonical JSON;
4. documented CSV import.

The application should not require a model provider to transform an instructor
rubric into canonical JSON.

Any import path must produce the same validated internal model.

---

## Workspace Architecture

Recommended workspace layout:

```text
workspace/
└── course_<course_id>/
    └── assignment_<assignment_id>/
        └── run_<run_id>/
            ├── run_manifest.json
            ├── assignment_package_snapshot/
            ├── submissions/
            │   ├── submission_001/
            │   │   ├── private/
            │   │   ├── original/
            │   │   ├── ai_safe/
            │   │   ├── evidence/
            │   │   ├── provider_runs/
            │   │   └── reports/
            │   └── submission_002/
            ├── batch/
            └── logs/
```

Private and AI-safe artifacts should remain visibly separated.

---

## Run Manifest

The run manifest should record:

- run ID;
- course and assignment;
- assignment package version and hash;
- provider profile;
- toolchain profile;
- execution policy;
- start and completion time;
- per-submission stage status;
- errors;
- retry eligibility;
- provider usage;
- approval status;
- Canvas write status.

Example stage record:

```json
{
  "submission_001": {
    "download": "complete",
    "extraction": "complete",
    "sanitization": "complete",
    "package": "complete",
    "compilation": "complete",
    "execution": "complete",
    "evaluation": "complete",
    "validation": "complete",
    "report": "complete"
  }
}
```

Supported conceptual states:

```text
not_started
in_progress
complete
failed
blocked
skipped
requires_review
```

---

## Resumability

The system should be restartable after interruption.

Before rerunning a stage, the workflow should check:

- prior stage status;
- source hashes;
- assignment package hash;
- provider request hash;
- existing artifact validity;
- whether retry is safe;
- whether another paid provider request would be duplicated.

The system should never repeat a paid provider request merely because the
application was restarted.

Explicit `--force` or equivalent behavior may invalidate or replace prior stage
artifacts, but it must be deliberate and logged.

---

## Batch Processing

The initial alpha should process submissions sequentially.

Reasons:

- easier error isolation;
- simpler provider rate management;
- simpler compiler and runtime management;
- easier audit trails;
- simpler resume behavior;
- reduced risk of overlapping logs and artifacts.

Future parallel execution may be considered only after:

- workspace isolation is proven;
- provider limits are handled;
- local execution isolation is improved;
- deterministic resume behavior is tested.

---

## Instructor Review Workbook

Future Module 8C.

The workbook should consume canonical one-student report JSON only.

Recommended sheets:

```text
Summary
Rubric Detail
Review Flags
Run Information
```

Editable fields:

- instructor item points;
- instructor feedback;
- instructor notes;
- approval status.

Immutable or protected fields:

- Canvas user ID;
- anonymous label;
- rubric item ID;
- maximum points;
- run ID;
- report hash;
- assignment ID.

The workbook is a review surface, not the source of truth.

---

## Approved Grade Import

Future Module 8D.

Workbook import must verify:

- workbook manifest;
- run identity;
- assignment identity;
- report hashes;
- student identity;
- rubric item IDs;
- maximum values;
- score ranges;
- missing rows;
- duplicate rows;
- total consistency;
- explicit approval value.

Supported approval values should be exact:

```text
APPROVED
NEEDS_REVIEW
DO_NOT_POST
```

Imported records should produce deterministic approved-grade JSON.

---

## Configuration Architecture

Configuration should be separated by scope.

### Application Settings

Examples:

- workspace root;
- logging level;
- retention policy;
- default output format.

### Canvas Settings

Examples:

- Canvas URL;
- course ID;
- token source.

### Provider Profile

Examples:

- provider type;
- model;
- reasoning setting;
- timeout;
- structured-output behavior;
- storage preference.

### Toolchain Profile

Examples:

- compiler path;
- language standard;
- warning flags;
- compile timeout;
- run timeout.

### Assignment Package Settings

Examples:

- required files;
- compile inputs;
- runtime inputs;
- output policy;
- global grading rules.

### Run Choices

Examples:

- one submission or all;
- execute student code;
- retry failed stages;
- overwrite behavior;
- provider profile selection.

Secrets belong in environment variables or approved secret stores.

---

## Preflight Architecture

Before processing begins, the application should validate:

- Canvas URL and token availability;
- course existence;
- assignment existence;
- workspace permissions;
- assignment package validity;
- rubric total consistency;
- provider configuration;
- compiler availability;
- execution policy;
- required reference files;
- output comparison inputs;
- privacy configuration.

The batch should not begin and later pause for routine configuration input.

---

## Error Architecture

Errors should be categorized.

Suggested categories:

```text
ConfigurationError
CanvasReadError
CanvasWriteError
SubmissionSelectionError
ArchiveValidationError
PrivacyValidationError
PackageValidationError
CompilerUnavailableError
CompilationError
ExecutionTimeoutError
ProviderError
ResponseValidationError
IdentityResolutionError
ReportValidationError
WorkbookValidationError
ApprovalValidationError
```

Every failed stage should report:

- stage;
- submission label;
- safe error message;
- whether Canvas was contacted;
- whether a provider was contacted;
- whether student code executed;
- whether partial artifacts were preserved;
- whether retry is safe.

---

## Logging Architecture

Logs should support diagnosis without exposing private data.

Logs intended for general debugging should avoid:

- student names;
- Canvas user IDs;
- attachment URLs;
- authorization headers;
- API keys;
- raw private manifests;
- full source code;
- private feedback.

Private audit logs may include identifiers when required, but they must remain
inside the private workspace.

---

## Testing Architecture

The system needs three test layers.

### Unit Tests

Test pure or isolated behavior:

- attempt selection;
- archive path validation;
- comment removal;
- identifier redaction;
- rubric validation;
- score calculation;
- evidence-path validation;
- output normalization;
- approval-state validation.

### Integration Tests

Test multiple local components:

- extract and sanitize a synthetic submission;
- compile and run a safe fixture;
- build a grading package;
- validate a saved provider response;
- generate a one-student report;
- resume from saved artifacts.

### Live Integration Tests

Explicit only:

- Canvas read connection;
- live provider request;
- future Canvas write test in a dedicated safe environment.

Live tests must never run by default.

---

## Golden Fixtures

The current successful one-student run should inspire a synthetic golden fixture.

The committed fixture must replace real identity with synthetic values.

Recommended fixture set:

1. full-credit successful submission;
2. noncompiling submission;
3. missing-file submission;
4. runtime-timeout submission;
5. malformed provider response;
6. schema-valid but domain-invalid response;
7. missing local evidence;
8. hallucinated evidence path;
9. privacy leak;
10. altered workbook record.

---

## Public Repository Architecture

The repository is intended to become public.

Public source must not contain:

- live `.env`;
- Canvas tokens;
- provider keys;
- original student ZIP files;
- downloaded submissions;
- private manifests;
- student identity;
- private grading reports;
- live provider artifacts containing protected information;
- generated workspace directories.

Examples and fixtures must use synthetic data.

---

## Branch and Milestone Strategy

Current branches:

```text
main
alpha-refactor
```

Current milestone tag:

```text
prototype-modules-1-through-8
```

Recommended meaning:

### `main`

Stable integrated state.

### `alpha-refactor`

Active refactoring toward the application architecture.

### Prototype Tag

Permanent reference to the proven Modules 1–8 implementation.

The tag must not be moved.

---

## Migration Strategy

The refactor should proceed by replacement through parity.

For each responsibility:

1. identify current implementation;
2. define shared contract;
3. extract or adapt reusable logic;
4. write tests;
5. add new service;
6. connect new service through a workflow;
7. compare output with prototype;
8. preserve prototype path;
9. retire old path only after parity is demonstrated.

This is a strangler-style migration rather than a rewrite.

---

## Alpha Completion Criteria

The end-user alpha is complete when it can:

1. configure Canvas, provider, toolchain, workspace, and assignment package;
2. validate all required inputs before processing;
3. process one submission end to end;
4. reproduce the known one-student report behavior;
5. process several or all submissions sequentially;
6. isolate per-submission failures;
7. resume without duplicate provider requests;
8. generate an instructor review workbook;
9. import workbook edits;
10. create validated approved-grade JSON;
11. preserve complete provenance and audit information;
12. stop before Canvas writeback.

---

## Version 1 Completion Criteria

Version 1 may be considered operational when it additionally provides:

- proposed Canvas change preview;
- explicit instructor confirmation;
- protected Canvas writeback;
- duplicate-write prevention;
- write audit log;
- stable installation process;
- user documentation;
- recovery documentation;
- supported interface;
- tested security and retention behavior.

---

## Architectural Decisions Already Made

The following decisions are currently accepted.

### AD-001 — Preserve Prototype Until Parity

The numbered Modules 1–8 remain until the refactored path reproduces them.

### AD-002 — Alpha Stops Before Canvas Writes

The end-user alpha ends with approved-grade JSON.

### AD-003 — Instructor Approval Is Separate

Model suggestion, report creation, instructor approval, and Canvas posting are
separate states.

### AD-004 — CLI Before GUI

The internal workflow and input contracts must stabilize before GUI design.

### AD-005 — Sequential Batch Processing First

The first batch workflow processes submissions sequentially.

### AD-006 — Deterministic Rubric Format

Canonical rubric data is created and validated deterministically.

### AD-007 — Provider-Neutral Core

OpenAI-specific behavior remains behind an adapter.

### AD-008 — Local Revalidation

Saved provider responses can be revalidated without another paid request.

### AD-009 — Local Score Calculation

Totals are calculated locally from item-level results and validated rules.

### AD-010 — Identity Restored After Provider Activity

Student identity is restored only in the private reporting stage.

### AD-011 — Current Repository Continues Through Alpha

The alpha refactor remains in the current repository, protected by branch and
tag history.

---

## Open Architectural Decisions

The following decisions are intentionally deferred.

### OD-001 — Domain Model Library

Options include:

- standard dataclasses plus manual validation;
- Pydantic;
- another lightweight validation library.

Selection should consider:

- schema generation;
- migration support;
- dependency weight;
- clarity;
- Windows compatibility.

### OD-002 — CLI Framework

Options include:

- standard `argparse`;
- Typer;
- Click.

The choice should follow actual command complexity.

### OD-003 — Final User Interface

Options include:

- PySide/PyQt desktop;
- local web application;
- browser frontend plus Python backend.

No decision is required before internal workflow stabilization.

### OD-004 — Hardened Execution Environment

Options may include:

- restricted local process;
- container;
- VM;
- remote sandbox.

The prototype timeout is not a final security boundary.

### OD-005 — Local Model Provider

A local provider should be evaluated against saved packages and known expected
results after the shared provider interface stabilizes.

### OD-006 — Retention and Cleanup Policy

The project must eventually define:

- private artifact lifetime;
- workspace cleanup;
- audit retention;
- approved-grade retention;
- provider artifact retention.

### OD-007 — Cross-Language Support

The first generalized alpha may remain C++ focused.

Support for Python, Java, Swift, or other languages should use language-specific
toolchain and execution profiles rather than conditionals scattered throughout
the codebase.

---

## Architecture Review Triggers

This document should be reviewed when:

- a trust boundary changes;
- a new provider is added;
- Canvas writeback is introduced;
- a GUI is selected;
- a new language is supported;
- execution isolation changes;
- artifact schemas change;
- the workspace model changes;
- approval semantics change;
- the project becomes publicly released;
- a major phase in `ROADMAP.md` is completed.

---

## Final Architectural Rule

The system should remain understandable from its artifacts and state transitions.

A future maintainer should be able to answer:

- what data entered the system;
- what was sent to a provider;
- what code was compiled or executed;
- what evidence was available;
- how the advisory score was calculated;
- what the instructor changed;
- whether approval occurred;
- whether Canvas was contacted;
- whether Canvas was modified.

If the architecture cannot answer those questions, it is not finished.
