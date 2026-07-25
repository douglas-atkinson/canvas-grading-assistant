# OD-001: Domain-Model Library Decision

## Document Purpose

This document resolves `OD-001` - the open architectural decision named in
`ARCHITECTURE.md`'s "Open Architectural Decisions" section and restated as a
required precondition in `ROADMAP.md`'s Phase 5 ("Decision Required": choose
standard dataclasses, Pydantic, or another lightweight validation library).

This is a documentation and architectural-decision record only. No
production code was written, modified, or moved to produce it; no
dependency was added or removed; no test was created; no numbered module was
touched. It completes Phase 4's remaining deliverable list item "domain-model
library decision" without beginning Phase 5 implementation.

**Status: ACCEPTED - 2026-07-24.** At the time this decision was recorded,
nothing in `ROADMAP.md` had yet been updated by this document; that
remained a separate, later step, and this document did not itself begin
Phase 5 implementation.

**Implementation status (added at Phase 5 closeout):** Phase 5 is now
complete on `alpha-refactor` (latest technical commit `798d9c3`).
`PrivacyClassification` and `ArtifactMetadata` are implemented as frozen,
strict Pydantic v2 models; Pydantic is explicitly declared
(`requirements-domain.txt`, `pydantic>=2.13,<3`); a `pytest` foundation and
171 passing tests are established; Module 5.1 historical-manifest
compatibility normalization is implemented in `ArtifactMetadata`;
`is_declared_ai_safe` adopted fail-closed semantics; recursive structural
privacy scanning remains independent of Pydantic validation, per Accepted
Phase 4 Decision (b) below. `ROADMAP.md` now records Phase 5 as COMPLETE.
Phase 5's exit criteria (Section 13's recommendation below, and the
criteria listed in `ROADMAP.md`'s Phase 5 section) are met.

---

## 1. Context

`ARCHITECTURE.md`'s Phase 5 target model list (`CourseRef`, `Rubric`,
`RubricCriterion`, `RubricItem`, `CompileEvidence`, `ExecutionEvidence`,
`GradingRequest`, `ProviderResponse`, `GradingResult`, `ValidationReport`,
`InstructorReport`, `ApprovalState`, and others) cannot be built until a
modeling approach is chosen. `ROADMAP.md` records this explicitly as
`OD-001` and repeats it in the Phase 4 "Current Recommended Next Task" list.

`ARTIFACT_CONTRACTS.md` (Phase 4's artifact-contract inventory, accepted this
session) is the freshest and most detailed source of the *actual* needs a
modeling system must satisfy - it documents 30 concrete artifacts, verified
field-by-field from the tracked Modules 1-8 source, and its "Accepted Phase 4
Decisions" section already commits to:

- `PrivacyClassification`/`ArtifactMetadata` as the first contract to
  formalize, ahead of `Rubric` (decision a);
- privacy metadata staying declarative, never replacing recursive
  `assert_ai_safe`-style scanning (decision b);
- future transmission validation scanning both AI-safe student material and
  the grading package (decision c, a future tested change, not made yet);
- future conceptual renames (`PackageBuildSummary`, `ValidationReport`,
  `ReportSummary`) with historical filenames/loaders staying supported
  (decision d);
- the AI-safe submission manifest surviving through parity as a deprecation
  candidate (decision e);
- saved provider-request artifacts eventually carrying structured fields,
  with the existing prompt-marker regex recovery staying available as a
  compatibility loader until proven unnecessary (decision f).

This document evaluates the modeling-library choice against those
already-accepted commitments, not independently of them - a library that
cannot honor decisions (b) and (c) in particular (privacy scanning must stay
independent and structural) would be disqualified regardless of its other
merits.

---

## 2. Decision Drivers

Pulled directly from `CLAUDE.md`, `ARCHITECTURE.md`'s OD-001 entry, and
`ARTIFACT_CONTRACTS.md`'s cross-cutting findings:

- **Do not add dependencies without explaining the benefit** (`CLAUDE.md`,
  Code Quality Expectations) - any library choice must be justified against
  concrete, cited repository needs, not general popularity.
- **Windows compatibility** and **no Unix-only shell/filesystem assumption**
  (`CLAUDE.md`) - the library must work cleanly in the project's actual
  development environment (MSYS2/GCC on Windows, per `README.md`).
- **Keep I/O at system boundaries; separate pure calculation from
  persistence** (`CLAUDE.md`) - whatever is chosen must not leak into
  Module 8-style score-calculation logic.
- **Readability over mechanical rule compliance** (`CLAUDE.md`) - a future
  contributor reading a model definition should understand the contract
  without first learning a large framework surface.
- **Schema generation, migration support, dependency weight, clarity, and
  Windows compatibility** are the exact criteria `ARCHITECTURE.md`'s OD-001
  entry already names.
- **Three independent, undocumented privacy-enforcement mechanisms**
  (`send_to_ai` boolean; four required-`False` `contains_*` fields;
  recursive `assert_ai_safe` key-scanning) must be unifiable in *expression*
  without collapsing into one trusted flag (`ARTIFACT_CONTRACTS.md`,
  Accepted Phase 4 Decision b).
- **Three independent rubric-validation implementations**, each hardcoding
  the same `1e-9` float tolerance separately, are the clearest duplication
  in the repository (`ARTIFACT_CONTRACTS.md`).
- **Five-shape, status-tagged compile/execution-evidence records**
  (`not_run` / `skipped` / `compiler_unavailable` / `failed_no_source_files`
  / full result, for compile evidence; a parallel five-shape set for
  execution evidence) are a natural fit for a tagged/discriminated union,
  not a single flat required-fields record (`ARTIFACT_CONTRACTS.md`,
  Artifacts 11-12).
- **Historical shape compatibility** is mandatory: Module 3 v1 vs. v2's
  differing privacy-block field counts and filename patterns; Module 5 vs.
  5.1's differing report shapes; Module 7 runs missing `run_metadata.json`
  entirely; the golden calibration run itself (`ARTIFACT_CONTRACTS.md`,
  "Compatibility Requirements for Saved Prototype Runs").
- **The prompt-marker regex-recovery coupling** must be closeable
  eventually, but only behind a tested migration, per Accepted Phase 4
  Decision (f) - the chosen system must support adding structured fields to
  a saved request incrementally, without breaking old runs immediately.
- **No extraction proceeds without a characterization test first**
  (`ROADMAP.md`, decision recorded 2026-07-23) - whatever is chosen must be
  straightforward to test against fixture data without contacting Canvas or
  a provider.

---

## 3. Options Considered

### Option 1 - Standard-library `dataclasses` with explicit validation

Plain `@dataclass` definitions (frozen where appropriate, as
`module_7/models.py` already does for `ModelRequest`/`ProviderResponse`),
with hand-written `from_dict`/`validate` functions performing the same kind
of manual field-by-field checking already used throughout the prototype
(e.g., Module 6's `validate_rubric`, Module 8's `rubric_contract`).

### Option 2 - Pydantic v2

Class-based models (`pydantic.BaseModel`) using Python type hints to declare
fields, with built-in JSON (de)serialization, validation, JSON Schema
generation, and discriminated-union support.

### Option 3 - Another lightweight option

Considered and evaluated, per the task's own instruction, only if a
concrete advantage over Options 1-2 exists for this repository:

- **`attrs` + `cattrs`** - similar ergonomics to dataclasses with more
  converter/validator hooks; no native JSON Schema generation comparable to
  Pydantic v2's; would still require hand-written JSON (de)serialization
  glue via `cattrs` converters. No concrete advantage over Option 2 found,
  and it would be a second new dependency alongside (not instead of)
  Pydantic, since Pydantic is already present transitively (see Section 5).
- **`msgspec`** - fast, small, has `Struct` types with JSON encoding/decoding
  and some schema support. Performance is not a decision driver named
  anywhere in `CLAUDE.md`, `ARCHITECTURE.md`, or `ROADMAP.md` - this is a
  human-in-the-loop grading workflow processing one submission at a time,
  not a high-throughput service. `msgspec` would be a genuinely *new*
  dependency (not already present anywhere in the current environment,
  transitively or otherwise), unlike Pydantic. No concrete, repository-cited
  advantage was found to justify that added cost.
- **`marshmallow`** - a mature schema/validation library, but its
  schema-first (rather than type-hint-first) API is less readable for a
  contributor already reading type-hinted Python throughout this repository,
  and it has no discriminated-union ergonomics comparable to Pydantic v2's.
  No concrete advantage found.
- **`TypedDict` + the existing `jsonschema` package** - the repository
  already depends on `jsonschema` directly (used in `module_7/validation.py`
  for the provider-response schema). Staying purely dict-based with
  `TypedDict` for static-typing hints and `jsonschema.Draft202012Validator`
  for runtime checks would add no new dependency at all. However, this
  approach provides no Python object ergonomics (no attribute access, no
  `model_dump`-style serialization, no discriminated-union support beyond
  what a hand-written `if/elif` dispatch already provides), and it does not
  solve the "generate a schema from the Python type" direction the current
  hand-written `response_schema()` function would benefit from - it only
  solves the reverse (validate a dict against a hand-written schema), which
  the project already does today. No concrete advantage found over Option 1
  (which already differs from this only in giving attribute access via
  dataclasses); this candidate is effectively a variant of Option 1's manual
  approach and is not scored as a separate option.

**Conclusion:** No candidate under Option 3 clears the "concrete advantage
over Options 1-2" bar this task requires. Option 3 is not carried forward
into the comparison table below.

---

## 4. Comparison Table

| Need (from `ARTIFACT_CONTRACTS.md`) | Dataclasses + explicit validation | Pydantic v2 |
|---|---|---|
| Loading nested persisted JSON | Manual - write a `from_dict` per nested level; `json.load` + hand assembly, as every module does today | Built-in - `model_validate`/`model_validate_json` walks nested models automatically |
| Validating untrusted/malformed artifact data | Manual `if isinstance(...)`/`raise ValueError` chains, exactly like today's `validate_rubric`/`rubric_contract`/`normalize_items` | Built-in field/type validation plus custom `field_validator`/`model_validator` hooks for domain rules |
| Producing clear failure messages | Whatever the author writes; today's code stops at the first failure found in most functions | `ValidationError` aggregates every failing field in one exception, with field path and reason - a real improvement over today's stop-at-first-error pattern |
| Preserving private vs. AI-safe distinctions | Fully manual - a `PrivacyClassification` dataclass with hand-written invariants | A typed `PrivacyClassification` model with `Literal`-typed classification and explicit boolean fields; still requires the same hand-written invariant that "valid" is not "AI-safe" (see Section 8) |
| Expressing explicit content assertions (`contains_*`) | Plain boolean fields, hand-checked | Plain boolean fields, checked via `field_validator`/`model_validator`; no material difference here |
| Strict recursive privacy checks without replacing them | Naturally external - a plain dataclass has no built-in scanning, so the existing `assert_ai_safe`-style function stays untouched by construction | Also naturally external if disciplined - Pydantic validates *shape*, not policy; the recursive scan must be called separately either way (see Section 8's rule against conflating the two) |
| Loading historical Module 3/5/7/8 shapes | Hand-written adapter function per historical shape, one at a time | `model_validator(mode="before")` gives one conventional, discoverable place per model to normalize old shapes before field validation runs |
| Aliases and compatibility adapters | Hand-written field renaming/defaulting in the same adapter function above | Native `Field(alias=...)`/`populate_by_name` plus the same `mode="before"` hook for anything an alias alone cannot express |
| Tagged/discriminated unions (compile/execution evidence) | Possible via a hand-written `Literal["status"]` tag plus manual `if status == ...` dispatch; works, but re-implemented per artifact | Native discriminated-union support (`Field(discriminator=...)`) maps directly onto the five-shape compile/execution-evidence records already documented |
| Serialization back to stable JSON | Hand-written, or `dataclasses.asdict` (already used in Module 5.1 for `FileReport`) plus manual `json.dumps` | Built-in `model_dump`/`model_dump_json`, with control over aliasing, field exclusion, and mode (`python` vs. `json`) - and this exact pattern (`response.model_dump(mode="json")`) is already used in the tracked `openai_provider.py` |
| Schema generation | None built in - the project would keep hand-writing JSON Schema, exactly as Module 6's `response_schema()` does today from the rubric summary | Built-in `model_json_schema()` - could generate the provider-facing structured-output schema directly from a `Rubric`/`RubricItemAssessment` model, replacing (not just duplicating) today's hand-written generator |
| Schema-version migration | Fully manual per-version adapter functions | `model_validator(mode="before")` conventionally holds version-branching logic; still requires the author to write the migration, but gives it one standard location per model |
| Avoiding accidental coercion | Naturally strict - a dataclass performs no coercion at all unless the author writes it | Requires an explicit strictness policy (Section 9); v2's default behavior is looser than a bare dataclass unless `strict=True`/`ConfigDict(strict=True)` is set |
| Incremental adoption | Trivial - a dataclass is just a class; can be introduced one artifact at a time with zero framework setup | Also incremental - Pydantic models coexist with plain dicts/dataclasses; each artifact can be converted independently |
| Testability | Straightforward - plain Python objects, easy `assert` statements | Straightforward - constructing invalid data and asserting `ValidationError` is a standard, well-documented pattern; no Canvas/provider contact required either way |
| Dependency and maintenance cost | Zero new dependency; the project already trusts the standard library indefinitely | Already present transitively (see Section 5); if adopted explicitly, a new pinned dependency with its own release cadence to track (v1-to-v2 was a breaking rewrite historically) |
| Readability for future contributors | High - no framework vocabulary beyond `@dataclass` itself | High, but requires learning Pydantic's validator/config vocabulary (`field_validator`, `model_validator`, `ConfigDict`, discriminated unions) - a real but bounded learning cost, partly offset by Pydantic's type-hint-first style matching the project's existing type-hint usage |
| Avoiding framework leakage into service/business logic | Effectively guaranteed - there is no framework to leak | Requires an explicit rule (Section 8): pure business logic (score calculation, rubric traversal) may accept validated Pydantic domain models directly as read-only typed inputs; framework-specific validation, serialization, schema-generation, migration, and I/O remain at boundaries, not inside calculation code |

---

## 5. Recommended Decision

**Adopt Pydantic v2 as the primary system for persisted artifact contracts
and every trust/external boundary** (Canvas data, provider requests and
responses, and every disk-persisted artifact documented in
`ARTIFACT_CONTRACTS.md`).

**Continue permitting standard-library dataclasses for small, internal,
runtime-only records** that never cross a process boundary as a defined,
versioned contract (see Section 8 for the precise boundary).

**Make Pydantic an explicit, intentional, directly-declared project
dependency if this decision is accepted** - it is not one today. Verified
during this session:

- `requirements-module7.txt` (the project's own, hand-authored overlay for
  Module 7) lists only `openai>=2.0.0`, `python-dotenv>=1.0.0`, and
  `jsonschema>=4.0.0`. It does **not** list `pydantic`.
- `requirements.txt` (a UTF-16-encoded, `pip freeze`-style full environment
  snapshot, confirmed via a byte-level check during this session) lists
  `pydantic==2.13.4` and `pydantic_core==2.46.4` alongside `openai==2.47.0`
  - present because the installed `openai` SDK depends on Pydantic v2
  internally, not because any project file requests it directly.
- No tracked source file contains `import pydantic` or
  `from pydantic import ...` anywhere in the repository (verified by
  grepping every `.py` file).
- `module_7/providers/openai_provider.py` already calls
  `response.model_dump(mode="json")` and duck-types a `model_dump` attribute
  via `getattr` (`OpenAIProvider._to_plain_dict`) - this **is** a Pydantic
  v2 `BaseModel` method, called today, but only because the OpenAI SDK's
  response objects happen to be Pydantic models under the hood. The project
  never asserts this, imports `pydantic`, or subclasses `BaseModel` itself.

**Conclusion on the transitive-vs-intentional question:** Pydantic v2 is
merely transitive today - present in the environment and even lightly
exercised through duck-typing, but never a declared or directly-imported
project dependency. If this OD-001 decision is accepted, Pydantic should be
added explicitly to the project's own dependency declarations (not left to
arrive incidentally via `openai`'s dependency graph), since the project's
own `domain`/`grading` code would then import and subclass it directly, and
depending on it indirectly through another library's unrelated dependency
resolution is not an acceptable way to depend on a data-modeling library the
codebase itself would rely on.

**Models are introduced incrementally, per artifact, not as a repository-wide
conversion.** This matches `ROADMAP.md` Phase 5's own "Implementation Rules"
("no repository-wide conversion in one step") and the already-accepted
extraction order in `ARTIFACT_CONTRACTS.md`.

---

## 6. Detailed Rationale

1. **The project already depends on Pydantic v2's behavior, just not its
   declaration.** `openai_provider.py` calls `model_dump(mode="json")` on
   provider responses today. Selecting Pydantic v2 for the project's own
   models does not introduce a new kind of object into the system - it
   extends a pattern already present and already working.
2. **Discriminated unions solve a real, already-documented shape problem.**
   `ARTIFACT_CONTRACTS.md` Artifacts 11 and 12 each describe five distinct,
   mutually exclusive shapes for compile/execution evidence
   (`not_run`, `skipped`, `compiler_unavailable`, `failed_no_source_files`,
   full result). Today this is an untyped dict assembled by hand in
   `module_6_build_grading_package.py`. A `Literal`-discriminated union
   makes the five shapes explicit and gives an author a compiler/IDE-visible
   contract instead of tribal knowledge of `local_compile_run_evidence()`'s
   branches.
3. **Schema generation replaces, rather than duplicates, existing
   hand-written logic.** Module 6's `response_schema()` hand-builds a JSON
   Schema from the rubric summary today. A `Rubric`/`RubricItemAssessment`
   Pydantic model's `model_json_schema()` could generate the equivalent
   schema directly from the same model that also validates the grading
   result locally - closing part of the three-way rubric-validation
   duplication `ARTIFACT_CONTRACTS.md` identifies as the clearest
   duplication in the repository, since the schema and the validator would
   share one Python source of truth instead of three.
4. **`model_validator(mode="before")` is a natural home for the
   already-required migration work.** The project must already support
   loading Module 3 v1 vs. v2, Module 5 vs. 5.1, and provider-request
   payloads whose companion manifest may or may not still resolve. Today
   each of these is (or would be) a bespoke adapter function. Pydantic gives
   one conventional, discoverable location per model for this logic, rather
   than a new one-off function per historical shape - a smaller readability
   win than the discriminated-union or schema-generation points, but a real
   one given how many historical shapes this repository already has to
   reconcile.
5. **Aggregated validation errors are a genuine UX improvement over today's
   stop-at-first-failure pattern.** `validate_rubric`, `rubric_contract`,
   and `normalize_items` each raise on the first problem found. An
   instructor debugging a malformed grading package or a corrupted saved
   run benefits from seeing every problem at once; Pydantic's
   `ValidationError` does this by default.
6. **Dataclasses remain correct where nothing above applies.** Module 5.1's
   `CommentStats` is a pure, in-process computation accumulator - it is
   never serialized, never crosses a trust boundary, and has no historical
   shape to reconcile. Converting it to Pydantic would add validation
   machinery with no artifact contract behind it to validate, which is
   exactly the kind of dependency-without-benefit `CLAUDE.md` warns against.
   `module_7/models.py`'s `ModelRequest`/`ProviderResponse` are a more
   interesting borderline case (see Section 8) since `ModelRequest` content
   is in fact persisted into `request_payload.json` - they are reasonable
   *early* conversion candidates once Phase 5 work reaches the
   `GradingRequest` contract, but they are not proposed as the *first*
   model built (Section 13).

---

## 7. Consequences and Trade-offs

- **A new, explicit dependency-maintenance obligation.** Selecting Pydantic
  as a declared (not incidental) dependency means tracking its release
  notes and pinning/upgrading it deliberately, distinct from whatever
  version `openai` happens to require. Pydantic's own v1-to-v2 transition
  was a substantial breaking rewrite; a future v3 could repeat that pattern
  (see Section 14).
- **Two coexisting idioms during migration.** Dataclasses for transient
  internal records and Pydantic for persisted contracts must be documented
  (Section 8) so a contributor knows which to reach for; without that
  documentation, this would read as inconsistency rather than a deliberate
  policy.
- **Two specific misuse risks must be actively guarded against, not just
  assumed away:**
  1. Treating "this Pydantic model validated successfully" as "this data is
     safe to send to a model provider." `ARTIFACT_CONTRACTS.md`'s Accepted
     Phase 4 Decision (b) already commits to keeping recursive privacy
     scanning independent of any declared classification; this OD-001
     decision must not weaken that commitment, and the rule is restated
     explicitly in Section 8 below.
  2. Letting framework-specific boundary operations (validation,
     serialization, schema generation, migration, or I/O) leak into
     calculation code (Module 8-style score/criterion/rule arithmetic).
     Validated Pydantic models may still be read directly by pure
     calculations - the risk to guard against is calculation code
     performing `model_validate`, `model_dump`, `model_json_schema`,
     migration, or file/network I/O itself, not calculation code merely
     accepting a validated model as an input.
- **Coercion risk if left unconfigured.** Pydantic v2's default field
  behavior permits some coercion (for example, numeric-string inputs can be
  coerced to `int`/`float` in lax mode) that a bare dataclass would never
  perform. This is addressed by an explicit strictness policy (Section 9),
  not left to each model author's discretion.

---

## 8. Rules for Where the Selected Model System Should and Should Not Be Used

**Use Pydantic v2 for:**

- Every persisted artifact contract documented in `ARTIFACT_CONTRACTS.md`
  (all 27 required artifacts plus the 3 additional diagnostic/preview
  artifacts, where they are ever promoted to a typed contract at all).
- Anything that crosses a trust boundary: Canvas API data once translated
  into domain models, provider requests/responses, and any artifact that is
  written to disk and later reloaded by a different process or session.
- Anything requiring schema-version migration, historical-shape aliasing,
  or JSON Schema generation.

**Use standard-library dataclasses for:**

- Genuinely transient, in-process-only computation records with no
  persistence and no trust-boundary role - `CommentStats` (Module 5.1) is
  the clean existing example.
- Small configuration/value objects that never cross a process boundary and
  carry no historical-shape or migration concern.

**Business-logic boundary:**

- Pure business logic (score/criterion/rule arithmetic - the Module
  8-equivalent logic in the target `grading` area) may accept validated
  Pydantic domain models as **read-only typed inputs**. A validated
  `Rubric` or `GradingResult` model is a perfectly reasonable argument type
  for a pure calculation function; there is no requirement to unwrap it
  into a duplicate dataclass or plain dictionary first.
- Pure business logic must **not** perform `model_validate`, `model_dump`,
  `model_json_schema`, file I/O, network I/O, schema-version migration, or
  boundary translation (Canvas-to-domain, provider-response-to-domain, or
  historical-shape normalization). Those operations remain at application
  boundaries, per `CLAUDE.md`'s "keep I/O at system boundaries; separate
  pure calculation from persistence and network access" - the rule is about
  keeping *those specific operations* out of calculation code, not about
  which object type calculation code is allowed to read.
- Introducing a separate dataclass or plain structure alongside an existing
  Pydantic model is appropriate only when it provides a concrete
  simplification for a specific calculation (for example, a small
  intermediate accumulator with no independent contract of its own, in the
  spirit of `CommentStats`). It must not be adopted as a mandatory wrapper
  step around every Pydantic model merely to keep Pydantic types out of
  calculation code.

**Do not:**

- Treat successful Pydantic validation as equivalent to AI-safety
  clearance. The recursive, `assert_ai_safe`-style structural scan must run
  independently, on every request before transmission, regardless of
  whether the data it scans is itself represented as a validated Pydantic
  model. A schema-valid `AISafeStudentMaterial` model that happens to carry
  a forbidden key must still be caught and rejected by the recursive scan,
  exactly as today - this is a restatement, not a revision, of
  `ARTIFACT_CONTRACTS.md`'s Accepted Phase 4 Decision (b).
- Convert a dataclass to Pydantic merely for stylistic consistency. Every
  conversion must be justified by an actual persisted-contract or
  trust-boundary need, per `CLAUDE.md`'s "do not add dependencies without
  explaining the benefit."

---

## 9. Strictness and Coercion Policy

### Numeric fields (scores and points)

Rubric scores and point values (`maximum_points`, `suggested_points`,
`recommended_value`, and similar) are not required to preserve Python's
`int`-versus-`float` type identity - the tracked prototype itself already
accepts both forms interchangeably (Module 6's `validate_rubric` and Module
8's `rubric_contract` both test `isinstance(value, (int, float))`, never
requiring one specific type). Instead:

- Score and point fields may accept any finite JSON integer or
  floating-point number.
- Numeric strings (for example, `"5"` or `"5.0"`) must **not** be silently
  converted to a number - a string in a numeric field is a validation
  error, not a coercion opportunity.
- Booleans must **not** be accepted as numbers, even though Python's `bool`
  is technically an `int` subclass (this is the one place today's prototype
  code is already careful: Module 8's `normalize_items` explicitly checks
  `isinstance(points, bool)` to reject a boolean disguised as a score).
- `NaN`, positive infinity, and negative infinity must be rejected - a
  score or point value must be a finite number.
- Any normalization to one canonical numeric representation (for example,
  always storing scores as `float`) must be explicit, documented, and
  covered by a test - it is not a default behavior of the model system, and
  it is not required by this policy.
- Current prototype behavior - accepting both `int` and `float` values
  interchangeably for every score/point field - must be preserved unless a
  later, separately documented migration deliberately changes it.

### Unknown fields (`extra` policy)

A single blanket `extra="forbid"` for every model is not required and is
not appropriate for every kind of input this project handles:

- Canonical, current-version artifacts **produced by this project itself**
  (the shapes this project fully controls, such as a freshly-built
  `Rubric` or `GradingResult` at its current schema version) should
  normally use `extra="forbid"`, mirroring the `additionalProperties: false`
  pattern the hand-written provider-response schema already enforces in
  Module 6 - an unrecognized field on a current-version, project-authored
  artifact should fail loudly.
- Historical artifact shapes (Module 3 v1 vs. v2, Module 5 vs. 5.1, and any
  other previously-documented shape difference) must pass through explicit
  compatibility normalization - per Section 10's `model_validator(mode=
  "before")` approach - **before** canonical-model validation runs, rather
  than being tolerated by loosening the canonical model's own `extra`
  setting.
- Raw Canvas API responses and raw model-provider responses must not be
  modeled as permanently closed (`extra="forbid"`) copies of an external
  API's response shape. External APIs can add fields without notice; these
  responses should be translated or explicitly whitelisted into a domain
  model at the boundary (matching `ARCHITECTURE.md`'s "Canvas records
  should be translated into domain models at the boundary"), not modeled as
  a rigid mirror of whatever the external API happened to return on a given
  day.
- Any exception to `extra="forbid"` on a project-authored, current-version
  model must be localized to the specific model/field that needs it,
  documented with the reason, and covered by a test - it is not a default
  to reach for broadly.
- Unknown fields must never be silently copied from a private or external
  object into an AI-safe artifact, regardless of the `extra` setting in
  effect - this is a privacy rule, not a schema-strictness rule, and it is
  enforced by the recursive `assert_ai_safe`-style scan (Section 8), not by
  `extra="forbid"` alone. A permissive `extra` setting used for a raw
  Canvas/provider response at the boundary must never be the same model
  that is later passed to the privacy-scanning/transmission step.

### Status-tagged fields

- Every status-tagged field (`assessment_status`, `recommended_action`,
  compile/execution `status`, and similar) is typed as a `Literal` (or a
  discriminated union, where the tag selects among structurally different
  shapes) rather than a bare `str`. An unrecognized status value must be a
  validation error, not a silently-accepted string - this simultaneously
  satisfies the "avoid accidental coercion" and "tagged/discriminated
  union" decision drivers.
- Where lax coercion would be genuinely useful (for example, accepting both
  `None` and an empty list as "no items" for backward compatibility with an
  older saved shape), that tolerance must be expressed explicitly via a
  `model_validator(mode="before")` normalization step, not via a globally
  lax configuration - so the tolerance is visible, tested, and scoped to
  the one field/shape it exists for.

---

## 10. Backward-Compatibility Strategy

- Every Pydantic-modeled persisted artifact must be loadable from, at
  minimum, the shapes already catalogued in `ARTIFACT_CONTRACTS.md`'s
  "Compatibility Requirements for Saved Prototype Runs": both Module 3
  manifest shapes (v1 and v2); both Module 5 sanitization-report shapes (5
  and 5.1); a saved Module 7 run whose `request_manifest.json` paths no
  longer resolve; a saved Module 7 run with no `run_metadata.json` at all;
  and the golden calibration run itself once it becomes a committed
  fixture.
- `model_validator(mode="before")` is the designated, single location per
  model where old-shape normalization happens - for example, normalizing
  the four required-`False` `contains_*` fields and the separate
  `send_to_ai` boolean into one internal representation **without deciding
  to collapse them into a single flag**, per Accepted Phase 4 Decision (b):
  both forms of the assertion must remain independently inspectable after
  normalization, not merged away.
- The prompt-marker regex-recovery fallback
  (`module_7_revalidate.py`/`module_8_create_grading_report.py`'s
  independent `extract_request_material()` functions) is unaffected by this
  decision and must remain available as a loader of last resort for
  historical runs, exactly as Accepted Phase 4 Decision (f) already
  requires. This OD-001 decision recommends adding structured fields to
  *future* saved requests; it does not require or imply retiring the regex
  fallback, which stays until a compatibility test proves it is no longer
  needed for any run of interest.
- No numbered prototype module is modified, renamed, or retired as part of
  adopting this decision. Per `CLAUDE.md`'s "Preserve the Working
  Prototype" rule, every model built under this decision is validated
  against the prototype's existing output before any prototype script is
  changed to use it.

---

## 11. Schema-Version Strategy

- Every new Pydantic-modeled persisted artifact carries an explicit
  `schema_version` field. This directly closes the gap
  `ARTIFACT_CONTRACTS.md` documents repeatedly: no `schema_version` on any
  Module 1-5 or Module 7 artifact; an inconsistent presence even *within* a
  single Module 6 run; and an independent, uncoordinated counter used by
  Module 8.
- `model_json_schema()` generates the JSON Schema for a given model version
  directly from its Python type definition, replacing the pattern where
  Module 6 hand-builds a JSON Schema from a separately-validated rubric
  summary. Where that generated schema must additionally satisfy a model
  provider's structured-output requirements (as today's `response_schema()`
  does), the same generated schema - or a thin, explicitly-documented
  transform of it - should be reused rather than hand-maintained a second
  time, so there is one source of truth instead of the current arrangement
  where the rubric shape is independently re-derived three times.
- A schema-version increment requires either:
  1. a `model_validator(mode="before")` migration that deterministically
     transforms the older version's shape into the current one; or
  2. an explicit, clearly-worded rejection identifying the incompatible
     version, when no safe deterministic migration exists.

  This matches `CLAUDE.md`'s Artifact and Storage Rules exactly: increment
  the version, document the change, provide deterministic migration when
  practical, preserve older fixtures, and reject incompatible artifacts
  clearly rather than silently reinterpreting them.

---

## 12. Testing Implications

- Per the 2026-07-23 `ROADMAP.md` decision, no shared model may be extracted
  from a prototype module that does not yet have a passing characterization
  test proving the prototype's current behavior. This applies identically
  regardless of which modeling system is chosen, and this OD-001 decision
  does not relax it.
- For every new Pydantic model, the minimum test set is:
  1. successful construction from a real (synthesized/anonymized) saved
     prototype artifact of the exact current shape;
  2. one failing-validation case per required field or invariant, asserting
     `ValidationError` and checking that the failure message identifies the
     right field;
  3. at least one historical-shape/aliasing case, for whichever artifact's
     model is built first that has more than one known historical shape
     (Module 3 v1/v2 or Module 5/5.1 are the two candidates already
     catalogued);
  4. a test proving that a *schema-valid* model can still be rejected by
     the independent recursive privacy scan - i.e., a test that directly
     protects Accepted Phase 4 Decisions (b) and (c) from being silently
     eroded by a future contributor who assumes "validated" means "safe."
- All such tests use local fixtures only; none contact Canvas or a model
  provider, per `CLAUDE.md`'s Testing Requirements.

---

## 13. Initial Phase 5 Model Recommendation — IMPLEMENTED

`PrivacyClassification`, `ArtifactMetadata`, and the Module 5.1
compatibility normalization described below were implemented and tested
during Phase 5 (171 passing tests; see `ROADMAP.md`'s Phase 5 section for
the full completion record). The recommendation and rationale below are
preserved as originally written.

This document does not revise `ARTIFACT_CONTRACTS.md`'s already-accepted
Phase 4 Decision (a): **`PrivacyClassification`/`ArtifactMetadata` remains
the first model to build**, now concretely as a Pydantic v2 model.

Pydantic v2 suits this specific model well: `PrivacyClassification` must
simultaneously express (1) a declared classification (a `Literal`-typed
field, analogous to today's `send_to_ai` boolean), (2) explicit `contains_*`
assertions (plain boolean fields), and (3) an unambiguous, class-level
statement that constructing or validating this model **does not** certify
AI-safety - the recursive scan remains a separate, required call. A short,
prominent docstring on the model plus a rule enforced in code review (not a
runtime check the model itself could perform) is the intended way to keep
that boundary visible to future contributors.

**Recommended first characterization-test target:** Module 5.1's
`module_5_ai_package_manifest.json` (Artifact 7 in `ARTIFACT_CONTRACTS.md`),
since it carries the strictest current enforcement in the pipeline
(`validate_ai_manifest()`'s four required-`False` checks) and is therefore
the best available stress test for the new model's strictness/coercion
policy (Section 9) before it is applied to any other artifact.

---

## 14. Conditions That Would Justify Revisiting This Decision

- Pydantic releases a future major version with breaking changes comparable
  in scope to the v1-to-v2 rewrite, and the migration cost is judged to
  outweigh the continued benefit at that time.
- The project drops the `openai` dependency entirely (for example, adopting
  a local model provider under `OD-005`) in a way that also removes
  Pydantic's transitive presence - this would not, by itself, invalidate the
  discriminated-union/schema-generation/migration-validator benefits argued
  for in Section 6, but it would remove the "already present and already
  exercised" argument's weight, and the decision should be re-examined on
  its remaining merits alone at that point.
- A characterization test, built while formalizing any specific artifact,
  reveals a historical shape that Pydantic v2 cannot represent or migrate
  without contortions clearly disproportionate to a hand-written adapter
  function - if this happens repeatedly rather than as an isolated case, it
  would call the general recommendation into question.
- After Phase 5/6 experience, the measured maintenance burden (upgrade
  breakage, contributor confusion between the dataclass/Pydantic split)
  demonstrably exceeds the documented benefit.

---

## Original Decision Summary and Current Outcome

- **File created:** `OD-001_DOMAIN_MODEL_LIBRARY.md` (this file).
- **Files inspected:** `CLAUDE.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
  `REPOSITORY_INVENTORY.md`, `ARTIFACT_CONTRACTS.md`, `requirements.txt`
  (confirmed UTF-16LE via byte-level check), `requirements-module7.txt`, and
  `module_7/providers/openai_provider.py` (to confirm the existing
  `model_dump` usage referenced in Sections 5-6) - none modified.
- **Recommended OD-001 decision (ACCEPTED 2026-07-24):** Pydantic v2 as the
  primary system for persisted artifact contracts and trust-boundary data;
  standard dataclasses remain appropriate for small, internal,
  non-persisted, runtime-only records; Pydantic was merely transitive when
  this decision was accepted, and the decision called for it to become an
  explicit, intentional dependency once Phase 5 began — it did, during
  Phase 5 (`requirements-domain.txt`, `pydantic>=2.13,<3`); models are
  introduced incrementally, per artifact, starting with
  `PrivacyClassification`/`ArtifactMetadata`; privacy scanning remains
  independent of Pydantic validation.
- **Corrected policies in this revision (Sections 8-9):** numeric score/point
  fields accept both JSON integers and floats without requiring Python
  `int`/`float` identity preservation, while still rejecting numeric
  strings, booleans, `NaN`, and infinities, and preserving today's
  int-or-float-accepting prototype behavior unless a documented migration
  changes it; `extra="forbid"` applies normally only to canonical,
  current-version, project-authored models, not to historical shapes
  (normalized before validation) or to raw Canvas/provider responses
  (translated or whitelisted at the boundary instead), with any exception
  localized, documented, and tested; and pure business logic may accept
  validated Pydantic models as read-only typed inputs directly, provided it
  performs no validation, serialization, schema-generation, or I/O of its
  own - conversion to a separate dataclass or plain structure is optional,
  used only where it is a concrete simplification, never a mandatory
  wrapper.
- **Strongest argument against this recommendation:** adopting Pydantic as
  a declared dependency creates an explicit, ongoing maintenance obligation
  distinct from `openai`'s own dependency resolution - Pydantic's v1-to-v2
  history shows this library can force a real migration effort on a future
  breaking release, and for a project whose `CLAUDE.md` explicitly
  privileges minimal dependencies and stdlib-first solutions, a
  dataclasses-only approach would avoid that risk entirely at the cost of
  more hand-written validation/migration code per artifact. This is a
  legitimate, not a manufactured, counter-argument, and it is the reason
  Section 14 names "future Pydantic v3 breakage" as a first-class condition
  for revisiting this decision rather than treating the choice as
  permanent.
- **Implemented first Phase 5 models:** `PrivacyClassification` and
  `ArtifactMetadata`, as Pydantic v2 models, with the first characterization
  test built against Module 5.1's `module_5_ai_package_manifest.json`
  shape, and `ArtifactMetadata`'s Module 5.1 compatibility normalization
  path also implemented and tested. 171 tests pass.
- **Unresolved concerns:**
  1. Whether `ModelRequest`/`ProviderResponse` (`module_7/models.py`) should
     convert to Pydantic early (given they already partially cross the
     persisted-artifact boundary via `request_payload.json`) or wait until
     the `GradingRequest` contract is formally reached in the extraction
     order - this document leans toward waiting, but does not decide it.
  2. The precise mechanism for reusing one generated schema for both local
     Pydantic validation and the model-provider's structured-output
     requirement (Section 11) needs a worked example against the current
     `rubric.json` before it can be considered settled, not just proposed.
  3. All unresolved questions already carried forward in
     `ARTIFACT_CONTRACTS.md`'s Summary (the items inherited from
     `REPOSITORY_INVENTORY.md` Part 5) remain open and are not re-litigated
     here.
- **Confirmation that no existing file changed when this decision record was
  originally created (2026-07-24):** Confirmed. At that time, only
  `OD-001_DOMAIN_MODEL_LIBRARY.md` was created. No production Python code,
  schema, configuration, or existing documentation (including `ROADMAP.md`
  and `ARTIFACT_CONTRACTS.md`) was modified, renamed, moved, staged,
  committed, or pushed. No dependency was added or removed. No numbered
  module was touched. No Canvas, model-provider, or other network call was
  made. No student code was compiled or executed. (Phase 5 implementation
  and this document's own subsequent updates naturally postdate that
  original, unmodified-repository snapshot.)
