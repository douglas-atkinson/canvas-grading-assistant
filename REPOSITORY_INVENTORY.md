# REPOSITORY_INVENTORY.md

## Purpose

This is the one-time, read-only architecture and code inventory called for by
`ROADMAP.md` Phase 3 ("Read-Only Repository Inventory"). It maps every
tracked file in the Modules 1-8 prototype to its current responsibility,
inputs/outputs, side effects, dependencies, privacy classification, and a
proposed destination in the target architecture described in
`ARCHITECTURE.md`.

**No production code was moved, renamed, or rewritten to produce this
document.** All findings below come from reading the tracked files as they
exist on `alpha-refactor` at commit `3a6091c`.

## How to Read This Document

- **Part 1** inventories every tracked file, grouped the way `ARCHITECTURE.md`
  groups the prototype (pre-Module exploration, then Modules 1-8, then
  configuration/assets, then documentation).
- **Part 2** lists cross-cutting findings required by `ROADMAP.md`: duplicated
  logic, hidden coupling, inconsistent artifact schemas, public-release
  risks, a known functional bug, and missing test coverage.
- **Part 3** is a lightweight preview of the artifact contracts that Phase 4
  will formalize.
- **Part 4** proposes the smallest safe extraction sequence.
- **Part 5** lists open questions for Doug/Sam before Phase 5 begins.

Per-file entries use a consistent set of fields drawn from the columns
`ROADMAP.md` requires: responsibility, inputs, outputs/artifacts produced,
side effects (Canvas contact / provider contact / student-code execution),
privacy classification, dependencies, proposed destination, tests
present/needed, and notes/risks.

---

# Part 1 — File-by-File Inventory

## Pre-Module Exploration Scripts

These three files predate the numbered Modules 1-8 pipeline. They are not
consumed by later modules but contain reusable Canvas read logic.

### `canvas_template.py` (97 lines)

- **Responsibility:** Minimal connect-and-inspect example from the original
  course template. Connects to Canvas, fetches a course, lists modules.
- **Inputs:** `.env` (`CANVAS_URL`, `CANVAS_TOKEN`, `COURSE_ID`).
- **Outputs:** Console output only. No file artifacts.
- **Side effects:** Canvas GET (course, modules). Contains a **commented-out**
  `course.update(course={'name': 'New Course Name'})` call demonstrating a
  Canvas write — disabled, but present as example code outside any future
  write-isolation module (see Part 2, Public-Release / Hygiene Risks).
- **Privacy classification:** Course-level metadata only; no student PII
  requested.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/CourseService` (read) — superseded in
  practice by `canvas_course_json_exporter.py` and Module 1/2.
- **Tests present/needed:** None present. Needs a mocked-Canvas unit test if
  retained past the skeleton phase; otherwise safe to retire once
  `canvas/CourseService` exists.
- **Notes/risks:** Low risk; template-era demo file.

### `canvas_course_json_exporter.py` (444 lines)

- **Responsibility:** Read-only full-course export (modules, pages,
  assignments, discussions, classic/new quizzes, file metadata, tabs,
  settings) to `canvas_exports/<name>_<id>_<timestamp>.json`.
- **Inputs:** `.env` Canvas config.
- **Outputs:** One JSON export file under `canvas_exports/` (gitignored).
- **Side effects:** Canvas GET only, across many endpoints. Explicitly
  excludes student submissions, grades, enrollments, and discussion replies
  (documented in its own docstring and `export_information.notes`).
- **Privacy classification:** Course/content metadata; deliberately excludes
  student data.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/CourseService` — its `make_json_safe`,
  `export_section` (per-section failure isolation so one bad endpoint
  doesn't abort the whole export), and `sanitize_filename` helpers are good
  reusable primitives.
- **Tests present/needed:** None present. Needs unit tests for
  `make_json_safe`, `sanitize_filename`, and `export_section`'s isolation
  behavior (pure functions, easy to test without Canvas).
- **Notes/risks:** Best-written "Canvas read" reference in the repo — good
  template for `canvas/CourseService`'s error-isolation pattern.

### `list_programming_assignments_complete.py` (212 lines)

- **Responsibility:** Locate the "Programming Assignment" assignment group
  and list its assignments. An intermediate, more defensive rewrite of
  Module 1 (function-based, `argparse`-free but with helper functions and a
  `find_assignment_group` case-insensitive matcher).
- **Inputs:** `.env` Canvas config.
- **Outputs:** Console output only.
- **Side effects:** Canvas GET (course, assignment groups, assignments).
- **Privacy classification:** Course/assignment metadata only.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/AssignmentService` (group lookup logic).
- **Tests present/needed:** None. Needs a unit test for
  `find_assignment_group`.
- **Notes/risks:** **Contains a real bug** — see Part 2, "Known Functional
  Bug." Not part of the numbered pipeline, so it does not block the alpha,
  but should not be copied into a shared service as-is.

---

## Module 1 — Canvas Course Exploration / Assignment Listing

### `module_1_list_programming_assignments.py` (131 lines)

- **Responsibility:** Script-level (no `main()`) listing of assignments in
  the "Programming Assignment" group.
- **Inputs:** `.env` Canvas config.
- **Outputs:** Console output only.
- **Side effects:** Canvas GET (course, assignment groups, assignments).
- **Privacy classification:** Course/assignment metadata only.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/AssignmentService`.
- **Tests present/needed:** None. Low priority for dedicated tests since its
  logic is superseded by `list_programming_assignments_complete.py`'s
  function-based version (which itself needs to be fixed before reuse).
- **Notes/risks:** Script-level top-level code (not gated behind
  `if __name__ == "__main__":`) — fine for an exploration script, unsuitable
  for a reusable service module as-is.

---

## Module 2 — Assignment Inspection

### `module_2_inspect_assignment.py` (364 lines)

- **Responsibility:** Given an assignment ID, fetch assignment-definition
  data (deliberately excluding `submission`, `observed_users`,
  `score_statistics`), print a structured summary and full attribute
  inventory, and save JSON to `output/assignment_<id>.json`.
- **Inputs:** CLI arg `assignment_id`; `.env` Canvas config.
- **Outputs:** `output/assignment_<id>.json` (gitignored).
- **Side effects:** Canvas GET (course, one assignment with `include=`
  overrides/visibility/can_edit/peer_review).
- **Privacy classification:** Assignment-definition metadata; the module
  explicitly avoids requesting submission or grade data and records that
  fact in the output JSON (`student_submissions_requested: false`).
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/AssignmentService.inspect()`.
- **Tests present/needed:** None. `make_json_safe`/`get_public_attributes`
  are pure and testable.
- **Notes/risks:** Reimplements `make_json_safe` independently (4th copy in
  the repo — see Part 2).

---

## Module 3 — Submission Discovery

### `module_3_list_submissions.py` (399 lines)

- **Responsibility:** List submissions for one assignment and split them
  into a **PRIVATE** manifest (Canvas user IDs, student names, download
  URLs) and an **AI-safe** manifest (anonymous labels only). This is the
  first anonymization boundary in the pipeline.
- **Inputs:** CLI arg `assignment_id`, optional `--show-names`; `.env`.
- **Outputs:** `output/assignment_<id>_private_submissions.json`,
  `output/assignment_<id>_ai_safe_manifest.json`.
- **Side effects:** Canvas GET (`assignment.get_submissions(include=["user"])`).
- **Privacy classification:** Produces both Zone 1 (PRIVATE,
  `send_to_ai: false`) and Zone 3-adjacent (AI-safe metadata,
  `send_to_ai: true`) artifacts from one run — the classification split is
  explicit and self-documenting in each output file.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/SubmissionService` (discovery) +
  `domain` (the anonymous-label assignment scheme, private/AI-safe manifest
  contracts).
- **Tests present/needed:** None. Needs fixture-based tests for the
  private/AI-safe record-splitting logic (pure functions
  `private_attachment_record`/`ai_safe_attachment_record`).
- **Notes/risks:** Superseded in practice by `module_3_list_submissions_v2.py`
  (see below) — Module 4's own docstring example uses a v2-style output
  filename. Kept per the "preserve prototype" rule; not itself broken.

### `module_3_list_submissions_v2.py` (490 lines)

- **Responsibility:** Revised Module 3. Adds `--mode {live,historical}` to
  target active vs. inactive/completed enrollments, reconciles enrollments
  against submissions via bulk + per-student fallback lookups
  (`get_multiple_submissions` then `get_submission` for stragglers), and
  fails fast (`sys.exit(2)`) when any targeted student can't be reconciled.
- **Inputs:** CLI args `assignment_id`, `--mode` (required),
  `--show-names`; `.env`.
- **Outputs:** `output/assignment_<id>_<mode>_private_submissions.json`,
  `output/assignment_<id>_<mode>_ai_safe_manifest.json`.
- **Side effects:** Canvas GET (enrollments, bulk submissions, per-student
  submission fallback).
- **Privacy classification:** Same PRIVATE/AI-safe split as Module 3, plus an
  `unresolved_canvas_user_ids` field in the private manifest for auditability.
- **Dependencies:** `canvasapi`, `python-dotenv`.
- **Proposed destination:** `canvas/SubmissionService` (this version's
  reconciliation logic — `get_target_enrollments`, `reconcile` — is the
  stronger candidate for the reusable service; it is more defensive than v1).
- **Tests present/needed:** None. `reconcile()` and `states_for_mode()` are
  pure and unit-testable with fixture enrollment/submission objects.
- **Notes/risks:** This is the version Module 4's docstring assumes as input.
  Recommend treating v2 as canonical when extracting `SubmissionService`,
  while keeping v1 available per the "do not delete prototype scripts"
  rule.

---

## Module 4 — Submission Download and Extraction

### `module_4_download_submission.py` (807 lines)

- **Responsibility:** Resolve one anonymous label to a Canvas user ID via the
  private Module 3 manifest, select the latest valid submitted attempt,
  require exactly one ZIP attachment, download it under strict size limits,
  and safely extract it (path-traversal, symlink, compression-ratio, file
  count, and per-file/total size checks) while preserving original
  filenames/paths.
- **Inputs:** CLI args `private_manifest` (path), `anonymous_label`,
  `--overwrite`; `.env` Canvas config (and cross-checks `COURSE_ID` against
  the manifest's course ID).
- **Outputs:**
  `output/assignment_<id>/<label>/original/submission.zip`,
  `output/assignment_<id>/<label>/extracted/...`,
  `output/assignment_<id>/<label>/module_4_private_extraction_manifest.json`,
  `output/assignment_<id>/<label>/local_file_inventory.txt`.
- **Side effects:** Canvas GET (submission + history, optional file-URL
  resolution) plus one authenticated HTTPS GET (streamed, size-capped) to
  download the ZIP. No writes.
- **Privacy classification:** PRIVATE (Zone 1/2) — extraction manifest
  contains `canvas_user_id`, original ZIP filename;
  `"pii_sanitized": false`, `"approved_for_ai": false` recorded explicitly.
  Original submission is preserved untouched (Zone 2, not modified in
  place).
- **Dependencies:** `canvasapi`, `python-dotenv`, `requests`, stdlib
  `zipfile`/`hashlib`/`shutil`/`stat`.
- **Proposed destination:** `submissions/` — this is the strongest, most
  defensively written module in the repo and should become the archetype
  for `submissions.download` and `submissions.extract`. Specific reusable
  functions: `select_latest_valid_attempt`, `select_single_zip_attachment`,
  `safe_member_path`, `is_zip_symlink`, `inspect_archive` (validates before
  any extraction happens), `extract_archive`, `sha256_file`.
- **Tests present/needed:** None present. This is the **highest-priority**
  file for regression tests given it implements every archive-safety
  control `CLAUDE.md` calls non-negotiable (path traversal, absolute paths,
  file count, extracted size, compression bombs, oversized files, symlinks).
  Needs fixture ZIPs for: path traversal, absolute path, zip bomb, symlink
  entry, oversized single file, too many entries, multiple ZIP attachments,
  no ZIP attachment, encrypted entry.
- **Notes/risks:** `is_zip_symlink` reads Unix mode bits from
  `ZipInfo.external_attr`; ZIPs created on Windows generally don't set this,
  so the symlink check is a Unix-authoring-tool safeguard, not a complete
  cross-platform one — worth a comment/test when extracted, not a blocker.
  Compile/extraction ordering is correct: `inspect_archive` fully validates
  every member before `extract_archive` writes anything.

---

## Module 5 / 5.1 — AI-Candidate Preparation

### `module_5_prepare_ai_copy.py` (651 lines) and `module_5_1_prepare_ai_copy.py` (682 lines)

These two files are ~95% identical (same comment-stripping state machine,
same identifier-derivation, same report shapes). **5.1 supersedes 5. Its only
functional differences:**

| | Module 5 | Module 5.1 |
|---|---|---|
| `path_warnings()` | Flags the ZIP stem as PII in paths | Excludes ZIP stem (avoids false positives like `CarProgram.zip` → `CarProgram/`); adds punctuation/spacing-insensitive matching (`normalize_for_path_comparison`) so `Melissa_Bott`/`MelissaBott` are still caught |
| Report metadata | No `module` block | Adds `"module": {"number": "5.1", ...}` |

- **Responsibility (both):** Copy extracted source into `ai_candidate/`,
  strip C/C++ comments with a hand-written state machine that preserves
  strings/char literals/raw strings and line counts, redact exact known
  identifiers (student name in 3 forms, Canvas user ID, long ZIP stems),
  and emit a private sanitization report + AI-safe package manifest +
  human-reviewable outbound preview.
- **Inputs:** CLI args `module_4_manifest`, `module_3_private_manifest`,
  `--overwrite`.
- **Outputs:**
  `<submission_root>/ai_candidate/...` (sanitized source tree),
  `module_5_private_sanitization_report.json`,
  `module_5_ai_package_manifest.json`,
  `module_5_outbound_preview.txt`.
- **Side effects:** None (no Canvas, no AI, no network). Local FS only.
- **Privacy classification:** Reads two PRIVATE inputs, produces one PRIVATE
  output (sanitization report — contains student name) and one AI-safe
  output (package manifest — explicitly `contains_student_name: false`
  etc.). `approved_for_ai` is always `false`; human review is always
  required (`sys.exit(2)` when any known identifier remains after
  redaction).
- **Dependencies:** stdlib only (`re`, `dataclasses`, `pathlib`, `shutil`).
- **Proposed destination:** `privacy/` — `strip_cpp_comments`,
  `derive_identifiers`, `redact_identifiers`, `path_warnings`,
  `find_raw_string_end` are pure, well-isolated, and the best candidates in
  the repo for early unit-test coverage since they need zero fixtures
  beyond strings.
- **Tests present/needed:** None present despite being pure logic — very low
  cost to add. Needs tests for: line-comment/block-comment stripping,
  raw-string handling (`R"delim(...)delim"`), unterminated
  comment/string/char detection, identifier redaction (case-insensitive,
  multiple name forms), and the 5.1 path-warning false-positive fix
  specifically (a regression test locking in the 5→5.1 behavior change).
- **Notes/risks:** Because 5 and 5.1 are near-duplicate files, **the
  extraction must preserve 5.1's behavior**, not 5's, as canonical — 5
  remains only as a preserved prototype step per `CLAUDE.md`.

---

## Module 6 — Grading Package Construction

### `module_6_build_grading_package.py` (1,385 lines — largest file in the repo)

- **Responsibility:** The pipeline's most complex module. Validates the
  Module 5.1 AI-safe manifest and rubric, assembles a provider-neutral
  grading package (assignment spec, rubric, instructor notes, starter/
  reference/supporting files, numbered student source), generates a strict
  JSON Schema for the structured response from the rubric's own IDs,
  attempts local compilation (auto-detecting `g++`/`clang++`/`cl`),
  optionally executes the compiled program under an explicit flag and hard
  timeout, compares output against a validated reference, and writes the
  complete `grading_request/` package atomically (via a staging directory
  swapped into place) while preserving any existing `model_runs/` from a
  prior Module 7 run.
- **Inputs:** CLI args `grading_assets` (dir), `submission_directory`, plus
  `--overwrite`, `--allow-warnings`, `--compiler`, `--skip-compile`,
  `--require-compiler`, `--run-student-code`, `--run-timeout`,
  `--max-captured-output`.
- **Outputs (all under `<submission_root>/grading_request/`):**
  `grading_package.json`, `ai_safe_student_material.json`,
  `response_schema.json`, `local_compile_run_evidence.json`,
  `package_validation_report.json`, `grading_request_manifest.json`,
  `grading_request_preview.txt`.
- **Side effects:** No Canvas, no provider contact (both explicitly recorded
  `false` in every output artifact). **Local compilation** always attempted
  unless `--skip-compile`. **Local execution** of the compiled
  student program only when `--run-student-code` is explicitly passed, with
  a configurable timeout (default 10s) — compile itself has a
  non-configurable 120s timeout. Execution happens via `subprocess.run` with
  no additional sandboxing beyond the timeout, matching the project's
  documented "not a hardened sandbox" stance.
- **Privacy classification:** Reads AI-safe input (Module 5.1's
  `ai_candidate/`), produces exclusively AI-safe output — every output
  artifact declares `contains_canvas_user_id/student_name/...: false`.
  `objective_evidence.submission_artifact` deliberately whitelists only
  harmless facts (archive type, entry count) from Module 4's private
  manifest rather than including it wholesale.
- **Dependencies:** stdlib only (`subprocess`, `tempfile`, `hashlib`, `re`,
  `shutil`).
- **Proposed destination:** Splits across three target areas:
  - `execution/` — `locate_compiler`, `compiler_kind`, `compiler_version`,
    `build_compile_command`, `local_compile_run_evidence`,
    `copy_build_inputs`, `normalized_output`, `trim_output`, `safe_command`.
  - `grading/` — `validate_rubric`, `response_schema`, `artifact_evidence`,
    `reference_validation`, `configured_records`/`directory_records`/
    `text_record`/`inside` (asset-path containment check).
  - `storage/` — the staging-directory atomic-write pattern (build in
    `.grading_request_building/`, then `Path.replace()`) is a good template
    for `storage`'s resumability guarantees generally.
- **Tests present/needed:** None present. High priority given the amount of
  logic. Needs: rubric validation (totals mismatch, duplicate IDs, empty
  criteria), response-schema generation from a known rubric, compiler
  auto-detection with a stubbed `shutil.which`, compile
  success/failure/timeout/no-compiler paths, execution
  success/nonzero-exit/timeout paths, output-comparison normalization, and
  the `--overwrite`-preserves-`model_runs/` behavior (already covered
  narratively by `SELF_TEST_MODULE_6_7.txt` but not by an automated test).
- **Notes/risks:** `validate_rubric()` here and `rubric_contract()` in
  Module 8 are **two independent implementations of the same rubric
  validation** (see Part 2, duplicated logic). `inside()`'s path-containment
  check for configured asset paths is a good small pattern worth lifting
  into a shared path-safety helper alongside Module 4's `safe_member_path`.

---

## Module 7 — Model Evaluation and Validation

Module 7 is the only part of the prototype already organized as a proper
Python package (`module_7/`), and it is the closest thing in the repo to the
target `grading/` + `grading/providers/` architecture already described in
`ARCHITECTURE.md`. Two CLI entry points sit outside the package.

### `module_7_evaluate.py` (379 lines) — entry point

- **Responsibility:** Orchestrates one Module 7 run: load package + student
  material, run the final privacy gate, load the profile and prompt, build
  the request, dry-run by default, send exactly one request with `--send`,
  save raw response + validated result + run metadata.
- **Inputs:** CLI args `grading_package`, `student_material`,
  `--response-schema`, `--profiles`, `--profile`, `--prompt`,
  `--output-dir`, `--send`, `--skip-availability-check`.
- **Outputs:** `<output_dir>/<timestamp>_<provider>_<model>/`:
  `request_payload.json`, `request_manifest.json`, and (only with `--send`)
  `raw_provider_response.json`, `grading_result.json`,
  `validation_report.json`, `run_metadata.json`.
- **Side effects:** Provider contact **only** with `--send` (else dry run).
  `provider.check_availability()` performs a metadata-only preflight
  request unless `--skip-availability-check`. No Canvas contact (explicitly
  recorded `false` in every output).
- **Privacy classification:** Input must already be AI-safe;
  `assert_ai_safe()` is a hard last-mile gate before any request is built.
- **Dependencies:** `module_7.*` package, `dotenv`.
- **Proposed destination:** `workflows/` (the orchestration itself) calling
  into `grading/` and `grading/providers/` services that already
  substantially exist in `module_7/`.
- **Tests present/needed:** None. Needs a dry-run integration test (no
  network) verifying `request_payload.json`/`request_manifest.json` shape,
  and a test that a provider is never constructed when `--send` is absent.
- **Notes/risks:** None significant — this is a clean orchestration script.

### `module_7_revalidate.py` (231 lines) — entry point

- **Responsibility:** Locally re-run schema + domain validation against a
  saved `grading_result.json` without any provider or Canvas contact —
  supports `AD-008` (local revalidation). Recovers the exact sent
  grading package/student material either from `request_manifest.json`'s
  file paths or, if those are gone, by regex-extracting them back out of
  `request_payload.json`'s `user_prompt` text.
- **Inputs:** CLI arg `run_directory`, `--replace-originals`.
- **Outputs:** `validation_report.revalidated.json` +
  `run_metadata.revalidated.json` (or, with `--replace-originals`, backs up
  and replaces the originals as `*.before_revalidation.json`).
- **Side effects:** None — no Canvas, no provider.
- **Privacy classification:** Operates entirely on already-saved AI-safe/
  validation artifacts.
- **Dependencies:** `module_7.validation`.
- **Proposed destination:** `grading/` (revalidation workflow) —
  functionally this is a `workflows.revalidate_saved_result` operation.
- **Tests present/needed:** None. Needs a test for the regex-based
  `extract_request_material` fallback specifically, since it is a fragile
  string-matching contract (see Part 2, hidden coupling).
- **Notes/risks:** See hidden-coupling finding below — recovering structured
  data by regexing a prompt string is exactly the kind of coupling
  `ARCHITECTURE.md`'s "Deterministic Contracts" principle argues against
  long-term, even though it's a reasonable pragmatic choice for a
  prototype.

### `module_7/config.py` (124 lines)

- **Responsibility:** Load and validate a named `ProviderProfile` from
  `config/model_profiles.json`, enforcing `store == False` and positive
  timeouts/token limits/character limits.
- **Proposed destination:** `config/` — this is nearly ready to move as-is;
  it's the cleanest example of the "Provider Profile" configuration concept
  described in `ARCHITECTURE.md`.
- **Tests present/needed:** None. Very cheap to test (pure, small, no I/O
  beyond one JSON read) — good first-extraction candidate.
- **Notes/risks:** Hardcodes `store=False` as a validation rule, not just a
  default — correctly enforces `AD-008`/privacy-by-separation at the config
  layer rather than trusting each provider adapter.

### `module_7/models.py` (34 lines)

- **Responsibility:** `ModelRequest` and `ProviderResponse` frozen/plain
  dataclasses — the shared provider-neutral request/response contracts
  `ARCHITECTURE.md` already names (`GradingRequest`/`ProviderResponse`).
- **Proposed destination:** `domain/` (or `grading/` if kept adjacent to the
  provider abstraction) — this **is** the `GradingRequest`/`ProviderResponse`
  contract from `ARCHITECTURE.md`, just named `ModelRequest`.
- **Tests present/needed:** None; trivial dataclasses, low priority.

### `module_7/payload_loader.py` (117 lines)

- **Responsibility:** Load Module 6 JSON, AI-safe student material (from
  JSON, a text file, or a directory of source files), and resolve the
  response schema (explicit path → embedded → referenced path, in that
  priority order).
- **Proposed destination:** `grading/` or `storage/` (loading concern).
- **Tests present/needed:** None. `load_response_schema`'s 3-way priority
  fallback deserves a direct test.

### `module_7/privacy.py` (94 lines)

- **Responsibility:** Final transmission-safety gate — recursively scans the
  AI-safe student material for forbidden keys (`canvas_user_id`,
  `student_name`, `download_url`, etc.) and for any explicit
  `send_to_ai: false`/`contains_*: true` flag, and raises before a request
  can be sent if anything is found.
- **Proposed destination:** `privacy/` — this is the last-mile version of
  the same concept `require_private`/`validate_ai_manifest` implement
  earlier in the pipeline (see Part 2 duplication finding), and arguably
  the most important one to preserve exactly since it's the last checkpoint
  before data leaves the machine.
- **Tests present/needed:** None. **High priority** — this is a safety-net
  function; needs tests proving it catches every forbidden key and every
  explicit-`false`/`true` privacy flag, including nested inside lists.

### `module_7/prompt_builder.py` (94 lines)

- **Responsibility:** Build the canonical `ModelRequest` — locates the
  anonymous label recursively, serializes package+material as compact
  sorted JSON, assembles the user prompt with `GRADING_PACKAGE_JSON`/
  `AI_SAFE_STUDENT_MATERIAL_JSON` section markers (the same markers
  `module_7_revalidate.py` and Module 8 later regex out of the saved
  prompt — see hidden coupling), and stamps `PROMPT_VERSION =
  "module7-grading-v2"`.
- **Proposed destination:** `grading/` (prompt construction, explicitly
  isolated from provider-specific code per `ARCHITECTURE.md`).
- **Tests present/needed:** None. Needs a test that
  `find_first_anonymous_label` searches nested dicts/lists correctly and
  that the emitted markers match what the regex-recovery consumers expect
  (a coupling test, effectively).

### `module_7/providers/base.py` (23 lines), `factory.py` (23 lines), `openai_provider.py` (130 lines)

- **Responsibility:** `ModelProvider` ABC (`describe`, `check_availability`,
  `evaluate`); `create_provider()` factory keyed on `profile.provider`
  (currently only `"openai"` registered); `OpenAIProvider` implementing the
  ABC against the OpenAI Responses API with `store: False` and strict
  JSON-schema structured output.
- **Side effects (openai_provider.py only):** Live network calls to OpenAI
  when invoked — `check_availability()` (metadata only) and `evaluate()`
  (one inference call with `max_output_tokens`/`reasoning.effort` from the
  profile).
- **Proposed destination:** `grading/providers/` — **already matches the
  target package name exactly.** This is close to a direct move once a
  `workflows`/`grading` split exists above it.
- **Tests present/needed:** None. `openai_provider.py` needs a test with the
  OpenAI client mocked/faked (never a live call in default tests, per
  `CLAUDE.md`); `factory.py` needs a test for the "unsupported provider"
  error path.
- **Notes/risks:** `factory.create_provider` already documents the intended
  extension point ("Future local adapters should be registered here...") —
  good alignment with `AD-007`/provider-neutral core.

### `module_7/validation.py` (602 lines)

- **Responsibility:** The pipeline's most rigorous validator. Parses JSON,
  validates against the strict Draft 2020-12 schema, checks the anonymous
  label matches, then domain-validates: every rubric item ID/criterion/
  maximum matches the actual rubric, `scored` items have in-range numeric
  points, `requires_local_evidence` items have `null` points and
  `manual_review_needed: true`, global rule IDs are complete/unique, and —
  most notably — every `evidence[].file` reference is checked against
  actual student source line counts, package (starter/reference/
  supporting) file line counts, known structured-document names, or
  resolvable `objective_evidence.*` dotted paths (rejecting hallucinated
  evidence paths).
- **Proposed destination:** `grading/` — this module is close to
  `ARCHITECTURE.md`'s "local result validation" and "local score
  reconciliation" responsibilities and is well-factored already
  (`validate_domain_rules`, `validate_evidence_entry`,
  `rubric_maps`/`student_file_lines`/`package_file_lines` are all pure
  helper functions).
- **Tests present/needed:** None present despite being the single most
  safety-critical validation function in the repo (it's what stands between
  a model response and `requires_local_evidence` being silently converted
  into an invented deduction). **Highest testing priority in the repo.**
  Needs fixtures for: valid response, unknown rubric item, duplicate item,
  wrong criterion/maximum, scored-without-points, unverified-item-with-
  numeric-score, missing/unknown global rules, hallucinated evidence file,
  invalid evidence line range, and the `objective_evidence.*` dotted-path
  resolution (both hit and miss).
- **Notes/risks:** This file already embodies README_VALIDATOR_PATCH.md's
  fix (the file/structured-document distinction) — the patch has been fully
  applied to the tracked file, so `README_VALIDATOR_PATCH.md` is historical
  documentation of a change already merged, not a pending patch.

---

## Module 8 — One-Student Instructor Report

### `module_8_create_grading_report.py` (702 lines)

- **Responsibility:** Consume one validated Module 7 run (preferring
  `*.revalidated.json` over the originals), locally recompute rubric
  totals/deductions/caps from the authoritative rubric (never trusting the
  model's arithmetic), restore student identity from a private manifest,
  and emit a canonical JSON report + readable Markdown + validation summary
  + run manifest, always with `approval.status = "NOT_APPROVED"`.
- **Inputs:** CLI arg `model_run_directory`, `--private-manifest`,
  `--output-directory`, `--overwrite`, `--allow-anonymous-report`.
- **Outputs:** `<run_dir>/module_8_report/`:
  `one_student_grading_report.json` (canonical),
  `one_student_grading_report.md` (rendering),
  `report_validation.json`, `module_8_report_manifest.json`.
- **Side effects:** None — no Canvas, no provider (explicitly recorded
  `false` throughout). Refuses to run at all if the Module 7 validation
  isn't `valid: true` (`require_valid`).
- **Privacy classification:** Produces the pipeline's first
  identity-restored artifact (Zone 5) — explicitly PRIVATE,
  `send_to_ai: false`. Identity restoration requires the private manifest
  to itself be marked `send_to_ai: false`
  (`restore_identity`); `--allow-anonymous-report` exists as a deliberate,
  non-default escape hatch that is loudly flagged in the report's own
  `warnings`.
- **Dependencies:** stdlib only (`hashlib`, `re`, `shutil`).
- **Proposed destination:** Splits across two target areas:
  - `grading/` — `rubric_contract`, `normalize_items`, `build_criteria`,
    `normalize_rules`, `score_summary` (this **is** the "Score
    Architecture" calculation pipeline `ARCHITECTURE.md` describes).
  - `reporting/` — `restore_identity`, `build_report`, `render_markdown`,
    `validation_summary`, `determine_status`.
- **Tests present/needed:** None present. **High priority** — this is the
  module that turns advisory model output into the artifact an instructor
  actually reads, and it's also the natural home of the golden end-to-end
  regression fixture `CLAUDE.md`/`ROADMAP.md` call for (the proven
  20-item/200-of-200/`NOT_APPROVED` run). Needs tests for: score
  calculation with a complete run, an incomplete run (unresolved items →
  `null` total), deductions, score caps interacting with deductions,
  identity-restoration failure modes (no match, multiple matches, mismatched
  attempt), and `--allow-anonymous-report`'s explicit-opt-in behavior.
- **Notes/risks:** `extract_request_material()` regex-recovers the grading
  package/student material from `request_payload.json`'s prompt text — the
  **same fragile string-matching pattern** as
  `module_7_revalidate.py` (see Part 2). `rubric_contract()` duplicates
  Module 6's `validate_rubric()` (see Part 2) with slightly different
  error messages and return shape.

---

## Configuration and Data Assets

### `config/model_profiles.json` / `config/model_profiles.example.json`

- **Responsibility:** Named `ProviderProfile` definitions consumed by
  `module_7/config.py`.
- **Privacy classification:** No secrets present — `api_key_env` names an
  environment variable, it does not embed a key. Both files are tracked and
  identical in content, which is fine (no live secret), but worth noting
  for Phase 2's public-release audit: if a future contributor ever pastes a
  literal key into `model_profiles.json` instead of `.env`, nothing in
  `.gitignore` would catch it before a commit.
- **Proposed destination:** `config/`.
- **Notes/risks:** Model name `gpt-5.2` (and `gpt-5.6` in a self-test log) —
  consistent with this project's dated context, not a risk.

### `grading_assets/cars_engines_steering/*`

- **Responsibility:** The one existing assignment package
  (`assignment_spec.md`, `rubric.json` — 200 points / 6 criteria / 20
  items / 5 global rules, `instructor_notes.md`, `package_config.json`,
  `instructor_reference/*.{h,cpp}`, `starter_files/`,
  `supporting_files/car_data.csv`, `reference_validation.json`).
- **Privacy classification:** Instructor-authored/synthetic content, not
  student data — safe to keep tracked and public.
- **Proposed destination:** Becomes the first fixture package for Phase 8
  (Assignment Package Generalization) — its `package_config.json` already
  matches the `assignment_package/` shape `ARCHITECTURE.md` proposes almost
  field-for-field.
- **Notes/risks:** This is currently the *only* assignment package, so every
  Cars-specific assumption baked into Module 6/7/8 (e.g., the rubric's
  20-item shape) hasn't yet been stress-tested against a second package —
  flagged again in Part 2 as a public-release/generalization risk to track,
  not fix now.

### `schemas/grading_response_schema.example.json`

- **Responsibility:** A frozen example of the schema Module 6 generates at
  runtime from `rubric.json` (20 items, 5 rules, matching enums).
- **Notes/risks:** This is a **generated-artifact snapshot committed as
  source** — if `rubric.json` changes, this example will silently drift out
  of sync with what Module 6 actually produces. Low risk today (nothing
  reads it as an input; Module 7 defaults to `--response-schema` from CLI
  or the embedded/referenced schema in the grading package, not this file),
  but worth a comment or regeneration check once `grading/` centralizes
  schema generation.

### `prompts/module_7_grading_prompt_v1.txt` / `module_7_grading_prompt_v2.txt`

- **Responsibility:** Version-controlled system prompts. v2 (current
  default, `PROMPT_VERSION = "module7-grading-v2"`) adds the
  `requires_local_evidence` semantics, explicit "missing evidence is not
  evidence of failure," sanitization-whitespace/starter-code protections,
  and stricter evidence-citation requirements that v1 lacks.
- **Proposed destination:** `grading/prompts/` (or similar) — already
  correctly version-controlled and referenced by explicit version string in
  every run's metadata, which is good practice worth preserving exactly.

### `requirements.txt` / `requirements-module7.txt`

- **Responsibility:** Pinned dependencies. `requirements.txt` covers the
  base Canvas/exploration stack; `requirements-module7.txt` adds `openai`,
  `python-dotenv`, `jsonschema` as a lighter-weight overlay.
- **Notes/risks:** `requirements.txt` is saved as **UTF-16** text (visible as
  space-separated characters when read as UTF-8) — not a security issue,
  but likely to cause friction for `pip install -r requirements.txt` on
  some platforms/encodings and is worth normalizing to UTF-8 during the
  Phase 6 skeleton work (flagged, not fixed, per the read-only-audit rule).

### `.env.example`, `.devcontainer/devcontainer.json`

- **Responsibility:** Local-dev bootstrapping. `.env.example` documents the
  three required Canvas variables (no OpenAI key placeholder — worth adding
  since Module 7 needs `OPENAI_API_KEY` too). `devcontainer.json` pins
  Python 3.11 and runs `pip install -r requirements.txt` on create.
- **Notes/risks:** `.env.example` doesn't mention `OPENAI_API_KEY` even
  though `module_7/providers/openai_provider.py` requires it — a
  documentation gap, not a security issue (still no secret committed).

---

## Documentation and Self-Test Artifacts

`README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `ROADMAP.md` are already in
place and current (read as part of session startup); not re-audited here.

- **`CHANGELOG_MODULE_6_7.md`, `MODULE_8_DESIGN.md`, `README_MODULE_6.md`,
  `README_MODULE_7.md`, `README_MODULE_8.md`, `README_VALIDATOR_PATCH.md`:**
  Accurate, per-module design/changelog notes. All describe behavior that
  matches what's in the corresponding tracked source today (verified above,
  file by file) — these read as historical/design documentation rather than
  aspirational, which is exactly what `CLAUDE.md`'s documentation rules ask
  for.
- **`TROUBLESHOOTING.md`:** Generic Canvas/Codespaces setup troubleshooting,
  inherited from the course template. Accurate and harmless; low priority.
- **`SELF_TEST_MODULE_6_7.txt`, `SELF_TEST_MODULE_8.txt`:** Narrative
  pass/fail summaries (not actual `pytest`/CI output — see Part 2, missing
  test coverage).
- **`SELF_TEST_RESULT.txt`, `SELF_TEST_VALIDATOR_PATCH.txt`:** Same
  narrative format, but **both contain leaked, unrelated debug output** —
  see Part 2, Public-Release Risks. This should be cleaned up before the
  Phase 2 public-release audit, independent of this Phase 3 inventory.

---

# Part 2 — Cross-Cutting Findings

## Duplicated Logic

| Pattern | Locations | Recommended shared home |
|---|---|---|
| Canvas config load + validate (`CANVAS_URL`/`CANVAS_TOKEN`/`COURSE_ID`) | `canvas_template.py`, `canvas_course_json_exporter.py`, `list_programming_assignments_complete.py`, `module_1`, `module_2`, `module_3`, `module_3_v2`, `module_4` — **8 independent reimplementations**, each with slightly different error text/validation order | `config/` (Canvas connection settings) |
| CanvasAPI object → JSON-safe dict (`make_json_safe`/`json_safe`) | `canvas_course_json_exporter.py`, `module_2`, `module_3`, `module_3_v2` — 4 copies | `canvas/` shared serialization helper |
| Generic `load_json`(path)→dict, validate-is-object | `module_4`, `module_5`/`5.1`, `module_6`, `module_7/payload_loader.py`, `module_7_revalidate.py`, `module_8` — 6+ copies | `storage/` |
| Generic `write_json`(path, value) | `module_6`, `module_7_evaluate.py`, `module_7_revalidate.py`, `module_8` — 4 copies | `storage/` |
| SHA-256 hashing (file or text) | `module_4.sha256_file`, `module_6.digest`, `module_7_evaluate.sha256_text`, `module_8.sha256` — 4 independent implementations | `storage/` |
| "Is this manifest explicitly private?" (`send_to_ai is False`) check | `module_4` (inline), `module_5`/`5.1.require_private`, `module_6.validate_ai_manifest`, `module_7/privacy.py.assert_ai_safe` (key-scanning approach), `module_8.restore_identity` (inline) — 5 different shapes of the same idea | `privacy/` — this is exactly the `PrivacyClassification`/`ArtifactMetadata` model `ROADMAP.md` Phase 5 suggests as a first candidate |
| Find-one-record-by-`anonymous_label` (error if 0 or >1 matches) | `module_4.find_private_submission`, `module_5`/`5.1.find_submission` | `domain`/`submissions` |
| **Rubric structural validation** (criteria/items sum to declared maxima, unique IDs) | `module_6.validate_rubric()` and `module_8.rubric_contract()` — **two full independent reimplementations** of the same rubric contract, with different error messages and return shapes | `domain.Rubric`/`RubricCriterion`/`RubricItem` — this is the single clearest, highest-value candidate for the "first shared domain model" `ROADMAP.md` Phase 5 asks for |
| C/C++ comment-stripping + identifier redaction | `module_5_prepare_ai_copy.py` and `module_5_1_prepare_ai_copy.py` — near-total file duplication; only `path_warnings()` and report metadata differ (5.1 is canonical) | `privacy/` |

## Hidden Coupling

- **Prompt-text regex recovery.** Both `module_7_revalidate.py`
  (`extract_request_material`) and `module_8_create_grading_report.py`
  (`extract_request_material` — same name, separately implemented) recover
  the exact grading package and student material by regexing
  `request_payload.json`'s `user_prompt` string for the literal markers
  `GRADING_PACKAGE_JSON\n...\n\nAI_SAFE_STUDENT_MATERIAL_JSON\n...`
  that `module_7/prompt_builder.py` writes. This works today only because
  three independently-maintained files agree on an undocumented string
  format. Any prompt-builder change to that format silently breaks
  revalidation and reporting with no compiler/schema to catch it. This is
  the most important "invisible" coupling in the repo — a strong argument
  for `ModelRequest`/saved-run artifacts to carry the structured package
  and student material as first-class fields rather than only as
  interpolated prompt text, once `grading/` is extracted.
- **Filename-convention coupling, not schema coupling.** Module 6 assumes
  `module_5_ai_package_manifest.json` and (for objective evidence)
  `module_4_private_extraction_manifest.json` exist at fixed relative paths
  under the submission root; Module 8 assumes `grading_result.json`,
  `validation_report(.revalidated)?.json`, `run_metadata(.revalidated)?.json`,
  and `request_payload.json` exist under the model-run directory. None of
  this is enforced by a shared "workspace layout" concept yet — it's
  convention encoded independently in each script's `Path` arithmetic.
  This is precisely the gap `ARCHITECTURE.md`'s `storage/` (workspace
  layout, run manifests) is meant to close.
- **`--overwrite` preserving `model_runs/`.** Module 6's `main()` has
  special-cased logic to detect and re-home an existing
  `grading_request/model_runs/` directory across an `--overwrite` rebuild.
  This is important, correct, and currently the *only* thing preventing
  `--overwrite` from silently discarding a paid Module 7 result — but it's
  implemented as a side-effect of Module 6's own file-replacement code
  rather than as an explicit "resume-safe" rule enforced by `storage/`.

## Inconsistent Artifact Schemas

- No consistent envelope. `ARCHITECTURE.md` recommends every artifact carry
  `artifact_type`/`schema_version`/`created_at_utc`/`privacy`. In practice:
  - Modules 1-5 outputs have no `schema_version` field at all.
  - Module 6 uses `SCHEMA_VERSION = "1.1"`.
  - Module 8 uses `SCHEMA_VERSION = "1.0"` — an independent counter, not a
    shared one.
  - Module 7's saved artifacts (`request_payload.json`,
    `run_metadata.json`, etc.) carry no `schema_version` at all.
- `privacy` blocks are shaped differently per file — some use
  `"classification"` + boolean flags (Modules 3-6, 8), Module 7's
  `privacy.py` instead does key-name/flag scanning rather than reading a
  declared classification. Both are defensible, but they are two different
  mechanisms enforcing the same rule.
- Module 3 vs. Module 3 v2 write differently-named output files for the same
  conceptual artifact (`assignment_<id>_private_submissions.json` vs.
  `assignment_<id>_<mode>_private_submissions.json`), which is fine given
  v2's added `--mode`, but is one more reason a shared, versioned artifact
  contract (Phase 4) will pay off quickly.

## Known Functional Bug

- **`list_programming_assignments_complete.py`, line 173** — inside
  `main()`, after `target_group` has already been resolved via
  `find_assignment_group()`, the manual filtering loop reads
  `assignment.assignment_group_id == group.id`, but `group` is never
  assigned anywhere in `main()`'s scope (it only exists inside the separate
  `find_assignment_group()` function). Running this script as written will
  raise `NameError: name 'group' is not defined` as soon as a matching
  assignment group is found. It should read `target_group.id`. This file is
  not part of the numbered Modules 1-8 pipeline (an earlier, superseded
  exploration script), so it does not block the alpha — but it should be
  fixed or explicitly retired rather than reused as source material for
  `canvas/AssignmentService`.

## Public-Release / Hygiene Risks (feeds Phase 2)

- **`SELF_TEST_RESULT.txt`** and **`SELF_TEST_VALIDATOR_PATCH.txt`** contain
  a leaked, unrelated stack trace from what appears to be internal AI-
  tooling ("Spreadsheet runtime warmup failed", paths under
  `/tmp/tmp.yTcnQsZYiA/artifact_tool_v2-2.8.4/...`, `RemoteError:
  hydrateCrdtFromProto requires an empty collaborative document`) mixed into
  what's presented as this project's self-test output. It contains no
  secrets or student data, but it is (a) not actually reproducible/
  verifiable test output, and (b) confusing/unprofessional content that
  should be cleaned or regenerated before the repository goes public.
  Flagging for Phase 2, not fixing here (read-only audit).
- **No automated test suite exists anywhere in the repository** — no
  `tests/` directory, no `pytest`/`unittest` in `requirements*.txt`, no
  CI configuration (`.github/workflows` absent). The "self-test" `.txt`
  files are hand-written narrative summaries of manual runs, not
  machine-verifiable output. This is the single biggest gap relative to
  `CLAUDE.md`'s Testing Requirements section and to `ROADMAP.md`'s Phase
  0-13 exit criteria (nearly every phase's exit criteria says "tests
  pass").
- **`requirements.txt` is UTF-16-encoded** — unusual and likely to cause
  friction on some tools/platforms even though `pip` typically tolerates it.
  Worth normalizing when the `pyproject.toml`/skeleton is introduced
  (Phase 6).
- **A commented-out Canvas write call exists in `canvas_template.py`**
  (`course.update(...)`) outside of any write-isolation boundary. It is
  inert today, but `CLAUDE.md` asks that write-capable code stay isolated
  from read workflows — worth removing or moving into clearly-labeled
  documentation-only material rather than live (if disabled) source, so a
  future contributor can't casually uncomment it in a read-only script.
- **Only one assignment package (`cars_engines_steering`) exists.** Several
  of Module 6/7/8's assumptions (20-item rubric shape reflected in the
  committed example schema, single-language/C++-only compiler logic) have
  never been exercised against a second package. Not a defect today, but a
  generalization risk to track into Phase 8.
- No secrets, tokens, student names, Canvas user IDs, or real submission
  data were found in any tracked file read during this audit. `.env`,
  `.venv`, `output/`, `canvas_exports/`, and `*.zip` are all correctly
  `.gitignore`d. `config/model_profiles.json` contains an env-var *name*,
  not a key value.

## Missing Test Coverage — Priority Order

1. `module_7/validation.py` — domain validation is the last defense against
   hallucinated evidence and invented deductions reaching an instructor.
2. `module_4_download_submission.py` — archive-safety controls
   (`CLAUDE.md` non-negotiables: path traversal, absolute paths, symlinks,
   file count, extracted size, compression ratio, per-file size).
3. `module_6_build_grading_package.py` — rubric validation, compile/execute/
   timeout paths, response-schema generation.
4. `module_8_create_grading_report.py` — score calculation (base points,
   deductions, caps, unresolved-item handling) and identity restoration —
   natural home for the golden 20-item/200-of-200/`NOT_APPROVED` regression
   fixture named in `CLAUDE.md`/`ROADMAP.md`.
5. `module_7/privacy.py` — the final pre-transmission safety gate.
6. `module_5_1_prepare_ai_copy.py` — comment-stripping state machine and
   identifier redaction (pure, cheap to test, currently untested).
7. Everything else (Canvas read modules, config loader, providers) — lower
   risk but still zero coverage today.

---

# Part 3 — Artifact Contract Preview (informs Phase 4)

This is a lightweight preview, not the full Phase 4 deliverable. Every
artifact below already exists in the prototype; Phase 4 should give each one
an explicit schema, required/optional fields, and a version.

| Artifact | Producer | Consumer(s) | Privacy | `send_to_ai` |
|---|---|---|---|---|
| Private submissions manifest | Module 3 / 3v2 | Module 4, 5/5.1, 8 | PRIVATE | `false` |
| AI-safe submissions manifest | Module 3 / 3v2 | (not currently re-read downstream) | AI-safe | `true` |
| Private extraction manifest | Module 4 | Module 5/5.1, Module 6 (`artifact_evidence`) | PRIVATE | `false` |
| Private sanitization report | Module 5/5.1 | (not currently re-read downstream) | PRIVATE | `false` |
| AI-safe package manifest | Module 5/5.1 | Module 6 | AI-safe | `true` |
| Grading package | Module 6 | Module 7 | AI-safe | `true` |
| AI-safe student material | Module 6 | Module 7 | AI-safe | `true` |
| Response schema | Module 6 | Module 7 | AI-safe (structural only) | `true` |
| Local compile/run evidence | Module 6 | Module 7 (embedded in package), Module 8 (indirectly) | AI-safe | `true` |
| Request payload / manifest | Module 7 | Module 7 revalidate, Module 8 (via regex recovery) | AI-safe | n/a (already sent) |
| Raw provider response | Module 7 | (debug only) | AI-safe | n/a |
| Grading result | Module 7 | Module 8 | AI-safe | n/a |
| Validation report | Module 7 / revalidate | Module 8 | AI-safe | n/a |
| Run metadata | Module 7 / revalidate | Module 8 | AI-safe | n/a |
| One-student instructor report (JSON + MD) | Module 8 | Future review workbook (Phase 11) | PRIVATE | `false` |

---

# Part 4 — Proposed Smallest Safe Extraction Sequence

In order, each step independently testable and each leaving the numbered
scripts fully intact and runnable:

1. **`storage`: `load_json`/`write_json`/`sha256_*` helpers.** Zero
   behavior risk (pure I/O helpers duplicated 4-6x already), immediately
   testable, and every later extraction depends on it.
2. **`domain`: `PrivacyClassification` / artifact-privacy check.** Replaces
   the 5 different "is this manifest private/AI-safe" implementations with
   one shared, tested predicate — directly serves `CLAUDE.md`'s privacy
   non-negotiables.
3. **`domain`: `Rubric` / `RubricCriterion` / `RubricItem`.** Replaces
   Module 6's `validate_rubric()` and Module 8's `rubric_contract()` with
   one shared, tested model — this is `ROADMAP.md` Phase 5's own suggested
   first candidate, and the clearest duplication found in this audit.
4. **`config`: `ProviderProfile` loader.** `module_7/config.py` is already
   nearly in final shape; lift it close to as-is.
5. **`grading/providers`: the Module 7 provider package.** `module_7/models.py`,
   `providers/base.py`, `providers/factory.py`, `providers/openai_provider.py`
   already match the target package name and shape; move with tests added
   for the mocked-client path.
6. **`privacy`: comment-stripping + redaction (from 5.1) + the final
   `assert_ai_safe` gate.** Pure functions, currently zero test coverage,
   high safety value.
7. **`submissions`: Module 4's archive-safety functions.** Highest-value
   module to protect with regression tests before any refactor touches it.
8. Only after 1-7 are in place and tested: begin wiring a real
   `workflows.process_one_submission` that calls these services directly
   (Phase 7), replacing script-to-script file handoffs with typed in-memory
   objects while keeping the numbered scripts runnable until parity is
   demonstrated end-to-end against the golden fixture.

---

# Part 5 — Open Questions for Phase 4/5

- Should the shared `Rubric` model be Pydantic or plain dataclasses (`OD-001`
  is still open)? Rubric validation is complex enough (nested criteria/items,
  cross-field sum checks) that schema-generation support may tip the
  decision — worth deciding before Step 3 of the extraction sequence above.
- Should `ModelRequest`/saved run artifacts be changed to carry the grading
  package and student material as structured fields (closing the
  prompt-regex coupling in Part 2) as part of Phase 5, or deferred to
  Phase 7's workflow rewrite? Recommend closing it in Phase 5 alongside the
  `Rubric` model, since it's low-risk (additive field, regex fallback can
  remain for old runs) and removes the repo's most fragile coupling early.
- Module 3 vs. 3v2 and Module 5 vs. 5.1: confirm with Doug/Sam that v2/5.1
  are intended as the sole basis for extracted services (this audit assumes
  so based on Module 4's own docstring example and 5.1's bug-fix-over-5
  relationship), while v1 files remain preserved-but-unused per
  `CLAUDE.md`.
- Timing for cleaning `SELF_TEST_RESULT.txt`/`SELF_TEST_VALIDATOR_PATCH.txt`
  (leaked unrelated debug content) — recommend doing this alongside Phase 2
  (Public-Release Safety Audit) rather than as part of this read-only
  inventory.

---

# Summary

- **Files created:** `REPOSITORY_INVENTORY.md` (this file).
- **Files changed:** None. No production code, configuration, or existing
  documentation was moved, renamed, or edited.
- **Tests run:** None — this was a read-only inventory; no Canvas calls, no
  provider calls, and no student code was executed.
- **Unresolved questions:** See Part 5.
- **Recommended first refactoring step:** Extract the shared `storage`
  JSON/hash helpers (Part 4, Step 1), immediately followed by the
  `PrivacyClassification` predicate (Step 2) and the `Rubric` domain model
  (Step 3) — all three are low-risk, independently testable, and directly
  eliminate the clearest duplication found in this audit.
