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

`GET /content/topics/{topic_id}/analytics?class_id={id}&purpose={purpose_code}`. Teachers must provide `class_id`; admins must omit `class_id` and receive institution-wide aggregates only. The `purpose` parameter is required only for admin requests; teacher requests must not send or depend on it.

Authorization:

- **Teacher:** `class_id` is required; the class must exist and `ClassSection.teacher_user_id == current_user.id`. Otherwise return 403 (or 404 for a nonexistent class, consistent with existing class APIs).
- **Admin:** must omit `class_id`; this endpoint provides institution-wide aggregates only. Reject admin requests containing `class_id`. Admin class-level releases are deferred until a separately reviewed cross-scope disclosure-control design exists.
- **Student/other roles:** denied by the existing teacher dependency.

Query scope:

- Teacher queries include only attempts with the requested `class_section_id`.
- Admin global queries include only attempts whose immutable `user_role_at_creation == UserRole.user`; attempts with unknown legacy role provenance are excluded. Deduplicate once per learner/question/question-definition-version across all class and unscoped contexts; do not count one learner once per class.
- Admin class-scoped queries are not supported by this endpoint. This avoids differencing a global aggregate against a class aggregate to reconstruct a small residual cohort.
- Do not join through current class enrollment to infer historical membership. The captured attempt context is the source of truth.
- Do not infer class from the student's current enrollment, assignment topic, teacher ownership of content, or the date of the attempt.
- A class's `ClassEnrollment` row is physically deleted when a student is removed. At attempt creation, validate that this row exists and that `ClassSection.is_archived == false`. The captured `QuizAttempt.class_section_id` remains the historical provenance after the student is later removed; do not re-check current enrollment when submitting or analyzing that already-created attempt.
- A deleted class will set `QuizAttempt.class_section_id` to NULL via `ON DELETE SET NULL`. Such attempts remain personal/unscoped for teacher queries and must not be reassigned to another class.

## 5. Small-cohort and inference protections

A class-scoped aggregate can still expose individual behavior when very few students answered a question. Apply a minimum cohort threshold per question.

**Recommended initial threshold: 5 distinct student accounts with a submitted attempt containing that question in the requested scope.** A blank answer still contributes one learner to the denominator because the current submit path persists a `QuestionResult` row for it.

To prevent a learner with many retries from dominating the aggregate, define the metric as follows:

- For teacher/class-scoped analytics, partition by `(class_section_id, topic_id, question_id, question_definition_version, student_user_id)` and select only that student's latest submitted `QuestionResult` within the requested class and definition version by parent `QuizAttempt.submitted_at` (with attempt ID as a deterministic tie-breaker).
- For admin global analytics, partition by `(topic_id, question_id, question_definition_version, student_user_id)` across **all** class and unscoped attempts; deliberately omit `class_section_id` from the partition. Select one latest result per learner/question/definition-version globally so a learner active in multiple classes contributes only once to each institution-wide definition-version total.
- In both scopes, calculate `answered`, `correct`, and `success_rate` from the selected one-per-learner answers. `answered` is the distinct learner count, not the number of attempts. Because blank answers remain in this denominator, the UI must label this value as learners/respondents (for example, «عدد الطلاب») rather than implying it is a count of non-empty answers.
- Calculate wrong-answer buckets from the same selected latest answer per learner and definition version; repeated retries must not increase a learner's contribution. For complementary-suppression analysis, count blank/omitted answers as a separate hidden answer category even though blanks are never emitted as wrong-answer text buckets.
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
- Do not add filters that allow repeated differencing of nearly identical populations. Admins receive only the institution-wide scope from this endpoint; do not expose a simultaneous class-level aggregate that can be subtracted from the global row. Any future admin class-level reporting requires a separately reviewed release-control design that prevents differencing across all permitted scopes.
- Do not expose student IDs, names, per-student scores, or attempt histories through this endpoint.
- Treat the threshold as a baseline suppression control, not a guarantee of anonymization. Reassess it if filters, exports, or additional analytics dimensions are introduced.

Admin access is governed by role and audit policy; admin-level aggregate visibility does not authorize exposing student-level details through this endpoint.

### Admin audit contract

The existing `AuditLog` model and `log_event(db, event_type, description, user_id)` helper can record this without adding a new audit table in this phase. Every successful admin institution-wide analytics read must write one event before returning the analytics response:

- `event_type`: `student_analytics_access`.
- `user_id`: the authenticated admin's user ID (actor).
- Require an enumerated `purpose` for admin reads (for example: `institutional_reporting`, `quality_review`, `support_case`, or `compliance`); do not accept free-form text that could accidentally store student personal data.
- `description`: include the topic ID, explicit `global` scope, endpoint/action, purpose code, and that the response was aggregate-only. Do not include student IDs, names, raw answers, or result rows.
- Failed authorization attempts need not create a successful-access event; they may be logged separately under the existing security logging policy.
- Audit persistence is fail-closed: if the audit insert/commit fails, do not return the analytics payload. Roll back the session and return a generic service error (503); do not leak analytics data or raw DB errors.
- The audit event is committed before the response is returned. This makes the audit trail a prerequisite for admin data access, not a best-effort side effect.

Teacher class-scoped access continues to be restricted by class ownership. Do not expand this endpoint to student-level detail or add export functionality as part of this change.

## 6. Historical data policy

- Existing `QuizAttempt` rows receive NULL for the new class/role provenance and question-definition snapshot fields. Do not infer or backfill them from current state.
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

Teacher analytics UI must require a class selection from classes owned by that teacher. Admin UI offers institution-wide aggregate scope only; do not provide class selection on this endpoint.

## 8. Migration and rollback plan

Migration:

1. Add nullable `quiz_attempts.class_section_id`.
2. Add nullable `quiz_attempts.user_role_at_creation` so existing rows can remain NULL/unknown without fabricated defaults. Enforce a non-null immutable role snapshot in the application transaction for every newly created attempt; reject any new attempt write that lacks it. Legacy NULL rows remain excluded from student analytics. Do not backfill by current role.
3. Add nullable `quiz_attempts.question_definition_snapshots` JSON for immutable per-question definitions captured when the attempt's question set is first presented. Legacy attempts remain NULL and must not be silently snapshotted from current mutable questions.
4. Add immutable attempt-presentation snapshot fields to `question_results`, including `question_definition_version`, prompt, type, difficulty, choices, and grading/correct-answer interpretation copied from the parent attempt snapshot at submission. Use the project's cross-database JSON conventions.
5. Add foreign key to `class_sections.id` with `ON DELETE SET NULL`.
6. Add indexes for the new version/provenance query paths.
6. Do not update existing rows; legacy role and choice provenance remains unknown.

Rollback:

- Stop new scoped-attempt writes and attempt-snapshot writes before rollback.
- Take/verify a backup under the existing backup policy.
- Drop the index, foreign key, and every column introduced by this revision, including `class_section_id`, `user_role_at_creation`, `question_definition_snapshots`, and every question-result snapshot/version column. Verify the downgrade leaves no added schema objects behind.
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
- The first presentation of an attempt captures an immutable question-definition snapshot; resume returns that same snapshot and submission grades against it.
- Submission and `QuestionResult` creation preserve the parent attempt association and copy the exact attempt-time definition snapshot and version.
- Student and staff role changes after attempt creation do not alter `user_role_at_creation` or analytics eligibility.
- Legacy attempts without role snapshots are excluded from student analytics.

### Analytics access

- Student receives 403.
- Teacher can query a class they own.
- Teacher cannot query another teacher's class.
- Teacher cannot omit `class_id` for global analytics.
- Admin can query institution-wide analytics only; a request containing `class_id` is rejected.
- Teacher results exclude NULL-provenance historical attempts.
- Class-scoped results exclude attempts from every other class.
- Deleted class references become NULL without deleting attempts.
- Admin global analytics count a student at most once per topic/question/definition-version across multiple class and unscoped attempts, selecting that student's latest submitted result for that definition version across all class contexts.
- Admin global analytics exclude all legacy attempts without trustworthy attempt-time role provenance, regardless of the account's current role.
- Class-scoped and global student analytics exclude staff-owned attempts.
- A blank `given_answer == null` contributes to the distinct-learner denominator and is treated as not-correct, but never appears in a wrong-answer bucket.

### Suppression and privacy

- Cohort below 5 distinct learners sets `suppressed=true` and nulls counts, rates, and wrong-answer details.
- Cohort at/above 5 returns only question-level aggregates, based on one latest answer per learner/question-definition-version. Treat blanks as a separate hidden bucket for complementary suppression: if any non-blank answer bucket, blank bucket, or numeric incorrect bucket has 1–4 distinct learners, complementary suppression must null `correct` and `success_rate` and all correctness-derived/bucket fields so the hidden category cannot be reconstructed by subtraction.
- Wrong-answer buckets below 5 distinct learners are suppressed independently for `mcq` and `true_false`; do not fall back to exposing the next-smallest bucket. If any such bucket is 1–4, suppress correctness metrics as well. Numeric questions expose no wrong-answer bucket in this phase; suppress correctness metrics when 1–4 learners are incorrect.
- Multiple attempts by one learner count as one contribution per question-definition-version in class scope; in admin global scope, a learner appearing in multiple classes contributes once per question-definition-version using the latest submitted answer within that version across all class contexts.
- The frontend labels the denominator as distinct learners/respondents, not non-empty answers.
- Exclude teacher/admin-owned attempts from student analytics.
- Admin institution-wide analytics requests require a supported purpose code and a successful audit write before data is returned; admin class-scoped requests are rejected by this endpoint.
- Missing/unsupported admin purpose is rejected; audit insert/commit failure returns a generic 503 and never returns analytics data.
- No student identity fields appear in the response.
- Existing analytics ordering and classification logic remains correct after scoping.
- Editing/reordering question definitions after an attempt starts does not change the definition shown or grading used for that attempt; legacy attempts/results without trustworthy presentation snapshots are not reinterpreted using current question data.
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

### 11.2 Immutable question-definition snapshot at presentation time

A submission-time snapshot alone is too late: the current quiz flow can reload a mutable question after the attempt starts or resumes. A question may be edited between presentation and submission, causing the learner's answer to be graded or labelled against a definition they never saw.

- When a quiz attempt's question set is first assembled and presented, capture an immutable question_definition_snapshots object on that QuizAttempt, keyed by stable question ID. Each entry preserves the exact prompt, type, difficulty, choices, and grading/correct-answer interpretation presented to the learner.
- Compute a stable question_definition_version for each entry from a canonical representation of those analytics-relevant fields (for example, a SHA-256 fingerprint). Any change to prompt, type, difficulty, choices, or grading interpretation produces a different version.
- The attempt snapshot is write-once. Resume responses must return the stored snapshot and render it; they must not reload current mutable question definitions for an already-started attempt.
- Submission must grade against the attempt's stored snapshot, not the current Question row. Copy the same snapshot fields and question_definition_version into each resulting QuestionResult so analytics can group and label the exact definition the learner saw.
- A question edit after attempt creation affects only newly created attempts. It must not rewrite an open attempt's snapshot or historical QuestionResult records.
- Legacy open attempts without a trustworthy presentation snapshot cannot be safely resumed against current mutable questions. Close/expire them through an explicit compatibility path and ask the learner to start a new attempt; do not silently attach the current definition.
- Legacy submitted results without a trustworthy snapshot/version are excluded from definition-version-specific analytics and choice-text buckets. Do not infer the definition from current question data.
- The implementation PR must define the exact JSON schema, canonicalization rules for the version fingerprint, nullability for numeric/free-form questions, and transaction boundaries for snapshot creation, resume, and submission.

QuestionResult remains the analytics fact row, but its immutable interpretation is inherited from the attempt-time presentation snapshot rather than reconstructed at submission.
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

**Question-definition versioning and response identity**
- Capture the full question definition when the attempt is first presented, as specified in section 11.2, and preserve it on the attempt across resume and submission.
- Persist a stable question_definition_version with each QuestionResult; this value identifies the exact prompt/type/difficulty/choices/grading definition shown to the learner.
- Include question_definition_version in every QuestionAnalyticsOut row. Clients must use (question_id, question_definition_version) as the stable row identity/key; two aggregates for different definitions must never be merged or displayed as if they represented the same question version.
- Deduplicate retries independently within each definition version. The teacher partition key is (class_section_id, topic_id, question_id, question_definition_version, student_user_id); the admin global partition key is (topic_id, question_id, question_definition_version, student_user_id).
- A later retry under definition B does not replace that learner's earlier contribution under definition A. Each definition-version aggregate uses that learner's latest submitted answer within that same version.
- A question edit after attempt start does not change the definition shown or grading used by that attempt. New attempts capture the updated definition and therefore a different version fingerprint.
- Legacy attempts/results without a trustworthy presentation snapshot/version are excluded from version-specific analytics. The implementation PR must define the exact JSON shape and canonical fingerprint algorithm; snapshot fields are write-once.
**Admin audit-purpose transport**
- Admin institution-wide requests must provide the enumerated purpose as the `purpose` query parameter shown in the endpoint contract: `institutional_reporting`, `quality_review`, `support_case`, or `compliance`.
- Missing or unsupported `purpose` on an admin request is rejected before aggregation. Teacher requests remain class-scoped and do not use admin purpose codes.
- Admin class-scoped requests are rejected by this endpoint; allowing global and class-specific releases together would enable differencing attacks against small residual cohorts.
- The purpose is a constrained enum, not arbitrary text. The audit record stores the accepted code and explicit global scope; it never stores free-form student data.
- Tests must cover each supported purpose, missing purpose, unsupported purpose, and audit-write failure. A failed audit write must return generic 503 without returning analytics data.

**Role snapshot migration compatibility**
- The database column is nullable to preserve the unknown state of pre-migration attempts. Application-level creation logic requires and writes a non-null role snapshot atomically for every new attempt.
- No database default may infer a role for legacy records. No current-role backfill is permitted.
- Migration tests must prove existing rows remain NULL and new attempt writes cannot omit the role or presentation snapshot.

**Complementary suppression output completeness**
- If any answer bucket has 1–4 learners, set `correct` and `success_rate` to NULL and `correctness_suppressed=true`.
- Also set `top_wrong_answer` and `top_wrong_count` to NULL and suppress any correctness-derived `flag` or label. Do not expose a top bucket, even if that top bucket itself has five or more learners, when a complementary bucket is small and could be derived from the displayed denominator.
- `answered` may remain visible only as the distinct respondent count; it must not be paired with any visible correctness or bucket metric that enables subtraction. For numeric questions with 1–4 incorrect learners, apply the same rule.
- The API response schema and UI must treat these nullable fields as intentional suppression, not as zero or as a missing-data error.

**Rollback completeness**
- The downgrade must explicitly remove every schema object introduced by the migration revision: all new columns, indexes, and foreign keys across both `quiz_attempts` and `question_results`. Add a migration test that upgrades, downgrades, and confirms the schema exactly matches the pre-upgrade shape.
### 11.8 Final exact-head review clarifications

These controls address the remaining review findings on the current design head and are mandatory for implementation.

**Blank-answer complementary suppression**
- Treat omitted/blank answers as a distinct internal answer category when evaluating every answer-bucket size for complementary suppression.
- A blank category is never returned as a wrong-answer label or count. However, if 1–4 distinct learners are blank, set correct and success_rate to NULL, set correctness_suppressed=true, and null top_wrong_answer, top_wrong_count, and any correctness-derived flag/label.
- This applies even when all non-blank answer buckets contain at least five learners. For example, a six-learner cohort with five correct answers and one blank must not expose answered=6 alongside correct=5.
- The answered field may remain visible only when all correctness-derived and answer-bucket fields are suppressed; it represents distinct respondents, including blanks.

**Definition snapshot timing and grading**
- The definition snapshot is captured when the attempt's question set is first presented, not at submission.
- Resume must display the stored attempt snapshot. Submission must grade against that same stored snapshot.
- If a question changes after attempt start, the open attempt continues using the original snapshot; only newly created attempts use the new definition.
- Tests must edit prompt/type/difficulty/choices/grading after attempt creation but before resume/submission and prove that the original displayed definition and grading interpretation remain in force.

**Version-aware retry deduplication and response schema**
- Include question_definition_version in the retry partition key for both teacher class-scoped and admin global aggregates.
- A learner's latest answer under version B must not erase their contribution under version A.
- Add question_definition_version to QuestionAnalyticsOut and require the frontend to key each analytics row by (question_id, question_definition_version).
- Test retries across two versions, including a case where the learner's version-A contribution remains present after a later version-B submission.

**Admin cross-scope differencing**
- This endpoint supports teacher-owned class scope and admin institution-wide scope only. Admins must omit class_id; reject admin requests that provide it.
- Do not expose both global and class-specific aggregate releases from this endpoint. A global total minus a visible class total can reveal a small residual cohort even when each displayed row independently meets the threshold.
- Admin class-level reporting is deferred until a separate privacy design defines and tests cross-scope release controls against differencing across all permitted cohorts and query combinations. Audit purpose codes alone are not a disclosure-control mechanism.

**Required additional tests**
- A cohort of six with five correct answers and one blank triggers complementary suppression and does not expose the one-person omission through answered, correct, success_rate, top-wrong fields, or flags.
- A question edited after attempt start is still rendered and graded using the attempt-time snapshot on resume and submission.
- A learner with a result under definition A and a later retry under definition B contributes once to each version-specific aggregate; B does not replace A.
- Every analytics response row includes question_definition_version, and the UI row key includes both question ID and version.
- Admin global analytics work with a supported purpose; admin requests with class_id are rejected, preventing global/class differencing through this endpoint.
