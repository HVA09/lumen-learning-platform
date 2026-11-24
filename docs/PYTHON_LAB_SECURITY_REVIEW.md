# Python Lab Security Review — 24 November 2026

Related issue: [#134](https://github.com/HVA09/lumen-learning-platform/issues/134)

## Scope and evidence

This is a source-level review of the Python lab at `main` commit `7240b77f706adc6706b14b0163809e244d46a965`, supplemented by the existing browser E2E test and the CI run recorded below. This is not a production penetration test or proof for every browser/runtime combination.

Reviewed files:

- `frontend/src/components/simulations/PythonLabSim.jsx`
- `frontend/public/python-sandbox.html`
- `frontend/public/python-sandbox.js`
- `frontend/src/components/simulations/PythonLabSim.test.jsx`
- `frontend/e2e/smoke_test.py`
- `.github/workflows/ci.yml`

## Controls verified in source

1. Learner code is sent to a dedicated iframe with `sandbox="allow-scripts"`; it is not granted `allow-same-origin`, forms, popups, navigation, or other permissions. The child therefore has an opaque origin rather than the authenticated application's origin.
2. The parent accepts messages only when both `event.source === frame.contentWindow` and `event.origin === "null"`, and checks a fixed channel and the active request ID.
3. The iframe bridge accepts commands only from `window.parent` and the origin derived from its document referrer. The iframe is configured with `referrerPolicy="origin"`.
4. Pyodide runs in a dedicated Blob Web Worker. Replacing the iframe terminates the worker, allowing cancellation of an infinite loop without blocking the authenticated page's main thread.
5. The iframe CSP defaults to deny, permits scripts from the application origin and the pinned jsDelivr origin, limits connections to jsDelivr, permits Blob workers and WebAssembly compilation, and denies objects, forms, base URL changes, styles, and images.
6. The parent enforces code and output size limits, boot and execution timeouts, and a user-triggered cancel/reset path.
7. Component tests cover iframe sandbox attributes, normal execution, forged message origins, wrong message sources, error handling, cancellation, and timeout behavior.
8. A real-browser test already exists in `frontend/e2e/smoke_test.py` as `_exercise_python_sandbox_isolation`, and `run_smoke_test()` invokes it. It creates an opaque-origin sandbox iframe in Chromium, verifies the parent cannot read its document, executes adversarial probes in the actual Pyodide Worker, checks that Worker DOM/storage access and parent-document access are blocked, and requires an enforced `connect-src` CSP violation for a request to the configured API origin.

## CI evidence

The documentation-only PR #178 ran workflow [45477095009](https://github.com/HVA09/lumen-learning-platform/actions/runs/45477095009) on commit `aab0adc3adce90800b8c0b527431a3a50da15a1d`.

At the time of this review:
- Browser E2E: **passed**, including the Python sandbox isolation function.
- Frontend tests and production build: **passed**.
- Full Git-history secret scan: **passed**.
- Backend tests: **still running** at the last status check.

A successful E2E job is evidence for this Chromium CI environment only. It is not a substitute for testing other supported browsers or a deployed non-root base path.

## Remaining verification required before closing #134

1. Extend the adversarial probe to explicitly attempt `sessionStorage` and cookie access, and assert no parent cookie or session marker is exposed. Current browser test seeds a parent cookie but does not explicitly print/assert a cookie-access probe from the worker.
2. Verify that no request reaches the API server when the Worker attempts access; the existing test requires an enforced CSP violation for the API origin, which is useful evidence but should be paired with server-side request observation.
3. Test additional non-CDN network destinations and ensure CSP blocks them.
4. Run the isolation E2E test in at least one additional supported browser, in addition to Chromium.
5. Verify deployed asset paths when `BASE_URL` is not `/`. The iframe URL is built from `BASE_URL`, while the child document currently loads `/python-sandbox.js` as a root-relative path; confirm the supported deployment topology or make this path base-aware.
6. Review the pinned Pyodide/CDN supply-chain assumption and document the supported-browser matrix and residual risks.

## Disposition

**Isolation controls and Chromium E2E coverage are present; issue #134 remains open pending the additional checks above.** WebAssembly alone is not the security boundary: the intended boundary is the opaque-origin iframe, restrictive CSP, and isolated worker. No production settings, secrets, student data, or production database were changed. This review does not authorize a deployment or broad enablement decision.
