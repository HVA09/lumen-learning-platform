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
