# Frontend Engineering Guide

## Scope
Applies to the Vue 3 + JavaScript frontend with Pinia, Vite, Sass, and Biome.
Engineers and AI contributors should follow these rules.

Goal: keep frontend code readable, predictable, testable, and easy to change.
Preferences allow justified exceptions; mandatory safeguards use “must”.

## General Rules
- Prefer simple, explicit code and focused components.
- Use Vue single-file components and Composition API with `<script setup>` in plain JavaScript.
- Prefer composition; extract reusable behavior into composables only when useful.
- Keep complex domain calculations in testable functions; simple display logic belongs in templates.
- Reuse stable concepts without coupling unrelated features or creating speculative abstractions.
- Keep API models and UI models separate when they differ.

## JavaScript
- Use ES modules, `const` by default, and `let` when reassignment is needed.
- Use selective JSDoc to explain non-obvious parameters, return values, and shared API contracts.
- Validate untrusted data at boundaries; documentation does not validate JSON at runtime.
- Keep functions focused and use descriptive names and explicit failure handling.
- Avoid unexplained domain values and unnecessary defensive checks for internally guaranteed values.

## Naming
- Use PascalCase for component filenames, such as `DeviceCard.vue`.
- Use camelCase for variables and functions; boolean names start with `is`, `has`, `can`, or `should`.
- Name composables `useSomething`, such as `useDeviceTelemetry.js`.
- Name domain API modules `devices.api.js` and store modules `devices.js`.
- Export stores as `useSomethingStore`, such as `useDevicesStore`.
- These are conventions, not required files for every feature.

## Components and Reactivity
- A component displays data, collects input, or coordinates a small UI workflow.
- Declare props and emitted events explicitly with `defineProps` and `defineEmits`.
- Treat props as read-only, including nested objects; emit events to request parent-owned changes.
- Use local `ref` or `reactive` state by default and `computed` for derived values.
- Keep computed getters free of side effects; do not duplicate values that can be derived.
- Handle user actions in event handlers. Use watchers to synchronize external effects when needed.
- Preserve reactivity when extracting values from reactive objects.
- Use stable domain identifiers as list keys.
- Clean up timers, listeners, subscriptions, and pending requests when their owner is disposed.
- Avoid components with many flags for unrelated behavior; split by responsibility or useful reuse.

## Pinia
- Register one Pinia instance at application startup.
- Use setup stores for state genuinely shared across components or routes.
- Keep temporary form input and component-only UI state local.
- Expose state, computed getters, and actions with clear responsibilities.
- Use actions for shared workflows; keep HTTP transport in domain API modules.
- Use `storeToRefs` when destructuring reactive store state or getters; actions can be destructured directly.
- Treat server data as server-owned; a store is not an independent source of truth.
- Avoid unbounded caches, duplicated state, and speculative stores.
- Clear user/company-specific state when the session or company changes; ensure obsolete responses cannot restore it.
- Do not persist passwords or invitation secrets. Choose token storage deliberately when authentication is implemented; do not add automatic store persistence by default.

## API Communication
- Group API functions by domain and keep transport details outside components.
- Document request/response contracts and validate relevant external data at the boundary.
- Handle loading, success, error, and empty states.
- Cancel obsolete requests where possible and prevent stale responses from overwriting current data.
- Bound request duration and retries; do not automatically retry writes without a safe retry contract.
- Never silently ignore API failures or expose internal backend details in UI messages.

## Security and Error Handling
- Secrets must never be included in browser code or client-exposed configuration.
- Backend authorization must enforce access and company isolation; hiding controls is only a UI decision.
- Avoid untrusted `v-html`; if HTML rendering is required, use a maintained sanitizer.
- Make user-facing errors understandable; log useful diagnostic context without tokens, passwords, or sensitive payloads.

## Styling
- Use Sass with SCSS syntax consistently.
- Put shared foundations and design tokens in global SCSS; use scoped SCSS for component styles.
- Avoid excessive nesting, broad global selectors, and unnecessary `!important`.
- Prefer semantic class names and shared tokens for recurring colors, spacing, and typography.
- Ordinary literals do not all need constants.

## Accessibility
- Use semantic HTML, labeled inputs, and actual buttons for actions.
- Important state must not rely only on color.
- Interactive controls must be keyboard accessible with visible focus.
- Manage focus for dialogs and associate validation messages with inputs.
- Make important status changes accessible to assistive technology.

## Resource Efficiency
- Bound retained telemetry, chart points, and caches; paginate or virtualize large lists when needed.
- Batch or throttle live updates, avoid overlapping polling, and pause unnecessary background work.
- Avoid repeated requests, unnecessary data copies, and expensive work during rendering.
- Measure responsiveness and memory before adding complex optimizations.

## Testing
- Test utilities, transformations, and meaningful application rules with unit tests.
- Test component behavior: input validation, interactions, loading/error/empty states, request races, cleanup, and keyboard use.
- Test store actions and session cleanup when shared state is introduced.
- Cover critical user flows with end-to-end tests as features arrive.
- Prefer Vitest and Vue Test Utils when meaningful tests are introduced.
- Test behavior rather than implementation details.

Vitest covers API boundaries and session behavior. Playwright covers critical browser flows with mocked API responses. Run `npm test` and `npm run test:e2e` for these checks.

## Code Quality
Biome is the formatter and linter, with recommended rules enabled. Vue/HTML support
is explicitly enabled but experimental. Verify fixes involving Vue templates and
script bindings; suppress only a specific demonstrated false positive with an explanation.

Biome checks JavaScript, Vue, HTML, and JSON. It does not lint or format SCSS or
Markdown in this setup. Vite's production build validates Vue and Sass compilation;
it does not provide static type checking or replace behavior tests.

Before merge:
- `npm run check` and `npm run build` pass.
- Relevant automated tests pass once configured.
- Report missing checks and untested behavior honestly.
- Remove debug logs and dead code.

## Review Checklist
- Are responsibilities, names, props, and events clear?
- Is reactivity preserved and derived state computed?
- Is Pinia used only for genuinely shared state?
- Is API logic separated from UI and are failures explicit?
- Are loading, error, and empty states handled?
- Are access boundaries enforced by the backend?
- Are requests, subscriptions, and retained data bounded or cleaned up?
- Are keyboard access and focus behavior usable?
- Are important behaviors tested, and does each abstraction simplify the feature?
