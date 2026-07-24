# Module 8 Design Boundary

## Purpose

Create one trustworthy instructor report from one saved and validated Module 7
result.

```text
Validated Module 7 advisory result
                |
                v
Module 8 local calculation and rendering
                |
                v
Private instructor JSON + Markdown report
```

Module 8 restores identity only after provider activity has finished. Its
output is therefore private and must never be sent back through the AI-facing
pipeline.

## Canonical output

`one_student_grading_report.json` is canonical.

`one_student_grading_report.md` is a readable rendering and is not an
automation source.

## Score semantics

Module 8 calculates:

1. Base rubric points from the structured rubric-item results.
2. Recommended global deductions.
3. Recommended score caps.
4. Suggested score after adjustments.

The score remains advisory. Module 8 never assigns an instructor final score.
When any item is `requires_local_evidence`, the complete suggested score is
`null`; only `scored_points_so_far` is retained.

## Why Module 8 precedes 8B–8D

The one-submission report contract should be stable before batching,
spreadsheets, or approval import are designed. That keeps orchestration and
Excel behavior from hiding mistakes in the core scoring calculation.
