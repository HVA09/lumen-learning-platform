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
2. `POST /quiz/attempts/{attempt_id}/submit` stores the final result on `QuizAttempt` and creates one `QuestionResult` per answered question.
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

An unfinished attempt retains its original class context. Resuming an attempt must not overwrite or backfill its `class_section_id`. If a resume request supplies a different class context, reject it with a conflict or return the existing context explicitly; do not silently move the attempt between classes.

Teacher/admin-created practice attempts must not be attributed to a student's class. If staff are permitted to use quiz routes, their attempts remain unscoped.

## 4. Analytics authorization and query contract

Change the endpoint to:

`GET /content/topics/{topic_id}/analytics?class_id={id}`

Authorization:

- **Teacher:** `class_id` is required; the class must exist and `ClassSection.teacher_user_id == current_user.id`. Otherwise return 403 (or 404 for a nonexistent class, consistent with existing class APIs).
- **Admin:** may omit `class_id` for institution-wide analytics, or provide a class ID for class-specific inspection.
- **Student/other roles:** denied by the existing teacher dependency.

Query scope:

- Teacher queries include only attempts with the requested `class_section_id`.
- Admin global queries may include all attempts, including legacy NULL-provenance attempts, as an aggregate only.
- Admin class queries include only the requested class.
- Do not join through current class enrollment to infer historical membership. The captured attempt context is the source of truth.
- Do not infer class from the student's current enrollment, assignment topic, teacher ownership of content, or the date of the attempt.

## 5. Small-cohort and inference protections

A class-scoped aggregate can still expose individual behavior when very few students answered a question. Apply a minimum cohort threshold per question.

**Recommended initial threshold: 5 distinct student accounts with at least one submitted answer to that question in the requested scope.**

For rows below the threshold:

- Return a suppression state, not the exact respondent count.
- Do not return success rate, correct count, or most-common wrong answer.
- Do not reveal small wrong-answer buckets; suppress the top wrong answer unless its count also meets the threshold.
- Keep the threshold centralized and documented, not duplicated across route/UI code.

Further protections:

- Teachers can query only whole classes they own; no arbitrary student lists or custom sub-cohorts.
- Do not add filters that allow repeated differencing of nearly identical populations.
- Do not expose student IDs, names, per-student scores, or attempt histories through this endpoint.
- Treat the threshold as a baseline suppression control, not a guarantee of anonymization. Reassess it if filters, exports, or additional analytics dimensions are introduced.

Admin access is governed by role and audit policy; admin-level aggregate visibility does not authorize exposing student-level details through this endpoint.

## 6. Historical data policy

- Existing `QuizAttempt` rows receive NULL for the new field.
- No backfill based on current class membership, assignment topic, teacher, or timestamps.
- Teachers cannot see historical NULL-provenance attempts in class analytics.
- Admins may see historical records only as institution-wide aggregates under the admin policy.
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

- Cohort below 5 suppresses counts, rates, and wrong-answer details.
- Cohort at/above 5 returns only question-level aggregates.
- Small top-wrong-answer buckets are suppressed independently.
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
