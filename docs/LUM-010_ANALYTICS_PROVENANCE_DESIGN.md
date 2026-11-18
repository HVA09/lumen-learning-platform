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

`GET /content/topics/{topic_id}/analytics?class_id={id}`

Authorization:

- **Teacher:** `class_id` is required; the class must exist and `ClassSection.teacher_user_id == current_user.id`. Otherwise return 403 (or 404 for a nonexistent class, consistent with existing class APIs).
- **Admin:** may omit `class_id` for institution-wide analytics, or provide a class ID for class-specific inspection.
- **Student/other roles:** denied by the existing teacher dependency.

Query scope:

- Teacher queries include only attempts with the requested `class_section_id`.
- Admin global queries include student-owned attempts only, including legacy NULL-provenance student attempts, as an aggregate only. For this global scope, deduplicate once per learner/question across all class contexts; do not count one learner once per class.
- Admin class queries include only student-owned attempts with the requested class ID.
- Do not join through current class enrollment to infer historical membership. The captured attempt context is the source of truth.
- Do not infer class from the student's current enrollment, assignment topic, teacher ownership of content, or the date of the attempt.
- A class's `ClassEnrollment` row is physically deleted when a student is removed. At attempt creation, validate that this row exists and that `ClassSection.is_archived == false`. The captured `QuizAttempt.class_section_id` remains the historical provenance after the student is later removed; do not re-check current enrollment when submitting or analyzing that already-created attempt.
- A deleted class will set `QuizAttempt.class_section_id` to NULL via `ON DELETE SET NULL`. Such attempts remain personal/unscoped for teacher queries and must not be reassigned to another class.

## 5. Small-cohort and inference protections

A class-scoped aggregate can still expose individual behavior when very few students answered a question. Apply a minimum cohort threshold per question.

**Recommended initial threshold: 5 distinct student accounts with at least one submitted answer to that question in the requested scope.**

To prevent a learner with many retries from dominating the aggregate, define the metric as follows:

- For teacher/class-scoped analytics, partition by `(class_section_id, topic_id, question_id, student_user_id)` and select only that student's latest submitted `QuestionResult` within the requested class by parent `QuizAttempt.submitted_at` (with attempt ID as a deterministic tie-breaker).
- For admin global analytics, partition by `(topic_id, question_id, student_user_id)` across **all** class and unscoped attempts; deliberately omit `class_section_id` from the partition. Select one latest result per learner/question globally so a learner active in multiple classes contributes only once to institution-wide totals.
- In both scopes, calculate `answered`, `correct`, and `success_rate` from the selected one-per-learner answers. `answered` is the distinct learner count, not the number of attempts.
- Calculate wrong-answer buckets from the same selected latest answer per learner; repeated retries must not increase a learner's contribution.
- Include only attempts belonging to student accounts (`UserRole.user`). Exclude `teacher` and `admin` attempts from both class and global student analytics. Admin global scope may include legacy NULL-provenance attempts only when their owning account is a student; retain them as aggregate-only records without inferring a class.
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
- Admin global aggregates may include historical NULL-provenance attempts only when `QuizAttempt.user_id` belongs to a student account (`UserRole.user`); deduplicate those attempts once per learner/question across the global population.
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
2. Add foreign key to `class_sections.id` with `ON DELETE SET NULL`.
3. Add an index.
4. Do not update existing rows.

Rollback:

- Stop new scoped-attempt writes before rollback.
- Take/verify a backup under the existing backup policy.
- Drop the index, foreign key, and column in the downgrade.
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
- Submission and `QuestionResult` creation preserve the parent attempt association.

### Analytics access

- Student receives 403.
- Teacher can query a class they own.
- Teacher cannot query another teacher's class.
- Teacher cannot omit `class_id` for global analytics.
- Admin can query institution-wide analytics and a selected class.
- Teacher results exclude NULL-provenance historical attempts.
- Class-scoped results exclude attempts from every other class.
- Deleted class references become NULL without deleting attempts.

### Suppression and privacy

- Cohort below 5 distinct learners sets `suppressed=true` and nulls counts, rates, and wrong-answer details.
- Cohort at/above 5 returns only question-level aggregates, based on one latest answer per learner/question.
- Wrong-answer buckets below 5 distinct learners are suppressed independently; do not fall back to exposing the next-smallest bucket.
- Multiple attempts by one learner count as one contribution per question in class scope; in admin global scope, a learner appearing in multiple classes contributes once per question using the latest submitted answer across all class contexts.
- Exclude teacher/admin-owned attempts from student analytics.
- Admin analytics requests require a supported purpose code and a successful audit write before data is returned.
- No student identity fields appear in the response.
- Existing analytics ordering and classification logic remains correct after scoping.

## 10. Delivery sequence

1. Approve this data contract and privacy threshold.
2. Implement model + migration + quiz-start validation + tests.
3. Implement scoped analytics API + authorization + suppression + tests.
4. Add student quiz-context selection and teacher/admin analytics scope UI.
5. Run full CI, Codex review, migration/restore checks, and post-merge verification.
6. Keep manual production acceptance and real backup/restore checks under the existing `DEFER-COMPUTER` policy where they require the user's computer.

**Non-goals:** no historical backfill, no student-level teacher reports, no assignment-to-quiz inference, no data deletion, and no production cutover in this design phase.
