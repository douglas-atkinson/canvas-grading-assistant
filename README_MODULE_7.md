# Module 7 — Provider-Neutral Model Evaluation, Revision 2

Module 7 sends exactly one anonymous grading request to the configured model
provider and stores one structured advisory response. It makes no Canvas
changes.

## Revision 2 changes

- Uses `prompts/module_7_grading_prompt_v2.txt` by default.
- Forbids deductions caused solely by missing local evidence.
- Supports `assessment_status: requires_local_evidence` with
  `suggested_points: null`.
- Forbids grading blank space created by comment removal.
- Forbids grading unchanged starter-code formatting or organization.
- Forbids importing stricter requirements from the reference solution.
- Adds semantic validation after JSON-schema validation:
  - exact rubric IDs;
  - correct criterion/item relationships;
  - exact per-item maximums;
  - status/score consistency;
  - unique global-rule IDs;
  - valid student evidence filenames and line ranges.

## Dry run

```cmd
python module_7_evaluate.py ^
  output\assignment_3572383\submission_001\grading_request\grading_package.json ^
  output\assignment_3572383\submission_001\grading_request\ai_safe_student_material.json ^
  --response-schema output\assignment_3572383\submission_001\grading_request\response_schema.json
```

The request payload should report:

```text
prompt_version: module7-grading-v2
```

## Send one request

After reviewing the dry-run payload:

```cmd
python module_7_evaluate.py ^
  output\assignment_3572383\submission_001\grading_request\grading_package.json ^
  output\assignment_3572383\submission_001\grading_request\ai_safe_student_material.json ^
  --response-schema output\assignment_3572383\submission_001\grading_request\response_schema.json ^
  --send
```

The response is valid only when JSON parsing, JSON Schema, anonymous-label,
and grading-domain validation all pass.

## Provider architecture

The provider interface and factory remain unchanged. OpenAI is still the only
registered provider, but a future local provider can be added without changing
the grading package, prompt contract, schema, validation rules, or downstream
review workflow.
