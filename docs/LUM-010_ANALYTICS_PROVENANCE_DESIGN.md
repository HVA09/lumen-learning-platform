# LUM-010 — Student Analytics Provenance Design

**Status:** Design proposal; implementation not started  
**Baseline:** `main` after leaderboard authorization PR #171  
**Scope:** Question-level analytics exposed by `GET /content/topics/{topic_id}/analytics`

## 1. Problem statement

The current analytics endpoint aggregates `QuestionResult` rows by question. A result joins to `QuizAttempt`, which identifies the student and topic but does not identify the class context in which the attempt occurred.

The endpoint currently requires a teacher role but does not scope the aggregation to a class owned by that teacher. This is insufficient for the approved privacy policy:

- Students see only their own progress and results.
- A teacher sees analytics for classes they currently teach.
- A teacher who does not own a class cannot inspect that class's student performance.
- Admins may inspect institution-wide analytics for legitimate administrative purposes, subject to audit.
- Historical attempts without trustworthy class provenance must not be assigned to a class by inference.

## 2. Current data lineage

1. `POST /quiz/topics/{topic_id}/start` creates or resumes a `QuizAttempt`.
2. `POST /quiz/attempts/{attempt_id}/submit` stores the final result on `QuizAttempt` and creates one `QuestionResult` per question in the submitted attempt, including questions the learner left blank.
3. `GET /content/topics/{topic_id}/analytics` aggregates `QuestionResult` by question.

Relevant current fields:

- `QuizAttempt.user_id`: student identity.
- `QuizAttempt.topic_id`: topic identity.
- `QuizAttempt.mode`: practice or gateway.
- `QuizAttempt.submitted_at`: submission timestamp.
- `QuestionResult.quiz_attempt_id`: parent attempt.
- `QuestionResult.question_id`: question being analyzed.

Neither `QuizAttempt` nor `QuestionResult` currently carries a trustworthy class or assignment reference. `Assignment.class_section_id` belongs to the separate written-assignment workflow and must not be inferred from a matching topic.

## 3. Proposed provenance model

Add an optional `class_section_id` to `QuizAttempt`:

- Nullable foreign key to `class_sections.id`.
- Index for class-scoped analytics queries.
- `ON DELETE SET NULL` as the conservative deletion behavior: deleting a class must not delete a student's historical quiz attempt.
- The value is captured once when the attempt is created and is immutable after creation.

### Capture contract

Extend `QuizStartRequest` with optional `class_section_id`.

When supplied:

1. The authenticated account must be a student account (`UserRole.user`).
2. The class must exist and be active.
3. The student must have a current `ClassEnrollment` for that class at attempt creation time.
4. The server writes the validated class ID to the new `QuizAttempt`; it never trusts a client-supplied ID without this check.
5. If validation fails, reject the request without creating an attempt.

When omitted, the attempt is personal/unscoped and `class_section_id` remains NULL. Do not silently choose a class when a student belongs to multiple classes.

### Resume behavior

The current resume lookup selects the latest open attempt by `user_id + topic_id + mode`; it does not currently distinguish class context. Preserve that behavior deliberately, but make the context contract explicit:

- Add `class_section_id` to `QuizAttemptOut` so the client can display the stored context when an attempt resumes.
- If `class_section_id` is omitted from a resume request, resume the open attempt with its stored context and return that context; do not reinterpret omission as a request to move it to personal scope.
- If the request explicitly supplies a class ID or explicit `null` and it differs from the stored value, return `409 Conflict`. Do not mutate the attempt.
- Use Pydantic's supplied-fields tracking (or an equivalent explicit sentinel) to distinguish an omitted field from an explicitly supplied `null`.
- A newly created attempt with omitted or explicit `null` context is personal/unscoped.

Teacher/admin-created practice attempts must not be attributed to a student's class. If staff are permitted to use quiz routes, their attempts remain unscoped, and any supplied non-null class ID is rejected.

## 4. Analytics authorization and query contract

Change the endpoint to:

`GET /content/topics/{topic_id}/analytics?class_id={id}&purpose={purpose_code}` (the `purpose` parameter is required only for admin requests; teacher requests must not send or depend on it).

Authorization:

- **Teacher:** `class_id` is required; the class must exist and `ClassSection.teacher_user_id == current_user.id`. Otherwise return 403 (or 404 for a nonexistent class, consistent with existing class APIs).
- **Admin:** may omit `class_id` for institution-wide analytics, or provide a class ID for class-specific inspection.
- **Student/other roles:** denied by the existing teacher dependency.

Query scope:

- Teacher queries include only attempts with the requested `class_section_id`.
- Admin global queries include only attempts whose immutable `user_role_at_creation == UserRole.user`; attempts with unknown legacy role provenance are excluded. For this global scope, deduplicate once per learner/question across all class contexts; do not count one learner once per class.
- Admin class queries include only student-owned attempts with the requested class ID.
- Do not join through current class enrollment to infer historical membership. The captured attempt context is the source of truth.
- Do not infer class from the student's current enrollment, assignment topic, teacher ownership of content, or the date of the attempt.
- A class's `ClassEnrollment` row is physically deleted when a student is removed. At attempt creation, validate that this row exists and that `ClassSection.is_archived == false`. The captured `QuizAttempt.class_section_id` remains the historical provenance after the student is later removed; do not re-check current enrollment when submitting or analyzing that already-created attempt.
- A deleted class will set `QuizAttempt.class_section_id` to NULL via `ON DELETE SET NULL`. Such attempts remain personal/unscoped for teacher queries and must not be reassigned to another class.

## 5. Small-cohort and inference protections

A class-scoped aggregate can still expose individual behavior when very few students answered a question. Apply a minimum cohort threshold per question.

**Recommended initial threshold: 5 distinct student accounts with a submitted attempt containing that question in the requested scope.** A blank answer still contributes one learner to the denominator because the current submit path persists a `QuestionResult` row for it.

To prevent a learner with many retries from dominating the aggregate, define the metric as follows:

- For teacher/class-scoped analytics, partition by `(class_section_id, topic_id, question_id, student_user_id)` and select only that student's latest submitted `QuestionResult` within the requested class by parent `QuizAttempt.submitted_at` (with attempt ID as a deterministic tie-breaker).
- For admin global analytics, partition by `(topic_id, question_id, student_user_id)` across **all** class and unscoped attempts; deliberately omit `class_section_id` from the partition. Select one latest result per learner/question globally so a learner active in multiple classes contributes only once to institution-wide totals.
- In both scopes, calculate `answered`, `correct`, and `success_rate` from the selected one-per-learner answers. `answered` is the distinct learner count, not the number of attempts. Because blank answers remain in this denominator, the UI must label this value as learners/respondents (for example, «عدد الطلاب») rather than implying it is a count of non-empty answers.
- Calculate wrong-answer buckets from the same selected latest answer per learner; repeated retries must not increase a learner's contribution.
- Preserve the current question-type boundary: wrong-answer text buckets are supported only for `mcq` and `true_false` questions. For an unsuppressed `numeric` row, keep `top_wrong_answer` NULL and `top_wrong_count` zero in this phase; do not aggregate or expose arbitrary numeric/free-form answer values. If the respondent cohort is suppressed, `top_wrong_count` remains NULL under the general suppression rule.
- Include only attempts with immutable `user_role_at_creation == UserRole.user`. Exclude `teacher`, `admin`, and legacy attempts whose attempt-time role is unknown from both class and global student analytics. Never use the account's current role to infer the historical role.
- The current submit handler creates a `QuestionResult` row for every question in the submitted attempt, even when the learner omitted an answer (`given_answer == null`). Therefore the denominator represents distinct learners who submitted an attempt containing that question, not only learners who entered a non-empty answer. Treat a blank as not correct for the success-rate denominator, but never include blanks in wrong-answer buckets.

For rows below the threshold, use an explicit response contract:

- Add `suppressed: bool` to `QuestionAnalyticsOut`.
- When `suppressed == true`, set `answered`, `correct`, `success_rate`, and `top_wrong_count` to NULL; set `top_wrong_answer` to NULL; use a neutral `flag` value such as `insufficient_data` with a non-identifying label. Do not return the exact respondent count.
- When `suppressed == false`, `answered` is the distinct learner count and `correct` is the number of those learners whose latest answer was correct.
- Do not reveal a wrong-answer bucket unless that bucket independently contains at least 5 distinct learners. If the top bucket is below threshold, return no top wrong answer/count rather than exposing the next bucket as a potentially identifying residual. `top_wrong_count` counts distinct learners, not attempts.
- Keep the threshold centralized and documented, not duplicated across route/UI code.

Further protections:

- Teachers can query only whole classes they own; no arbitrary student lists or custom sub-cohorts.
- Do not add filters that allow repeated differencing of nearly identical populations.
- Do not expose student IDs, names, per-student scores, or attempt histories through this endpoint.
- Treat the threshold as a baseline suppression control, not a guarantee of anonymization. Reassess it if filters, exports, or additional analytics dimensions are introduced.

Admin access is governed by role and audit policy; admin-level aggregate visibility does not authorize exposing student-level details through this endpoint.

### Admin audit contract

The existing `AuditLog` model and `log_event(db, event_type, description, user_id)` helper can record this without adding a new audit table in this phase. Every successful admin analytics read (global or class-scoped) must write one event before returning the analytics response:

- `event_type`: `student_analytics_access`.
- `user_id`: the authenticated admin's user ID (actor).
- Require an enumerated `purpose` for admin reads (for example: `institutional_reporting`, `quality_review`, `support_case`, or `compliance`); do not accept free-form text that could accidentally store student personal data.
- `description`: include the topic ID, explicit scope (`global` or class ID), endpoint/action, purpose code, and that the response was aggregate-only. Do not include student IDs, names, raw answers, or result rows.
- Failed authorization attempts need not create a successful-access event; they may be logged separately under the existing security logging policy.
- Audit persistence is fail-closed: if the audit insert/commit fails, do not return the analytics payload. Roll back the session and return a generic service error (503); do not leak analytics data or raw DB errors.
- The audit event is committed before the response is returned. This makes the audit trail a prerequisite for admin data access, not a best-effort side effect.

Teacher class-scoped access continues to be restricted by class ownership. Do not expand this endpoint to student-level detail or add export functionality as part of this change.

## 6. Historical data policy

- Existing `QuizAttempt` rows receive NULL for the new field.
- No backfill based on current class membership, assignment topic, teacher, or timestamps.
- Teachers cannot see historical NULL-provenance attempts in class analytics.
- Historical attempts have unknown attempt-time role and are excluded from all student analytics, including admin global aggregates. Do not infer historical role from the account's current role or backfill it.
- Exclude historical attempts owned by teacher/admin accounts from student analytics.
- Do not fabricate class provenance to make historical charts appear complete.

## 7. Frontend behavior

At quiz start, students may optionally select the class context for the activity:

- Show only classes returned for the authenticated student's own enrollments.
- Include a clear personal/unassigned option.
- Do not silently attribute an activity to a class.
- If a student belongs to multiple classes, require an explicit choice to associate the attempt.
- If a student chooses no class, the attempt remains personal and is not included in teacher class analytics.
- Resume UI must preserve and display the original attempt context rather than offering to change it.

Teacher analytics UI must require a class selection from classes owned by that teacher. Admin UI may offer institution-wide or class-specific scope.

## 8. Migration and rollback plan

Migration:

1. Add nullable `quiz_attempts.class_section_id`.
2. Add nullable `quiz_attempts.user_role_at_creation` so existing rows can remain NULL/unknown without fabricated defaults. Enforce a non-null immutable role snapshot in the application transaction for every newly created attempt; reject any new attempt write that lacks it. Legacy NULL rows remain excluded from student analytics. Do not backfill by current role.
3. Add immutable submission-time question interpretation fields to `question_results` (at minimum question type and choices snapshot for choice questions, plus the grading/correct-answer snapshot needed to preserve correctness). Use the project's cross-database JSON type/serialization conventions; define exact shape and nullability in the implementation PR.
4. Add foreign key to `class_sections.id` with `ON DELETE SET NULL`.
5. Add an index.
6. Do not update existing rows; legacy role and choice provenance remains unknown.

Rollback:

- Stop new scoped-attempt writes before rollback.
- Take/verify a backup under the existing backup policy.
- Drop the index, foreign key, and every column introduced by this revision, including `class_section_id`, `user_role_at_creation`, and every question-result snapshot column. Verify the downgrade leaves no added schema objects behind.
- Recognize that dropping the column discards newly captured provenance; do not run a downgrade casually after production data has been written.

No migration should be merged until the schema, Alembic revision chain, PostgreSQL/SQLite behavior, deployment ordering, and rollback have been independently reviewed.

## 9. Required test matrix

### Attempt capture

- Student enrolled in class can start an attempt with that class ID.
- Student not enrolled in the class is rejected.
- Nonexistent or archived class is rejected.
- Student may start an unscoped personal attempt.
- Student in multiple classes can explicitly choose one.
- Teacher/admin cannot attribute their own attempts to a student's class.
- Resuming an attempt preserves the original class ID and cannot change it.
- Submission and `QuestionResult` creation preserve the parent attempt association and immutable question/choice interpretation snapshot.
- Student and staff role changes after attempt creation do not alter `user_role_at_creation` or analytics eligibility.
- Legacy attempts without role snapshots are excluded from student analytics.

### Analytics access

- Student receives 403.
- Teacher can query a class they own.
- Teacher cannot query another teacher's class.
- Teacher cannot omit `class_id` for global analytics.
- Admin can query institution-wide analytics and a selected class.
- Teacher results exclude NULL-provenance historical attempts.
- Class-scoped results exclude attempts from every other class.
- Deleted class references become NULL without deleting attempts.
- Admin global analytics count a student at most once per topic/question across multiple class and unscoped attempts, selecting that student's latest submitted result across all class contexts.
- Admin global analytics exclude all legacy attempts without trustworthy attempt-time role provenance, regardless of the account's current role.
- Class-scoped and global student analytics exclude staff-owned attempts.
- A blank `given_answer == null` contributes to the distinct-learner denominator and is treated as not-correct, but never appears in a wrong-answer bucket.

### Suppression and privacy

- Cohort below 5 distinct learners sets `suppressed=true` and nulls counts, rates, and wrong-answer details.
- Cohort at/above 5 returns only question-level aggregates, based on one latest answer per learner/question. If any answer bucket has 1–4 distinct learners, complementary suppression must also null `correct` and `success_rate` so the hidden bucket cannot be reconstructed by subtraction; apply the same rule to numeric questions with 1–4 incorrect learners.
- Wrong-answer buckets below 5 distinct learners are suppressed independently for `mcq` and `true_false`; do not fall back to exposing the next-smallest bucket. If any such bucket is 1–4, suppress correctness metrics as well. Numeric questions expose no wrong-answer bucket in this phase; suppress correctness metrics when 1–4 learners are incorrect.
- Multiple attempts by one learner count as one contribution per question in class scope; in admin global scope, a learner appearing in multiple classes contributes once per question using the latest submitted answer across all class contexts.
- The frontend labels the denominator as distinct learners/respondents, not non-empty answers.
- Exclude teacher/admin-owned attempts from student analytics.
- Admin analytics requests require a supported purpose code and a successful audit write before data is returned.
- Missing/unsupported admin purpose is rejected; audit insert/commit failure returns a generic 503 and never returns analytics data.
- No student identity fields appear in the response.
- Existing analytics ordering and classification logic remains correct after scoping.
- Editing/reordering question choices after submission does not change historical answer interpretation; legacy results without snapshots are excluded from choice-text buckets.
- Primary and complementary suppression payloads validate against nullable response schemas.

## 10. Delivery sequence

1. Approve this data contract and privacy threshold.
2. Implement model + migration + quiz-start validation + tests.
3. Implement scoped analytics API + authorization + suppression + tests.
4. Add student quiz-context selection and teacher/admin analytics scope UI.
5. Run full CI, Codex review, migration/restore checks, and post-merge verification.
6. Keep manual production acceptance and real backup/restore checks under the existing `DEFER-COMPUTER` policy where they require the user's computer.

**Non-goals:** no historical backfill, no student-level teacher reports, no assignment-to-quiz inference, no data deletion, and no production cutover in this design phase.

## 11. Mandatory clarifications from final privacy review

This section supersedes any earlier wording in this proposal that conflicts with it. These requirements are part of the design gate, not optional implementation notes.

### 11.1 Attempt-time role provenance

Add an immutable, non-null role snapshot for every newly created QuizAttempt, for example user_role_at_creation using the existing role enum/string contract.

- Capture the authenticated user's role in the same transaction that creates the attempt.
- Never update this snapshot when an administrator later promotes or demotes the account.
- Student analytics eligibility is based on user_role_at_creation == UserRole.user, not the account's current role.
- Staff attempts remain staff attempts even if the account is later demoted; student attempts remain student attempts if later promoted.
- Existing attempts have no trustworthy attempt-time role snapshot. Treat their role provenance as unknown and exclude them from student analytics, including admin global aggregates. Do not infer historical role from the current account role or fabricate a snapshot. If a separate immutable, auditable historical role record is later proven complete, that can be a separately reviewed migration proposal.

### 11.2 Immutable question/choice snapshot

At submission, persist the question interpretation needed to analyze the submitted answer, rather than resolving old answer indices against mutable current question data.

- Extend QuestionResult with an immutable snapshot sufficient to interpret the answer at submission, at minimum question_type_at_submission and choices_at_submission for choice-based questions. Store the correct-answer interpretation used for grading as well if it is not already recoverable immutably from the stored result.
- For MCQ/true-false wrong-answer buckets, interpret given_answer only against choices_at_submission, never the current Question.choices.
- Editing/reordering choices after submission must not change historical bucket labels or correctness.
- Legacy QuestionResult rows without a trustworthy snapshot must not be bucketed using current mutable question choices. Exclude them from choice-text bucket output; do not guess.
- The implementation design must define JSON shape, nullability for numeric/free-form types, and how question edits are versioned or snapshotted. Snapshot fields are write-once.

### 11.3 Complementary suppression for correctness metrics

Primary cohort suppression alone is insufficient. A visible answered and correct pair can reveal a wrong-answer bucket by subtraction even when that bucket is hidden.

- Keep the primary cohort gate: fewer than five distinct learners suppresses the entire row and returns no exact respondent count.
- For an otherwise eligible cohort, calculate the distinct-learner counts for every answer bucket from the one-latest-answer-per-learner set.
- If any answer bucket has between one and four distinct learners, apply complementary suppression to the correctness metrics: set correct and success_rate to NULL and set correctness_suppressed=true. Do not return another metric from which the hidden count can be derived.
- Do not reveal a small bucket's label or count. Do not reveal the next-largest bucket as a replacement.
- If all answer buckets meet the threshold, correct and success_rate may be returned.
- For numeric questions, where arbitrary answer buckets are not emitted, if the number of incorrect learners is between one and four, suppress correct and success_rate in the same way. This prevents deriving the small incorrect cohort from answered - correct.
- Define correctness_suppressed: bool in the response contract. When true, correct and success_rate must be nullable and NULL. The primary suppressed flag remains reserved for the entire row being below the cohort threshold.
- Keep answered only when the primary cohort is unsuppressed; never combine it with a visible correctness count when complementary suppression is active.

### 11.4 Response schema nullability

The implementation must update QuestionAnalyticsOut and any nested response models before returning suppressed values.

- answered: int | null
- correct: int | null
- success_rate: float | null
- top_wrong_count: int | null
- top_wrong_answer: str | null
- suppressed: bool
- correctness_suppressed: bool

For a primary-suppressed row, all count/rate/bucket fields are NULL. For complementary suppression, answered may remain visible but correct and success_rate are NULL. Add response-model tests for both cases so Pydantic validation cannot reject the privacy-preserving response.

### 11.5 Updated legacy eligibility rule

The earlier statement that admin global analytics may include legacy NULL-provenance attempts when the owner's current role is student is superseded. Legacy attempts without attempt-time role provenance are excluded from all student analytics. This avoids role-change history being retroactively reinterpreted. No role or class provenance backfill is allowed by inference.

### 11.6 Additional required tests

- Create a student attempt, promote the account to teacher/admin, and verify the attempt remains student-originated for analytics.
- Create a teacher/admin attempt, demote the account to student, and verify it remains excluded from student analytics.
- Verify legacy attempts with unknown attempt-time role are excluded even if the current account role is student.
- Submit an MCQ/true-false answer, edit/reorder the question choices, and verify the historical bucket uses the stored submission snapshot.
- Verify legacy results without a choice snapshot do not use current choices to create wrong-answer labels.
- Verify a cohort of five with a 4/1 answer split hides correctness metrics and does not expose the minority bucket.
- Verify numeric cohorts with one to four incorrect learners hide correct and success_rate.
- Verify primary and complementary suppression responses pass the nullable Pydantic response schema.

### 11.7 Question-definition versioning, audit transport, and migration nullability

These clarifications close the remaining design ambiguities and supersede any shorter wording above.

**Question-definition versioning**
- A submission-time snapshot must preserve the exact analytics-relevant question definition shown to the learner, not just its current database ID or choice list.
- At minimum, persist immutable `question_prompt_at_submission`, `question_type_at_submission`, `question_difficulty_at_submission`, `choices_at_submission` (for choice questions), and the grading/correct-answer interpretation actually used by the submit handler.
- Persist a stable `question_definition_version` (or an equivalent deterministic snapshot identity) with each `QuestionResult`. A change to prompt, question type, difficulty, choices, or grading interpretation creates a new definition version for analytics purposes.
- Analytics must group and return separate rows per `(question_id, question_definition_version)`; never combine historical answers to materially different question definitions under the current prompt.
- Snapshot fields are write-once. Editing a question after submission must not rewrite previous `QuestionResult` snapshots.
- Legacy results without a trustworthy definition snapshot are excluded from version-specific choice buckets and must not be attributed to the current definition by inference. The implementation PR must define the exact JSON shape, version-generation rule, nullability for numeric/free-form questions, and deterministic handling of grading changes.

**Admin audit-purpose transport**
- Admin requests must provide the enumerated purpose as the `purpose` query parameter shown in the endpoint contract: `institutional_reporting`, `quality_review`, `support_case`, or `compliance`.
- Missing or unsupported `purpose` on an admin request is rejected before aggregation. Teacher requests remain class-scoped and do not use admin purpose codes.
- The purpose is a constrained enum, not arbitrary text. The audit record stores the accepted code and the explicit global/class scope; it never stores free-form student data.
- Tests must cover each supported purpose, missing purpose, unsupported purpose, and audit-write failure. A failed audit write must return generic 503 without returning analytics data.

**Role snapshot migration compatibility**
- The database column is nullable to preserve the unknown state of pre-migration attempts. Application-level creation logic requires and writes a non-null role snapshot atomically for every new attempt.
- No database default may infer a role for legacy records. No current-role backfill is permitted.
- Migration tests must prove existing rows remain NULL and new attempt writes cannot omit the snapshot.

**Complementary suppression output completeness**
- If any answer bucket has 1–4 learners, set `correct` and `success_rate` to NULL and `correctness_suppressed=true`.
- Also set `top_wrong_answer` and `top_wrong_count` to NULL and suppress any correctness-derived `flag` or label. Do not expose a top bucket, even if that top bucket itself has five or more learners, when a complementary bucket is small and could be derived from the displayed denominator.
- `answered` may remain visible only as the distinct respondent count; it must not be paired with any visible correctness or bucket metric that enables subtraction. For numeric questions with 1–4 incorrect learners, apply the same rule.
- The API response schema and UI must treat these nullable fields as intentional suppression, not as zero or as a missing-data error.

**Rollback completeness**
- The downgrade must explicitly remove every schema object introduced by the migration revision: all new columns, indexes, and foreign keys across both `quiz_attempts` and `question_results`. Add a migration test that upgrades, downgrades, and confirms the schema exactly matches the pre-upgrade shape.