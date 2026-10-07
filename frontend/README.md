# TelemetryHub frontend

Vue 3, JavaScript, Pinia, Vue Router, Sass and Biome. Use Node.js 24 LTS and npm.

```sh
cd frontend
npm ci
npm run dev
```

Start FastAPI separately on `127.0.0.1:8000`. Vite forwards `/api/*` to the backend, removing `/api`. Open the URL printed by Vite.

- `/`: login with an existing account.
- `/profile`: protected landing page after signing in.

Tokens are held in memory only. Refreshing or closing the page requires another login. Passwords are never persisted. Authentication loads `/auth/me` before entering the profile. The backend enforces permissions.

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
- `src/views/`: login and a minimal authenticated landing page.
- `src/components/`: decorative orbital illustration.
- `src/styles.scss`: shared styles and design tokens.

See [the engineering guide](frontend-engineering-guide.md). Biome checks Vue/JS/HTML/JSON; Vite compiles Sass. Browser tests mock the backend; they do not validate a live database or backend integration.
