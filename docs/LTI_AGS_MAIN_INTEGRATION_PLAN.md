# LTI AGS integration plan from current main

Status: integration preparation only; no LTI application code or database migration has been ported yet.

## Starting point

- Repository: `HVA09/lumen-learning-platform`
- Integration branch: `feat/lti-ags-integration-main-20261120`
- Branch base: `main` at `7240b77f706adc6706b14b0163809e244d46a965`
- Legacy source PR: [#154](https://github.com/HVA09/lumen-learning-platform/pull/154)
- Legacy source branch: `feat/lti-ags-rebased-20261115`
- The source branch is 46 commits ahead and 14 behind current main, with a 31-file diff. Do not merge or force-update it as the integration target.

## Blocking integration findings

### Alembic graph

Current main contains:

- `0023_content_ownership` revising `0022_auth_sessions`.

The legacy LTI branch contains:

- `0023_lti_ags_grade_passback` also revising `0022_auth_sessions`.
- `0024_lti_resource_discovery` revising the LTI grade-passback revision.
- `0025_lti_ags_delivery_order` revising resource discovery.
- `0026_lti_submission_subject` revising delivery order.
- `0027_lti_ags_delivery_lease` revising submission subject.
- `0028_lti_ags_manual_retry_authorization.py` whose module revision value is `0028_lti_ags_manual_retry`, not the filename/header identifier.

Required proposed linear sequence after main's ownership migration:

1. `0024_lti_ags_grade_passback` → `0023_content_ownership`
2. `0025_lti_resource_discovery` → `0024_lti_ags_grade_passback`
3. `0026_lti_ags_delivery_order` → `0025_lti_resource_discovery`
4. `0027_lti_submission_subject` → `0026_lti_ags_delivery_order`
5. `0028_lti_ags_delivery_lease` → `0027_lti_submission_subject`
6. `0029_lti_ags_manual_retry` → `0028_lti_ags_delivery_lease`

This is a proposed graph only. Before editing, inspect every migration's full upgrade/downgrade body and all references to revision IDs. Update each filename, docstring, `revision`, and `down_revision` consistently. Do not run migrations during this integration work.

### Assignment authorization

Current main's `backend/app/routers/assignments.py` rejects non-student roles in `submit_assignment` before creating or updating a submission:

```python
if current_user.role != UserRole.user:
    raise HTTPException(status_code=403, ...)
```

The legacy PR implementation adds LTI context mapping but omits this guard. Port only the LTI-specific additions onto the current main implementation. Preserve assignment ownership/visibility checks and the student-only guard.

Required regression coverage:

- teacher submission attempt returns 403 and creates no submission or grade event;
- admin submission attempt returns 403 and creates no submission or grade event;
- eligible student with verified LTI context can submit and binds only to the matching platform/deployment/resource-link mapping;
- normal non-LTI student submission continues to work;
- unrelated or unverified LTI context creates no grade event;
- assignment owner/manageability and enrollment checks remain enforced.

## Porting sequence

1. Reconcile the complete LTI model/schema/service/router/task/frontend diff against current main; do not copy whole legacy files over main.
2. Port models and relationships, then services and router changes, preserving current main behavior.
3. Re-chain migrations using the proposed sequence, after verifying all migration bodies and constraints.
4. Port tests and add the authorization and no-side-effect regression cases above.
5. Port frontend administration UI/API helpers only after backend contracts are stable.
6. Run Alembic graph validation (one intended head), clean-database upgrade, populated-database upgrade, downgrade/upgrade, `alembic check`, backend/frontend suites, browser E2E, and secret scan on the exact integration head.
7. Keep Moodle Sandbox and Canvas Sandbox as separate release gates: OIDC launch, verified target binding, grade passback, re-grade ordering, retry/failure behavior, and evidence capture.
8. Request independent review before changing the legacy PR's status or proposing merge.

## Safety boundaries

- No migration execution, production database access, LMS configuration, secrets, deployment, or data changes.
- Keep PR #154 open and Draft as historical source until the new integration branch is reviewed and tested.
- Do not claim Moodle/Canvas compatibility from unit tests or CI alone.
- Do not merge this branch until all code, migration, authorization, CI, independent-review, and sandbox gates are satisfied.


## Verified model and migration dependency map (20 Nov 2026)

A source-to-main comparison confirms that `backend/app/models/lti.py` cannot be ported as an isolated file:

- The LTI model defines `LTIAssignmentLink`, `LTIResourceLinkDiscovery`, `LTIAGSGradeEvent`, and `LTIAGSDeliveryLease`, which are not exported by current main's `models/__init__.py`.
- The source `AssignmentSubmission` adds `grade_version`, `lti_assignment_link_id`, `lti_subject`, and a relationship to `LTIAssignmentLink`; current main's model does not contain these fields.
- The source `AuthSession` adds `lti_platform_id`, `lti_deployment_id`, `lti_resource_link_id`, and `lti_subject`; current main's model does not contain these fields.
- The source `LTIAuthCode` adds platform, deployment, resource-link, and subject context fields. These are coupled to the LTI launch/session flow and must be checked against the existing main schema before porting.
- The source model export list adds the four AGS/resource-discovery classes; importing only the new LTI file without coordinated model and schema changes is incomplete.

### Migration body observations

The six source migrations were inspected, not just their headers:

- The first AGS migration adds `assignment_submissions.grade_version`, creates `lti_assignment_links` and `lti_ags_grade_events`, and includes the initial status constraint `pending/sent/dead`.
- Resource discovery adds LTI context columns to `lti_auth_codes` and `auth_sessions`, adds `assignment_submissions.lti_assignment_link_id`, and creates `lti_resource_link_discoveries`.
- Delivery ordering adds/backfills `score_timestamp` from `created_at`, then makes it non-null with a server default, and expands the event status constraint to include `superseded`.
- Submission subject adds `lti_subject` to auth codes, sessions, and submissions.
- Delivery lease creates the unique per-assignment-link/subject-hash lease table and its expiry index.
- Manual retry adds `manual_retry_requested_at`; its filename and docstring say `0028_lti_ags_manual_retry_authorization` while its actual Python `revision` is `0028_lti_ags_manual_retry`.

### Integration implication

Porting must be treated as one coordinated schema/model/service/API/test change set. In particular, do not expose the AGS event model until all columns and constraints expected by the model exist in the re-chained migrations. Validate both a clean database and a populated database after the graph is re-chained. The proposed revision sequence above remains provisional until full graph inspection confirms all parent references and the repository's expected Alembic head behavior.


## Current-main LTI baseline discovered (20 Nov 2026)

A further live inspection corrected the integration scope: current `main` already contains a working LTI 1.3/OIDC foundation. It is not necessary or safe to port the entire legacy LTI implementation over main.

Verified current-main files:

- `backend/app/main.py` imports and mounts `app.routers.lti`.
- `backend/app/routers/lti.py` already supports platform registration, OIDC login initiation/callback, one-time exchange, and LTI user linking.
- `backend/app/services/lti_service.py` already contains the base LTI cryptographic/JWKS/token validation helpers.
- `backend/app/models/lti.py` already contains `LTIPlatform`, `LTIUserLink`, `LTIAuthState`, and `LTIAuthCode`.
- `backend/app/schemas/lti.py` already contains platform and exchange schemas.
- `backend/app/config.py` already has LTI tool key/KID and target-link URI settings.
- `backend/app/tests/test_lti.py` exists and exercises the base LTI flow with a generated test RSA keypair.

Therefore the safe scope is **incremental AGS + resource-link discovery**, not a wholesale LTI 1.3 port. Keep current-main OIDC and login/session behavior as the base and port only the verified deltas.

### Exact incremental deltas confirmed

- Extend `LTIAuthCode` with platform/deployment/resource-link/subject context, and extend `AuthSession` with the same verified launch context needed by submission handling.
- Add `LTIAssignmentLink`, `LTIResourceLinkDiscovery`, `LTIAGSGradeEvent`, and `LTIAGSDeliveryLease` to the existing LTI model module and model exports.
- Extend `AssignmentSubmission` with grade version and verified LTI target/subject fields. Preserve current-main's student-only role guard in `submit_assignment`; source branch's LTI additions must be transplanted around that guard, not replace the current function.
- Extend the existing LTI router with resource discovery, assignment-link administration, grade-event inspection and controlled retry. Preserve current-main OIDC endpoints and security headers/cookie handling.
- Extend the current LTI service with AGS endpoint validation, discovery persistence, outbox creation, OAuth client assertion/token handling, ordered grade delivery, lease handling and retry behavior.
- Add the AGS Celery beat/outbox tasks to current-main `tasks.py`; current main currently schedules only weekly digest and due-card reminders.
- Do not re-port base LTI platform registration, OIDC launch, JWKS validation, or user-linking code unless a concrete diff proves a necessary fix.

### Updated port order

1. Reconcile only the incremental source/main diff for the LTI model, auth-code context, auth-session context, and assignment-submission fields.
2. Reconcile migrations against current-main's existing LTI tables and its `0023_content_ownership` head. Re-chain the six source migrations, accounting for the already-present base LTI schema; inspect whether any source migration attempts to recreate a table/column that current main already has.
3. Port service functions in bounded groups: resource discovery; outbox event creation; AGS OAuth/token and HTTP delivery; lease/order/retry.
4. Port router endpoints while retaining main's current OIDC implementation and admin authorization.
5. Port assignment submit/grade changes while preserving student-only and assignment visibility/enrollment protections; add teacher/admin 403 no-side-effect tests.
6. Port Celery scheduling and worker tasks; verify task registration, Beat cadence, bounded dispatch and recovery.
7. Run model metadata/migration graph checks and full CI on the integration head. Sandbox Moodle/Canvas tests remain separate release gates.

### Critical migration correction

Because main already has base LTI tables, the source migration bodies must be checked for overlap before applying the proposed renumbering. In particular, verify whether `lti_platforms`, `lti_user_links`, `lti_auth_states`, and `lti_auth_codes` are created by existing main migrations and ensure the incremental chain alters/adds only missing AGS context. The previous proposed linear revision numbers are provisional; never blindly apply them if they duplicate existing schema operations.


## Corrected migration-body verification (20 Nov 2026)

The complete relevant migration bodies were fetched from both current `main` and the legacy LTI source branch. This resolves the earlier open question about whether AGS recreates the base LTI schema:

- Current `main` already has the shared ancestor migrations `0014_lti` and `0018_lti_one_time_auth`. They create `lti_platforms`, `lti_user_links`, `lti_auth_states`, and `lti_auth_codes`.
- The legacy AGS migration `0023_lti_ags_grade_passback` does **not** recreate those four base tables. It adds `assignment_submissions.grade_version`, creates `lti_assignment_links` and `lti_ags_grade_events`, and adds their constraints/index.
- Legacy `0024_lti_resource_discovery` alters the already-existing `lti_auth_codes` and `auth_sessions` tables, adds the submission-to-assignment-link FK/index, and creates `lti_resource_link_discoveries`.
- Legacy `0025_lti_ags_delivery_order` backfills `score_timestamp` from `created_at`, makes it non-null with a server default, and expands the grade-event status check to include `superseded`.
- Legacy `0026_lti_submission_subject` adds `lti_subject` to auth codes, sessions, and submissions.
- Legacy `0027_lti_ags_delivery_lease` creates the lease table and expiry index.
- Legacy `0028_lti_ags_manual_retry_authorization.py` adds `manual_retry_requested_at`; its actual Python revision identifier is `0028_lti_ags_manual_retry`, which differs from its filename and docstring.

The proposed integration graph is therefore structurally viable as a linear chain after current main's ownership migration:

1. `0024_lti_ags_grade_passback` revises `0023_content_ownership`.
2. `0025_lti_resource_discovery` revises `0024_lti_ags_grade_passback`.
3. `0026_lti_ags_delivery_order` revises `0025_lti_resource_discovery`.
4. `0027_lti_submission_subject` revises `0026_lti_ags_delivery_order`.
5. `0028_lti_ags_delivery_lease` revises `0027_lti_submission_subject`.
6. `0029_lti_ags_manual_retry` revises `0028_lti_ags_delivery_lease`.

This is a graph-level proposal, not a migration execution result. Before implementation, still inspect current main's complete Alembic graph and ensure every renamed filename, module `revision`, docstring ID, and `down_revision` agrees. Also review downgrade order and PostgreSQL/SQLite compatibility for named FK/check-constraint operations.

### Model-delta correction

The source model comparison confirms that base LTI model classes already exist in main and must be extended, not copied wholesale. The additional source-only model classes are `LTIAssignmentLink`, `LTIResourceLinkDiscovery`, `LTIAGSGradeEvent`, and `LTIAGSDeliveryLease`. Source-only fields include:
- `LTIAuthCode`: verified platform/deployment/resource-link/subject context.
- `AuthSession`: verified platform/deployment/resource-link/subject context.
- `AssignmentSubmission`: `grade_version`, `lti_assignment_link_id`, and `lti_subject`.

The earlier statement that these source-only fields need coordinated model/schema changes remains correct. The newly verified point is that the legacy AGS migration chain extends the shared base LTI tables rather than creating those base tables a second time.


## Incremental service/router/task review (20 Nov 2026)

Fetched current-main and legacy-source service, router, task, assignment and test files and compared their public definitions.

### Confirmed source-only AGS capabilities

The legacy source adds these service functions beyond current main's OIDC/JWKS base:

- `validate_lti_ags_lineitem_url`
- `record_lti_ags_launch_context`
- `create_lti_ags_grade_event`
- `build_ags_client_assertion`
- `request_ags_access_token`
- `post_lti_ags_score`
- `dispatch_lti_grade_event`

The source also adds resource discovery, assignment-link administration, grade-event inspection and an admin retry endpoint. Celery Beat schedules an outbox dispatcher every minute; the dispatcher selects at most 100 due pending event IDs, closes its DB session, then enqueues individual tasks. Worker settings observed in source: 45-second HTTP timeout, 8 automatic attempts, 120-second per-learner lease.

### Security regression: source submit route omits current-main student-only guard

The legacy `submit_assignment` implementation allows the assignment owner/manager branch to bypass the enrollment rejection and does not explicitly reject teacher/admin roles before creating/updating a submission. Current main's existing implementation includes an explicit `current_user.role == UserRole.user` requirement. This guard must be retained at the start of the submit handler before any ORM mutation or LTI context binding.

Required tests on the integrated branch:
- teacher submit attempt => 403, no submission row, no grade event, no study activity/notification side effects;
- admin submit attempt => same no-side-effect guarantees;
- student non-LTI submission continues to work;
- verified LTI student context binds only the exact platform + deployment + resource-link + assignment mapping;
- mismatched identity/resource/assignment produces no LTI target and no AGS event.

### Service integration cautions

- Keep current-main URL validation, DNS resolution, pinned-IP HTTP, no-redirect behavior and bounded response reads. Source changes extend endpoint resolution to permit a query string only for the validated AGS lineitem request; do not replace the safer current-main implementation wholesale.
- Preserve the exact launch subject and verified context only when exchanging a one-time LTI code into the browser session. Do not infer LMS subject from local user ID.
- Keep grade-event creation in the same transaction as the grade update so a committed grade cannot lose its outbox event.
- Delivery code commits before OAuth/HTTP and uses a per-(assignment-link, subject-hash) lease. Preserve this transaction boundary and test independent workers, lease expiry, stale-owner fencing, newer-grade supersession, retry timestamps and DB pool release.
- The dispatcher is a periodic scanner with a fixed 100-event selection limit; it is not a claim operation. Multiple Beat instances may enqueue duplicate event tasks, so worker-side row/lease fencing remains mandatory. Monitor backlog/oldest due age before changing cadence or limits.
- The source tests include dedicated AGS protocol and grade-target-binding suites. These tests are useful porting references but are not proof they pass against current main until actually run on the integrated head.

### Current disposition

No application code has been copied. This review is a porting checklist and a confirmed security regression to guard against. The next safe code change should be a narrow, reviewed model/schema increment plus tests on the integration branch, followed by service functions in bounded units. Do not port the legacy `assignments.py` wholesale.


## Model integration progress (2026-11-20)

The integration branch now includes the AGS model layer, based on the source branch but applied only to the four model files after verifying the integration branch still matched the expected main blobs:

- `backend/app/models/lti.py`: adds `LTIAssignmentLink`, `LTIResourceLinkDiscovery`, `LTIAGSGradeEvent`, and `LTIAGSDeliveryLease`; extends `LTIAuthCode` with verified platform/deployment/resource-link/subject context.
- `backend/app/models/assignment.py`: adds `grade_version`, `lti_assignment_link_id`, `lti_subject`, and the mapping relationship while retaining the main assignment/submission fields and unique constraint.
- `backend/app/models/auth_session.py`: adds the verified LTI launch context while retaining the main session fields and indexes.
- `backend/app/models/__init__.py`: registers and exports the new model classes.

Commits created on the integration branch:
- `355e4f09ba7d5a9cce4365e6aa83c41144afe2ca`
- `259599a2f0b8d8b96ed892bfd19f4959241edc11`
- `e9a6bfdf41cd9092883ed0f8f7a3b8a66f732498`
- `48797c33fe5134cd4b08adbdf55f85bfd650d537`

No application tests have been run for these commits yet.

## Migration graph conflict and required rechain

The current main branch already owns revision `0023_content_ownership` (down revision `0022_auth_sessions`). The source AGS branch independently uses revision `0023_lti_ags_grade_passback` with the same down revision. These cannot be combined as-is: the integrated Alembic graph would have two heads.

The safe linear integration sequence must preserve main's content-ownership migration and re-number/re-chain the AGS migrations:
1. `0024_lti_ags_grade_passback` revises `0023_content_ownership`.
2. `0025_lti_resource_discovery` revises `0024_lti_ags_grade_passback`.
3. `0026_lti_ags_delivery_order` revises `0025_lti_resource_discovery`.
4. `0027_lti_submission_subject` revises `0026_lti_ags_delivery_order`.
5. `0028_lti_ags_delivery_lease` revises `0027_lti_submission_subject`.
6. `0029_lti_ags_manual_retry` revises `0028_lti_ags_delivery_lease`.

The source migration file `0028_lti_ags_manual_retry_authorization.py` has a metadata mismatch: its docstring says `0028_lti_ags_manual_retry_authorization`, while its actual revision is `0028_lti_ags_manual_retry`. The integrated migration should use one consistent revision ID and filename.

Migration implementation is not yet applied. Before writing migrations, inspect all existing main/source migration operations, dialect compatibility (especially SQLite batch/foreign-key behavior), and downgrade ordering. Never run migrations against a real or production database as part of this integration step.
