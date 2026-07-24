# Canvas Grading Assistant

A privacy-conscious, human-in-the-loop grading assistant for programming assignments submitted through Canvas.

The project began as a small Canvas API exploration and grew into a working end-to-end prototype that can retrieve a programming submission, prepare a privacy-safe copy, compile and run the code locally, request an advisory AI evaluation, validate the structured response, and create a readable one-student grading report.

> **Project status:** Working prototype through Module 8. Active refactoring toward an end-user alpha.

## Why This Project Exists

Programming assignments are time-consuming to grade well. A useful grading assistant should do more than produce a score: it should preserve instructor authority, respect student privacy, cite evidence, apply a rubric consistently, and make every automated decision reviewable.

This project is designed around those requirements.

The AI is advisory only. It does not determine the final grade, and the current project does not post grades or feedback to Canvas.

## Current Capabilities

The working prototype supports the following workflow:

1. Connect to Canvas and inspect a course.
2. Select and inspect an assignment.
3. Retrieve submission metadata.
4. Download and safely extract one submitted ZIP archive.
5. Create a separate AI-candidate copy of the source code.
6. Remove comments and redact known identifiers while preserving useful line positions.
7. Build a provider-neutral grading package.
8. Compile the student program locally with an explicitly selected compiler.
9. Optionally execute untrusted student code with an explicit flag and timeout.
10. Compare runtime output with validated reference output.
11. Send one structured advisory grading request to a configured model provider.
12. Validate the returned JSON against schema and project-specific rules.
13. Revalidate saved results locally without paying for another model request.
14. Restore the student identity locally after all provider activity is complete.
15. Produce canonical JSON and readable Markdown grading reports.

The current tested workflow uses C++ submissions, Canvas, GCC through MSYS2, and OpenAI as the model provider.

## Core Design Principles

### Human Review Is Required

The model returns a grading suggestion, not a final grade.

Every generated instructor report is explicitly marked:

```json
{
  "approval": {
    "status": "NOT_APPROVED",
    "final_score": null
  }
}
```

Instructor approval and Canvas writeback belong to later, separate stages.

### Privacy by Separation

Private Canvas metadata and AI-safe material are stored separately.

The model-facing package excludes:

- student names;
- Canvas user IDs;
- attachment download URLs;
- original ZIP filenames;
- private submission metadata not needed for grading.

Student identity is restored only after the model response has been saved and validated locally.

### Student Code Is Untrusted

Compilation and execution are separate operations.

Student code is executed only when the instructor explicitly enables execution. Runtime is constrained by a timeout, and the result is captured as objective evidence.

This prototype is not yet a hardened sandbox. Do not treat local execution as suitable for hostile code.

### Objective Evidence Beats Guesswork

When available, local evidence is stronger than source-code inference:

- compiler and version;
- compile command;
- return code;
- warnings and errors;
- execution status;
- standard output and standard error;
- timeout result;
- normalized output comparison.

Missing evidence must not automatically become a deduction.

### Deterministic Data Contracts

Rubrics, grading packages, model responses, validation reports, and instructor reports use structured JSON contracts.

The long-term alpha will validate these contracts through shared typed models rather than relying on AI to transform arbitrary documents into usable data.

## Prototype Workflow

```text
Canvas
  |
  v
Course and assignment inspection
  |
  v
Private submission manifest
  |
  v
Safe download and extraction
  |
  v
Privacy-safe student-material copy
  |
  v
Grading package plus local compile/run evidence
  |
  v
Advisory model evaluation
  |
  v
Schema and domain validation
  |
  v
Private one-student instructor report
```

The prototype currently implements this flow as numbered development modules. Those modules intentionally produce inspectable artifacts at every stage.

That approach was valuable for development and debugging. The active `alpha-refactor` branch is reorganizing the same proven behavior into reusable services and application workflows.

## Project Milestone

The tag:

```text
prototype-modules-1-through-8
```

marks the known working prototype through the one-student grading-report stage.

Current branches:

- `main` — stable project history and integrated work;
- `alpha-refactor` — active application refactoring.

## Planned Alpha

The end-user alpha is intended to add:

- shared domain models and versioned schemas;
- reusable Canvas, privacy, execution, grading, and reporting services;
- a coherent command-line application;
- deterministic assignment-package creation and validation;
- resumable workspace and run manifests;
- sequential processing of multiple submissions;
- an instructor review workbook;
- validated import of instructor-approved grades;
- complete audit trails and recovery information.

The alpha will still stop before automatic Canvas writeback.

## Later Version 1 Goals

A later operational version may add:

- proposed-change previews;
- explicit instructor approval gates;
- protected Canvas grade and feedback posting;
- duplicate-post prevention;
- additional model providers;
- local-model evaluation;
- a desktop or local web interface;
- installation and recovery tooling.

## Repository Direction

The target architecture separates the project into focused areas such as:

```text
canvas
submissions
privacy
execution
grading
reporting
review
storage
workflows
domain models
configuration
```

The current numbered scripts will remain available until their replacements reproduce the working prototype through automated regression tests.

## Development Setup

The project is under active refactoring, so setup instructions may change.

### Requirements

- Python 3
- A Canvas account with API access
- A Canvas API token
- Access to a Canvas course and assignment
- A supported C++ compiler for local compilation
- A configured model-provider account for live advisory evaluation

The tested Windows compiler setup uses the MSYS2 UCRT64 build of GCC.

### Local Environment

Create and activate a virtual environment, then install the project requirements:

```bash
python -m venv .venv
```

Windows Command Prompt:

```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a local `.env` file based on `.env.example` and provide the required Canvas settings:

```text
CANVAS_URL=https://your-institution.instructure.com
CANVAS_TOKEN=your_canvas_api_token
COURSE_ID=your_course_id
```

Never commit `.env`.

Provider configuration is stored separately from student data. Do not place API keys in source files, JSON artifacts, screenshots, documentation, issues, or commits.

## Safety and Privacy Warning

This project processes educational records and may handle FERPA-protected information.

Do not commit or publish:

- downloaded student submissions;
- private manifests;
- student names or Canvas user IDs;
- grading reports containing student identities;
- model request or response files containing private information;
- Canvas access tokens;
- provider API keys;
- `.env` files;
- generated `output`, `workspace`, or run directories.

Before using this project with real students, review your institution's policies for:

- student privacy;
- third-party AI services;
- data retention;
- automated decision support;
- source-code execution;
- Canvas API use.

The instructor remains responsible for every final grading decision.

## Testing Philosophy

The refactor will preserve known end-to-end regression scenarios, including:

- a successful full-credit submission;
- compilation failure;
- missing source files;
- runtime timeout;
- malformed provider output;
- missing local evidence;
- privacy-leak detection;
- altered review-workbook data.

Tests must not contact Canvas or a model provider unless explicitly marked as live integration tests.

## Contributing

The project is being developed primarily as an instructional and practical tool, but contributions, issue reports, architecture discussions, and assignment-package examples are welcome.

Before contributing:

1. Do not include real student data.
2. Do not include credentials or private run artifacts.
3. Preserve the human-review boundary.
4. Do not weaken privacy or validation checks merely to make a test pass.
5. Keep provider-specific code behind a provider abstraction.
6. Add or update tests for behavior changes.

## Public Project Status

This repository may be made public while the alpha is still under development.

That is intentional. The project is useful as an example of:

- incremental API exploration;
- privacy-aware AI integration;
- artifact-driven development;
- deterministic validation;
- human-in-the-loop grading architecture;
- refactoring a working prototype into an application.

It should not yet be represented as production-ready grading software.

## Origins

This repository began from a Canvas API course template used for an AI-assisted programming course. The template provided the initial Canvas connection and development environment. The grading workflow, privacy pipeline, local evidence system, model validation, and reporting architecture were developed as the capstone evolved.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

Instructors and developers are welcome to study, adapt, and extend the project for their own courses and institutions, subject to their local privacy, security, and academic policies.

## Disclaimer

This software is provided as-is.

It is an experimental instructor-support tool, not an autonomous grading authority. Always review source evidence, model recommendations, calculated totals, and proposed feedback before using the results in an academic setting.
