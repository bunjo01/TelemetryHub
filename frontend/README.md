# TelemetryHub frontend

Vue 3, JavaScript, Pinia, Vue Router, Sass and Biome. Use Node.js 24 LTS and npm.

```sh
cd frontend
npm ci
npm run dev
```

Start FastAPI separately on `127.0.0.1:8000`. Vite forwards `/api/*` to the backend, removing `/api`. Open the URL printed by Vite.

- `/`: login with an existing account.
- `/profile`: email, role, sign out and role-specific actions.
- System administrators can create companies through a popup.
- Administrators can invite owners using an email and a searchable company dropdown. The resulting registration link has a Copy link button and manual-copy fallback; no email is sent.
- `/register#token=...`: invitation-based registration with read-only email, password and confirmation. Successful registration returns to login. Owner and member invitations use the same form.
- Member invitations remain a disabled placeholder.

Login tokens are held in memory only. Refreshing or closing the page requires another login. Passwords are never persisted. Authentication loads `/auth/me` before entering the profile. The backend enforces permissions.

Invitation secrets remain in the registration URL fragment until registration succeeds, so refreshing works. They are not stored in local/session storage or sent in API URLs; preview and acceptance send the token in a JSON body. Share the link only with its intended recipient. Signed-in visitors must explicitly sign out before registering.

## Commands

- `npm run check`: Biome lint and formatting.
- `npm run check:fix`: safe Biome fixes.
- `npm run build`: production build.
- `npm run preview`: local production preview, including the development API proxy.
- `npm test`: API boundary and session behavior tests.
- `npx playwright install chromium`: install the browser once.
- `npm run test:e2e`: browser flows using mocked API responses; no database needed.

For production, serve `dist/` with HTTPS, route `/api/*` to FastAPI with the prefix stripped, and fall back to `index.html` for frontend routes. Vite's proxy is not included in the production assets.

## Structure

- `src/api/`: bounded HTTP transport, response validation and domain requests.
- `src/stores/auth.js`: shared in-memory session and cancellation.
- `src/router.js`: route access and page titles.
- `src/views/`: login, registration and profile with local form state.
- `src/components/`: decorative orbital illustration.
- `src/styles.scss`: shared styles and design tokens.

See [the engineering guide](frontend-engineering-guide.md). Biome checks Vue/JS/HTML/JSON; Vite compiles Sass. Browser tests mock the backend; they do not validate a live database or backend integration.
