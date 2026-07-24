# Module 6 — Build One Grading Package with Local Evidence

Module 6 combines one AI-safe student submission with the instructor grading
assets, attempts local compilation, optionally executes the compiled program,
and creates the provider-neutral files consumed by Module 7.

It contacts neither Canvas nor a model provider.

## Updated command

From the project root:

```cmd
python module_6_build_grading_package.py ^
  grading_assets\cars_engines_steering ^
  output\assignment_3572383\submission_001 ^
  --overwrite ^
  --run-student-code ^
  --require-compiler
```

`--overwrite` now preserves any existing `grading_request\model_runs` folder,
including earlier baseline model responses.

## Compiler detection

With `--compiler auto`, Module 6 checks:

1. the `CXX` environment variable;
2. `g++`;
3. `clang++`;
4. `cl`.

MSVC `cl` must normally be run from a Visual Studio Developer Command Prompt
so its include and library environment is configured. An explicit executable
may be supplied:

```cmd
--compiler g++
```

or:

```cmd
--compiler clang++
```

Use `--require-compiler` to fail rather than quietly produce
`compiler_unavailable` evidence.

## Execution safety

Compilation is attempted by default. Student code is executed only when the
explicit `--run-student-code` flag is present.

Execution has a hard timeout, defaulting to 10 seconds:

```cmd
--run-timeout 10
```

The timeout limits hangs but is not a full operating-system sandbox. Student
code should be treated as untrusted.

## New output

Module 6 now creates:

```text
grading_request/
├── grading_package.json
├── ai_safe_student_material.json
├── response_schema.json
├── local_compile_run_evidence.json
├── grading_request_preview.txt
├── package_validation_report.json
├── grading_request_manifest.json
└── model_runs/                         # preserved when already present
```

`local_compile_run_evidence.json` records:

- compiler identity and version;
- path-neutral compile command;
- compile return code and output;
- execution return code and output;
- timeout status;
- exact and normalized comparison with validated reference output, when
  reference output is available.

The normalized comparison ignores blank lines, capitalization, indentation,
and insignificant whitespace around colons. It is evidence, not an automatic
final grading decision.

## Missing evidence

The generated response schema now permits:

```json
{
  "assessment_status": "requires_local_evidence",
  "suggested_points": null,
  "manual_review_needed": true
}
```

Missing evidence must not be converted into an arbitrary point deduction.
