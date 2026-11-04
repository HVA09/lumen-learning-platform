/**
 * Initial ESLint baseline for the Lumen frontend.
 *
 * This is intentionally a small, dependency-free core-rule set. Findings are
 * warnings only until the existing codebase has been measured and reviewed.
 * React-specific, accessibility, and import-order rules are not included yet.
 */

const asReadonlyGlobals = (names) =>
  Object.fromEntries(names.map((name) => [name, "readonly"]));

const browserGlobals = asReadonlyGlobals([
  "window",
  "document",
  "navigator",
  "location",
  "history",
  "localStorage",
  "sessionStorage",
  "console",
  "fetch",
  "Headers",
  "Request",
  "Response",
  "URL",
  "URLSearchParams",
  "FormData",
  "Blob",
  "File",
  "FileReader",
  "WebSocket",
  "Event",
  "EventTarget",
  "CustomEvent",
  "Node",
  "Element",
  "HTMLElement",
  "HTMLInputElement",
  "HTMLFormElement",
  "MutationObserver",
  "IntersectionObserver",
  "ResizeObserver",
  "AbortController",
  "DOMParser",
  "TextEncoder",
  "TextDecoder",
  "requestAnimationFrame",
  "cancelAnimationFrame",
  "setTimeout",
  "clearTimeout",
  "setInterval",
  "clearInterval",
  "queueMicrotask",
  "performance",
  "crypto",
  "Notification",
  "Audio",
  "Image",
  "Worker",
  "atob",
  "btoa",
  "structuredClone",
]);

const testGlobals = asReadonlyGlobals([
  "describe",
  "it",
  "test",
  "expect",
  "vi",
  "beforeAll",
  "afterAll",
  "beforeEach",
  "afterEach",
]);

export default [
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: browserGlobals,
    },
    rules: {
      "no-unused-vars": [
        "warn",
        {
          args: "after-used",
          argsIgnorePattern: "^_",
          caughtErrors: "none",
          ignoreRestSiblings: true,
          varsIgnorePattern: "^_",
        },
      ],
      "no-undef": "warn",
      "no-unreachable": "warn",
      "no-constant-condition": "warn",
      "no-dupe-keys": "warn",
      "no-duplicate-case": "warn",
      "no-fallthrough": "warn",
      "no-self-assign": "warn",
      "no-self-compare": "warn",
      "valid-typeof": "warn",
    },
  },
  {
    files: ["src/**/*.{test,spec}.{js,jsx}", "src/test/setup.js"],
    languageOptions: {
      globals: testGlobals,
    },
  },
];
