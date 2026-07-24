# Module 7 Validator Patch

This patch fixes a false-positive validation failure introduced when Module 7
began accepting local compilation, execution, output-comparison, and package
inventory evidence.

## Cause

The old domain validator assumed that every `evidence[].file` value had to be
a student source filename. The model correctly cited structured evidence such
as:

```text
objective_evidence.student_compilation
objective_evidence.student_execution
objective_evidence.student_execution.stdout
objective_evidence.output_comparison
ai_safe_student_material.json
```

Those references existed in the sent grading package, but the validator
incorrectly labeled them as unknown student files.

## Install

Copy these files into the project root, replacing `validation.py`:

```text
module_7/
    validation.py
module_7_revalidate.py
```

No changes are required to the prompt, response schema, provider, or Module 6.

## Revalidate the Existing Run Without Paying Again

```cmd
python module_7_revalidate.py ^
  output\assignment_3572383\submission_001\grading_request\model_runs\20260723_155856_openai_gpt-5_2
```

This creates:

```text
validation_report.revalidated.json
run_metadata.revalidated.json
```

It contacts neither OpenAI nor Canvas.

After reviewing the revalidated report, this version backs up and replaces the
original validation and metadata files:

```cmd
python module_7_revalidate.py ^
  output\assignment_3572383\submission_001\grading_request\model_runs\20260723_155856_openai_gpt-5_2 ^
  --replace-originals
```

Backups are named:

```text
validation_report.before_revalidation.json
run_metadata.before_revalidation.json
```

## Validator Rules

The patched validator now distinguishes among:

1. Student source files  
   Must use valid one-based source line ranges.

2. Starter, reference, and supporting files  
   May use line ranges validated against the package file metadata.

3. Structured package documents  
   `grading_package.json`, `ai_safe_student_material.json`, and
   `local_compile_run_evidence.json` are accepted with null line numbers.

4. Existing objective-evidence paths  
   Dot paths beginning with `objective_evidence` are resolved against the
   actual grading package. Unknown paths are rejected.

5. Text objective evidence  
   Values such as `objective_evidence.student_execution.stdout` may use
   validated text line ranges.

This still catches hallucinated filenames and package paths while permitting
the legitimate evidence introduced by the compile/run stage.
