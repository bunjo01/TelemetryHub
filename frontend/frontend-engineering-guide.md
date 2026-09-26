# Frontend Engineering Guide

## Scope
Applies to the React + TypeScript frontend.

Goal: keep frontend code readable, predictable, testable, and easy to change.

## General Rules
- Prefer simple code over clever code.
- Keep components focused on one responsibility.
- Avoid large components with too much business logic.
- Keep business logic outside templates when possible.
- Prefer composition over inheritance.
- Do not duplicate logic without reason.
- Do not create abstractions before they are needed.
- Keep API models and UI models separate when they differ.

## TypeScript
- Use strict TypeScript settings.
- Avoid `any`; prefer proper types or `unknown`.
- Prefer explicit return types for shared/public functions.
- Prefer unions over magic strings.
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

Examples:

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

Split components when responsibilities become unrelated.

Avoid:
- large components,
- business logic inside templates,
- direct database/backend knowledge in UI components.

## State
- Use local state by default.
- Use shared state only when multiple parts of the app truly need it.
- Treat server data as server-owned data.
- Do not put everything in global state.

## API Communication
- Keep HTTP calls outside components.
- Group API functions by domain.
- Use typed request and response models.
- Handle loading, success, error, and empty states.
- Never silently ignore API failures.

## Error Handling
User-facing errors should be understandable.

Technical error details belong in logs, not UI messages.

## Styling
- Use SCSS consistently.
- Avoid excessive nesting.
- Prefer semantic class names.
- Avoid repeated magic values.
- Avoid `!important` unless necessary.

## Accessibility
- Use semantic HTML.
- Inputs need labels.
- Buttons should be actual buttons.
- Important state must not rely only on color.
- Interactive controls must be keyboard accessible.

## Performance
Watch for:
- unnecessary re-renders,
- repeated API calls,
- expensive computations,
- rendering huge telemetry lists.

Use pagination or virtualization when needed.

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
- loading/error/empty states.

### End-to-End Tests
Cover only critical flows, such as:
- login,
- open device,
- view telemetry,
- acknowledge alert.

Test behavior, not implementation details.

## Code Quality
Use:
- Biome,
- TypeScript strict mode,
- automated tests.

Before merge:
- formatting passes,
- lint passes,
- TypeScript passes,
- tests pass,
- no debug logs,
- no dead code.

## Avoid
- giant components,
- `any`,
- duplicated API logic,
- global state for everything,
- premature abstractions,
- hidden side effects,
- magic strings/numbers.

## Review Checklist
- Is the component responsibility clear?
- Are names descriptive?
- Are types strict?
- Is API logic separated from UI?
- Are loading/error states handled?
- Are important behaviors tested?
- Is the code simpler than the alternative?
