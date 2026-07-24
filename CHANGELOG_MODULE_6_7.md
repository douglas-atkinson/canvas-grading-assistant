# Module 6/7 Targeted Update

This update implements the four changes identified after the first OpenAI
baseline run:

1. Local compile and optional run evidence before model evaluation.
2. `requires_local_evidence` instead of uncertainty-based numeric deductions.
3. An explicit rule that missing evidence never causes a deduction.
4. Explicit protection for comment-removal whitespace and unchanged starter
   code during readability evaluation.

Additional safeguards:

- Existing Module 7 baseline runs survive Module 6 `--overwrite`.
- Student execution requires an explicit flag and has a hard timeout.
- Module 7 validates rubric identities, maxima, status/score consistency, and
  evidence line references after schema validation.
