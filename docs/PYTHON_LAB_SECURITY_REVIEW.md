# Python Lab Security Review — 24 November 2026

Related issue: [#134](https://github.com/HVA09/lumen-learning-platform/issues/134)

## Scope and evidence

This is a source-level review of the current `main` implementation at `7240b77f706adc6706b14b0163809e244d46a965`. It is not a live-browser penetration test, a production deployment approval, or proof that every browser/runtime combination enforces the intended policy.

Reviewed files:

- `frontend/src/components/simulations/PythonLabSim.jsx`
- `frontend/public/python-sandbox.html`
- `frontend/public/python-sandbox.js`
- `frontend/src/components/simulations/PythonLabSim.test.jsx`
- `frontend/vite.config.js`
- `backend/app/main.py`

## Controls verified in source

1. Learner code is sent to a dedicated iframe with `sandbox="allow-scripts"`; the iframe is not granted `allow-same-origin`, forms, popups, navigation, or other permissions. This gives the child an opaque origin rather than the authenticated application's origin.
2. The parent accepts messages only when both `event.source === frame.contentWindow` and `event.origin === "null"`, and checks a fixed channel and the active request ID.
3. The iframe bridge accepts commands only from `window.parent` and the origin derived from its document referrer. The iframe is configured with `referrerPolicy="origin"`.
4. Pyodide is executed in a dedicated Web Worker created from a Blob. The worker can be terminated by replacing the iframe, so an infinite Python loop does not need to block the authenticated page's main thread.
5. The iframe CSP defaults to deny, permits scripts from the application origin and the pinned jsDelivr origin, limits connections to jsDelivr, permits Blob workers and WebAssembly compilation, and denies objects, forms, base URL changes, styles, and images.
6. The parent enforces code and output size limits, a boot timeout, an execution timeout, and a user-triggered cancel/reset path.
7. Existing component tests cover iframe sandbox attributes, normal execution, forged message origins, wrong message sources, error handling, cancellation, and timeout behavior.

## Important interpretation

- WebAssembly by itself is not the security boundary. The intended boundary is the opaque-origin iframe plus the worker and restrictive CSP.
- The parent uses target origin `*` when posting to an opaque-origin iframe; that is expected because the iframe's origin is `null`. The child validates the sender's source and the exact parent origin before accepting a run request.
- The reviewed component tests simulate `postMessage` events. They do not execute hostile Python in a real browser and do not prove browser-enforced isolation end-to-end.

## Remaining verification required before closing #134

1. Add a real-browser E2E test that runs adversarial Python attempting to access `window`, `document`, local/session storage, cookies, and the parent application DOM. Assert that no authenticated-page object is reachable.
2. Test attempts to call the application's authenticated API and other non-CDN network destinations from the Python runtime. Verify CSP blocks them in supported browsers; ensure no credentialed request reaches the Lumen API.
3. Verify that the worker cannot communicate with the parent except through the narrowly validated bridge and that forged/unsolicited worker messages cannot complete another request.
4. Test boot timeout, execution timeout, cancellation, iframe replacement, and repeated runs in Chromium and at least one additional supported browser.
5. Verify deployed asset paths when `BASE_URL` is not `/`. The iframe URL is built from `BASE_URL`, while the child document currently loads `/python-sandbox.js` as a root-relative path; confirm supported deployment topology or make this path base-aware.
6. Review the pinned Pyodide/CDN supply-chain assumption and ensure the CSP does not silently broaden beyond the intended CDN origin.
7. Record the supported-browser matrix and residual risks. Do not enable broader student access based solely on unit tests.

## Disposition

**Partially addressed; not closed.** The source contains meaningful isolation controls, but the acceptance criteria in #134 require browser-level adversarial verification. No application code, production settings, secrets, student data, or production database were changed by this review. No deployment is authorized by this document.
