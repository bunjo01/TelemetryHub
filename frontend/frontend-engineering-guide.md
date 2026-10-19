# Frontend Engineering Guide

## Scope
Applies to the Vue 3 + JavaScript frontend with Pinia, Vite, Sass, and Biome.
Engineers and AI contributors must follow this guide for frontend work.

Goal: keep frontend code readable, predictable, testable, and easy to change.
Required conventions include BEM naming, component ownership, multiline SCSS,
and logical grouping of related style rules. They are not optional preferences.
Direct instructions such as “use”, “keep”, and “do not” state project rules;
“prefer” and “should” indicate recommendations that allow justified alternatives.
“Must” emphasizes a requirement. Explicit exceptions are identified in the guide.

## How to Use This Guide

- Read this guide before implementing or refactoring frontend code. Inspect the affected components, their callers, and relevant tests before choosing an abstraction.
- Apply these conventions to new and changed code. Existing code may predate them and is not a precedent to copy blindly.
- Keep changes within the requested scope. A request to follow this guide does not authorize a whole-application rewrite.
- Preserve appearance, accessibility, API contracts, and user-visible behavior during structural refactoring unless the task explicitly changes them.
- Document why an exception is needed and how it preserves the rule's intent. Exceptions must not silently discard required conventions or security and accessibility safeguards. Routine implementation choices do not require user approval.
- Optimize for clear ownership and predictable changes, not the largest number of components or the shortest files.

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

### Component Boundaries and Reuse

Separate these responsibilities:

| Layer | Owns | Should not own |
| --- | --- | --- |
| Shared UI components | Repeated controls and interaction behavior: buttons, labeled fields, dialog shells, feedback | Domain API calls, company permissions, authentication redirects |
| Feature components | A coherent workflow, such as company selection or invitation creation | Internal implementation of other components |
| Views and application layout | Page composition, navigation coordination, placement of components | Duplicated implementations of shared controls |
| API modules and stores | HTTP contracts and genuinely shared application state | Presentation and local form layout |

- Extract repeated markup and behavior when they represent the same concept. Similar colors or dimensions alone do not justify merging unrelated components.
- A component used once can still deserve extraction if it isolates a substantial responsibility. Line count is a signal to inspect responsibilities, not a hard limit.
- Before adding a control, look for an existing implementation to reuse or extend. Keep supported variants small and driven by actual callers.
- Shared buttons must preserve native semantics, explicit button types, disabled behavior, and accessible names. Do not turn every HTML element into a wrapper component.
- Shared fields must consistently connect labels, controls, help text, and errors. Forward native attributes and events to the intended control, preserve `v-model`, and support focus without querying private markup.
- Shared dialogs own their shell and common interaction lifecycle: accessible labeling, initial focus, closing, and focus restoration. Prefer native `<dialog>`. Feature code owns submission state and whether closing is currently allowed, communicating this through the dialog's public interface.
- Keep domain-specific search and selection separate from the workflow that consumes the selection. Introduce a general searchable dropdown only when its contract is justified by real uses.
- Keep shared application chrome in the application layout. Extract a header or footer when it gives that responsibility a clearer owner.
- Prefer props, events, slots, and small explicit exposed methods over reaching into another component's DOM or private state. A reusable child must not depend on a particular parent or route.
- Use composables for cohesive stateful behavior when this improves reuse or clarity. Do not move every handler into a composable merely to shorten a component.

For example, an invitation workflow can compose a dialog shell, a company picker,
form controls, and an invitation-link result. The invitation component coordinates
submission; the dialog does not know about invitation endpoints, and the picker
does not create invitations. Each extracted unit must make the workflow easier to
understand, not just move its complexity across files.

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
- Keep session tokens in memory under the current authentication design. Do not add persistence as part of a UI refactor; changing session storage requires an explicit authentication-design task.

## API Communication
- Group API functions by domain and keep transport details outside components.
- Document request/response contracts and validate relevant external data at the boundary.
- Handle loading, success, error, and empty states.
- Cancel obsolete requests where possible and prevent stale responses from overwriting current data.
- Bound request duration and retries; do not automatically retry writes without a safe retry contract.
- Never silently ignore API failures or expose internal backend details in UI messages.

## Security and Error Handling
- Server credentials, signing keys, and other server-only secrets must never be embedded in shipped source, assets, or client-exposed configuration.
- Runtime credentials, such as user-entered passwords, session tokens, and invitation tokens, may be handled only where their workflow requires them. Do not log them or persist them in local storage, session storage, or application caches. Clear sensitive form state when its workflow ends or is disposed.
- Preserve the invitation flow's deliberate URL-fragment behavior: the token remains in the registration fragment so refreshing works, is sent to the API in a request body rather than its URL, and is removed from the current URL after successful registration.
- Backend authorization must enforce access and company isolation; hiding controls is only a UI decision.
- Avoid untrusted `v-html`; if HTML rendering is required, use a maintained sanitizer.
- Make user-facing errors understandable; log useful diagnostic context without tokens, passwords, or sensitive payloads.

## Styling

Use Sass with SCSS syntax and BEM principles for component styling. Keep component
styles in `<style scoped lang="scss">` beside their template and logic. A Vue style
block is not an inline HTML style attribute; moving it into another file is not
required for readability.

Scoped styles and BEM have complementary roles: Vue scopes style matching, while
BEM makes ownership and relationships explicit. Scoped styles do not replace BEM
names or justify overriding a child's private markup.

### Formatting and Rule Organization

- Every nonempty style rule must use multiple lines, with one declaration per line and the closing brace on its own line. This applies even to one-property rules and rules inside media queries.
- Use two-space indentation and a blank line between rule blocks. Break long values, such as multiple background gradients, across lines where helpful.
- Keep related rules together: a block's base styling, elements, variants, interaction states, and responsive adjustments should be easy to find as a group.
- Within a component, keep related heading rules together and related control rules together. Do not scatter a button's styles among unrelated sections.
- Keep responsive rules with the component they affect, in a consistent order. Group them at the end of that component's styles when they affect several of its elements.
- Preserve intentional cascade order when regrouping rules. Formatting and reordering must not silently change appearance.
- Do not compress source SCSS to save lines. Production minification is the build tool's responsibility.

```scss
// Avoid, even for a short rule:
.button { cursor: pointer; }

// Use:
.button {
  min-height: 2.9rem;
  padding: 0.7rem 1.1rem;
  border-radius: 0.5rem;
  cursor: pointer;
}

.button--primary {
  background: var(--accent);
  color: #102722;
}

.button--primary:hover:not(:disabled) {
  background: #b7f3e6;
}

.button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
```

### BEM Naming and Ownership

Use lowercase, hyphenated names with `block__element--modifier` notation:

| Entity | Meaning | Example |
| --- | --- | --- |
| Block | An independent component with a meaningful purpose | `company-picker` |
| Element | A constituent part owned by that block | `company-picker__option` |
| Modifier | A variant or state of a block or element | `button--primary`, `company-picker__option--selected` |
| Mix | Multiple BEM entities on the same DOM node, each with a clear responsibility | `class="button invitation-form__submit"` |

- Use the base class together with its modifier: `class="button button--primary"`, never just `class="button--primary"`.
- Prefix modifiers with their owning block or element. Avoid unowned variant classes such as `primary`, `compact`, or `selected`.
- Name blocks and elements by purpose, and modifiers by meaningful variants or states. Prefer `button--primary` to `button--green`.
- Elements belong to blocks, not to other elements. Use `company-picker__option-label`, never `company-picker__option__label`.
- A block modifier does not create a new element namespace. Use `dialog__title` inside `dialog dialog--wide`, never `dialog--wide__title`.
- Nested DOM structure does not require nested class names or selectors. A reusable block inside another block keeps its own identity.
- Use simple class selectors for component appearance. Avoid IDs, bare tag selectors such as `h1` or `input`, and tag-qualified classes such as `button.button`.
- Keep compiled selector specificity low. Avoid long descendant chains and redundant combinations such as `.button.button--primary`. A block modifier affecting its own element, such as `.dialog--wide .dialog__body`, is a valid limited use of nesting.
- SCSS `&__element`, `&--modifier`, and pseudo-class nesting are acceptable when readable; they must not hide deep selector chains. Flat explicit selectors are also valid.
- Keep native state attributes and accessibility semantics. A BEM class does not replace `disabled`, `aria-expanded`, or another required HTML attribute. Native pseudo-classes such as `:disabled` and `:focus-visible` are appropriate.
- A BEM element does not automatically need its own Vue component. Extract components based on responsibility and useful reuse.

### Layout, Shared Styles, and Encapsulation

- A reusable block owns its internal appearance and layout. Its parent owns placement and spacing relative to siblings.
- Use a mix for contextual positioning rather than teaching a shared control about each page. For example, `.button` owns button appearance and `.invitation-form__submit` owns its placement in the form.
- Reusable components that accept a layout class must apply it to a documented layout root. For components with multiple roots or explicit attribute forwarding, route that class deliberately; do not rely on an ambiguous fallthrough. Forward control attributes to the control, not automatically to its wrapper.
- Keep the responsibilities of mixed classes distinct so their properties do not compete through source order.
- Shared button styles belong to the button component. Page-specific button placement belongs to the page. Styling ownership does not require a Vue component for every styled element: a heading can remain `profile__title` in the profile block, with related heading rules grouped there.
- Do not override another component's private elements with descendant selectors or `:deep()`. Prefer its supported props, slots, modifiers, or CSS custom properties. Document unavoidable third-party integration exceptions.
- Keep global SCSS small: shared design tokens and explicitly agreed document foundations. Component-specific typography, form controls, and variants belong to their blocks.
- Intentionally shared CSS-only blocks may live in `src/styles/` and be loaded once by `styles.scss` with Sass `@use`. The `message` block owns shared feedback appearance; use `message message--error` or `message message--success`. Consumers retain semantic markup, alert/status roles, IDs, and contextual layout classes. A CSS-only block does not require a Vue wrapper.
- Shared visual blocks also include `panel` (surface appearance), `eyebrow` (small section introductions), and `supporting-text` (secondary explanatory/status text), each in its own `src/styles/` file. Their callers own content, semantics, placement, and spacing. Customize supporting text size through `--supporting-text-font-size` (default `0.9rem`); the registration password hint uses `0.8rem`. Keep `--muted` as a color token, not a standalone styling class.
- Minimal document setup, such as `:root` tokens, body margin, and box sizing, is a deliberate project exception to strict BEM's avoidance of global rules. Keep these exceptions narrow; do not use them to introduce global visual styling for all headings, inputs, or buttons.
- Prefer shared tokens for recurring colors, spacing, and typography. Ordinary literals do not all need constants.
- Avoid unnecessary `!important`, generic wrapper components, and abstractions based only on matching CSS values.
- Group implementation by component ownership. Do not reproduce the classic BEM directory-per-modifier structure or introduce its JavaScript/build tools solely to claim BEM compliance. Vue components and Vite remain the project's implementation tools.

### Methodology References

These conventions apply BEM's independence, composition, and naming principles to
this Vue application. The formatting rules above are project conventions; BEM
alone does not enforce multiline formatting or source ordering.

- [Official BEM methodology](https://bem.info/en/methodology/)
- [CSS: ownership, composition, selectors, and reuse](https://bem.info/en/methodology/css/)
- [Naming conventions, including the two-dashes variant](https://bem.info/en/methodology/naming-convention/)
- [JavaScript: encapsulation and component interaction](https://bem.info/en/methodology/js/)
- [File structure](https://bem.info/en/methodology/filestructure/) and [FAQ](https://bem.info/en/methodology/faq/)

The [course_site repository](https://github.com/matejarilak/course_site) is an
inspiration for readable, grouped Sass, not an authoritative specification or an
architecture to copy. Follow the conventions in this guide when examples differ.

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
- Use the existing Vitest and Playwright suites. Prefer Vue Test Utils if focused Vue component tests are needed; it is not currently installed and is not required merely to refactor styles.
- Test behavior rather than implementation details.

Vitest covers API boundaries and session behavior. Playwright covers critical browser flows with mocked API responses. Run `npm test` and `npm run test:e2e` for these checks.

## Code Quality
Biome is the formatter and linter, with recommended rules enabled. Vue/HTML support
is explicitly enabled but experimental. Verify fixes involving Vue templates and
script bindings; suppress only a specific demonstrated false positive with an explanation.

Biome checks JavaScript, Vue, HTML, and JSON. It does not lint or format SCSS or
Markdown in this setup. Vite's production build validates Vue and Sass compilation;
it does not provide static type checking or replace behavior tests.

SCSS formatting, BEM naming, and component ownership currently require manual
review. A passing Biome check does not verify them. When extending tooling, add
SCSS-aware formatting and lint checks without overlapping formatter ownership;
validate support for Vue style blocks before enabling them. Automated naming
checks supplement, but do not replace, review of component boundaries and logical
rule grouping. This guide does not imply that such tooling is already installed.

For component or styling refactors, verify existing flows, keyboard focus and
Escape behavior, form semantics, loading and disabled states, request cancellation,
and desktop/mobile layouts. Prefer behavior-based test selectors over private CSS
classes. Update tests that intentionally inspect layout when class names change;
do not weaken assertions to make a refactor pass. Add focused tests for meaningful
new shared behavior rather than tests that simply mirror markup.

Before merge of application-code changes:
- `npm run check` and `npm run build` pass.
- Relevant existing automated tests pass; run the full unit and browser suites for a refactor of shared controls used across the application.
- Report missing checks and untested behavior honestly.
- Remove debug logs and dead code.

For documentation-only changes, review consistency, examples, and links and run
`git diff --check`. Application builds and browser tests are not required unless
the change also affects executable code or configuration.

## Review Checklist
- Are responsibilities, names, props, and events clear?
- Does each extraction remove duplication or isolate a coherent responsibility without creating a speculative general-purpose API?
- Do shared controls preserve native attributes, form behavior, accessible names, and focus handling?
- Are BEM blocks independent, elements correctly owned, and modifiers paired with their base classes?
- Does the parent own contextual placement without overriding a child's private appearance?
- Is SCSS multiline and logically grouped, with low-specificity selectors and narrowly limited global rules?
- Did the refactor preserve appearance and behavior, including responsive layouts and asynchronous cleanup?
- Is reactivity preserved and derived state computed?
- Is Pinia used only for genuinely shared state?
- Is API logic separated from UI and are failures explicit?
- Are loading, error, and empty states handled?
- Are access boundaries enforced by the backend?
- Are requests, subscriptions, and retained data bounded or cleaned up?
- Are keyboard access and focus behavior usable?
- Are important behaviors tested, and does each abstraction simplify the feature?
