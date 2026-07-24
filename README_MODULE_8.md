# Module 8 — One-Student Grading Report

Module 8 consumes one **validated** Module 7 model run and creates a canonical
private JSON report plus a readable Markdown report for one student.

It does not contact Canvas or a model provider, approve a grade, or post
feedback.

## Install

Copy these files into the repository root:

```text
module_8_create_grading_report.py
README_MODULE_8.md
MODULE_8_DESIGN.md
```

## Typical command

```cmd
python module_8_create_grading_report.py ^
    output\assignment_3572383\submission_001\grading_request\model_runs\20260723_155856_openai_gpt-5_2 ^
    --private-manifest output\assignment_3572383_historical_private_submissions.json
```

Use the actual private-manifest filename in the project.

## Output

```text
<model_run_directory>\
└── module_8_report\
    ├── one_student_grading_report.json
    ├── one_student_grading_report.md
    ├── report_validation.json
    └── module_8_report_manifest.json
```

The JSON file is canonical. The Markdown file is the readable rendering.

## Rules

- Module 8 refuses an invalid Module 7 result.
- It prefers `validation_report.revalidated.json` and
  `run_metadata.revalidated.json` when they exist.
- Rubric totals are calculated locally from the authoritative rubric.
- Model-generated totals are never trusted.
- `requires_local_evidence` items remain unresolved and prevent a complete
  advisory score.
- Recommended deductions and score caps are recalculated locally.
- Identity restoration requires a private manifest marked `send_to_ai: false`.
- The generated report is private and marked `send_to_ai: false`.
- The approval state is always `NOT_APPROVED`.
- Canvas and the model provider are never contacted.

## Anonymous development mode

```cmd
python module_8_create_grading_report.py <model_run_directory> ^
    --allow-anonymous-report
```

Anonymous mode must be deliberate; it is not the normal default.

## Replacing an existing report

Add:

```text
--overwrite
```
