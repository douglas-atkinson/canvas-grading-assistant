# Instructor Grading Notes

## Authority and Purpose

- The rubric is the primary scoring authority.
- The assignment specification explains what students were asked to build.
- These notes clarify the instructor's grading intent.
- The validated reference implementation is one successful solution, not a
  template students must imitate.
- The AI provides a grading suggestion only. The instructor determines the
  final score.

## Fairness and Alternative Designs

- Accept alternative implementations that satisfy the assignment requirements.
- Do not compare student code to the reference implementation line by line.
- Do not grade based on textual similarity to the reference implementation.
- Equivalent class designs, helper functions, validation strategies, and
  parameter-passing choices are acceptable when behavior and required
  interfaces are substantially correct.
- Students do not have to match the instructor reference's formatting,
  capitalization style for data members, or implementation order.
- A minor capitalization variation such as `getID()` instead of `getId()`
  should not lose points by itself when the required accessor is clearly
  present and the program remains compatible with the project.

## Supplied Main Program

- The assignment provided a substantially completed main program.
- Do not award significant authorship credit merely because supplied main
  logic is present.
- Students were allowed to modify main, but modifications should be judged
  only by whether the final program still satisfies the requirements.
- The exact original starter main file is included in the starter_files directory. Do not award authorship credit for unchanged starter code. Evaluate student changes only when they affect correctness, integration, or code quality.

## Comments and Privacy

- Source comments are not graded.
- Student comments are removed from the AI-facing copy for privacy.
- Do not deduct points because comments are absent from the AI-facing files.
- Evaluate readability using naming, organization, structure, and formatting.

## Output

- The output must contain the required car, engine, and steering information.
- Minor spacing, capitalization, blank-line, or punctuation differences should
  not lose points unless they make the output incorrect or difficult to read.
- The local execution result is stronger evidence than visual inference from
  source code.

## Validation and Exceptions

- Validation may be implemented differently from the reference solution.
- Constructors and setters should reject invalid negative numeric values where
  appropriate.
- A student should receive credit for correct validation behavior even when the
  implementation differs from the reference.
- Do not require validation that was not reasonably implied by the assignment.

## Evidence and Uncertainty

- Cite specific student files and lines when explaining a score.
- Do not infer code or behavior that is not present.
- Do not claim the program compiles or runs unless local compile/run evidence
  is supplied.
- Distinguish among missing work, incorrect work, and a valid alternative.
- Flag uncertain judgments for instructor review rather than inventing facts.

## Avoiding Double Penalties

- Score each rubric item independently.
- Apply global deductions only when supported by local objective evidence.
- Do not deduct twice for the same underlying defect unless it independently
  affects two clearly distinct rubric requirements.
