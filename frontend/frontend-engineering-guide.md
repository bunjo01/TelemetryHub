# Frontend Engineering Guide

## Scope
Applies to the React + TypeScript frontend.
Engineers and AI contributors should follow these rules.

Goal: keep frontend code readable, predictable, testable, and easy to change.
Preferences allow justified exceptions; mandatory safeguards use “must”.

## General Rules
- Prefer simple code over clever code.
- Keep components focused on one responsibility.
- Keep complex domain calculations in testable functions; straightforward display logic belongs in JSX.
- Prefer composition over inheritance.
- Reuse stable concepts; accept small duplication when sharing would couple unrelated features.
- Do not create abstractions before they are needed.
- Keep API models and UI models separate when they differ.
- Follow idiomatic React and TypeScript and existing project conventions.

## TypeScript
- Use strict TypeScript settings.
- Avoid `any`; prefer proper types or `unknown`.
- Prefer explicit return types for shared/public functions.
- Use unions for a known set of alternatives.
- Avoid excessive type assertions.
- Avoid non-null assertions unless the value is guaranteed.

Example:

```ts
type DeviceStatus = "online" | "offline" | "warning";
```

## Naming
Use:
- `PascalCase` for components and types.
- `camelCase` for variables and functions.
- boolean names starting with `is`, `has`, `can`, or `should`.
- `use` followed by a capitalized name for custom hooks, such as `useDeviceTelemetry`.

Use descriptive domain names. These filenames illustrate conventions, not required files for every feature:

```text
DeviceCard.tsx
DeviceDetailsPage.tsx
device.api.ts
device.types.ts
isLoading
hasError
canEdit
```

## Component Design
A component should primarily:
- display data,
- collect input, or
- coordinate a small UI workflow.

Split components by responsibility or useful reuse, not an arbitrary line count.
Avoid shared components with many flags for unrelated variations.
Keep database and backend implementation details outside UI components.

- Keep rendering pure and treat props and state as immutable.
- Follow hook rules; ordinary hooks belong at the top level of components or custom hooks.
- Use stable item identifiers as keys for lists that can change order or membership.

## State
- Use local state by default.
- Use shared state only when multiple parts of the app truly need it.
- Treat server data as server-owned data.
- Do not put everything in global state.
- Derive values from props/state when possible instead of storing duplicate state.
- Handle user actions in event handlers; use effects to synchronize external systems.
- Declare effect dependencies accurately and clean up timers, listeners, and subscriptions.

## API Communication
- Keep transport details in domain API functions or hooks that components can call.
- Group API functions by domain.
- Use typed request and response models.
- Validate untrusted external data at boundaries; TypeScript types do not validate JSON at runtime.
- Cancel obsolete requests where possible and prevent stale responses from overwriting current data.
- Handle loading, success, error, and empty states.
- Never silently ignore API failures.

## Error Handling
User-facing errors should be understandable.

Log useful diagnostic context without secrets or sensitive payloads; keep internal details out of UI messages.

## Security
- Secrets must never be included in browser code or client-exposed configuration.
- Backend authorization must enforce access; hiding controls is only a UI decision.
- Avoid rendering untrusted HTML; if required, use a maintained sanitizer.

## Styling
- Use SCSS consistently.
- Avoid excessive nesting.
- Prefer semantic class names.
- Use shared design tokens for recurring colors, spacing, and typography; ordinary literals do not all need constants.
- Avoid `!important` unless necessary.

## Accessibility
- Use semantic HTML.
- Inputs need labels.
- Buttons should be actual buttons.
- Important state must not rely only on color.
- Interactive controls must be keyboard accessible.
- Keep keyboard focus visible; manage focus when dialogs open and close.
- Associate validation messages with their inputs and make important status changes accessible to assistive technology.

## Resource Efficiency
- Bound retained telemetry, chart points, and caches; paginate or virtualize large lists as appropriate.
- Batch or throttle live updates and avoid overlapping polling requests; pause unnecessary background work.
- Avoid repeated requests, unnecessary data copies, and expensive work during rendering.
- Measure rendering time, responsiveness, and memory on representative data before adding memoization or other complex optimizations.

## Testing
### Unit Tests
Test:
- utilities,
- transformations,
- frontend business-like logic.

### Component Tests
Test:
- important UI states,
- validation,
- user interactions,
- loading/error/empty states,
- relevant request races, cleanup, and keyboard interactions.

### End-to-End Tests
Cover only critical flows, such as:
- login,
- open device,
- view telemetry,
- acknowledge alert.

Test behavior, not implementation details.

## Code Quality
Biome and strict TypeScript are configured. Biome currently uses the lint-rule
preset `none`; useful lint rules need to be enabled for enforcement.
No test runner or test script is configured yet. Configure these when adding tests
and report unavailable checks honestly.

Before merge:
- `npm run check`, `npm run typecheck`, and `npm run build` pass,
- relevant automated tests pass once configured,
- missing checks or untested behavior are reported,
- no debug logs,
- no dead code.

## Avoid
- giant components,
- `any`,
- duplicated API logic,
- global state for everything,
- premature abstractions,
- hidden side effects,
- unexplained domain values and duplicated design tokens.

## Review Checklist
- Is the component responsibility clear?
- Are names descriptive?
- Are types strict?
- Is API logic separated from UI?
- Are loading/error states handled?
- Are important behaviors tested?
- Are requests, subscriptions, and retained data bounded or cleaned up?
- Are keyboard access and focus behavior usable?
- Is the code simpler than the alternative?
