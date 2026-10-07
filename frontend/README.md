# IoTMonitor frontend

Minimal Vue 3 starter using plain JavaScript, Pinia, Vite, Sass, and Biome.
Use Node.js 24 LTS and npm.

```sh
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. This starter displays a welcome page and does not require the backend.

## Commands

- `npm run check`: lint and formatting checks.
- `npm run check:fix`: apply safe Biome fixes.
- `npm run build`: production build into `dist/`.
- `npm run preview`: preview the production build.

## Structure

- `src/main.js`: Vue application and Pinia setup.
- `src/App.vue`: minimal welcome page.
- `src/styles.scss`: global styles.
- `vite.config.js`: Vue plugin configuration.

No routes, feature stores, API integration, or test runner are configured.
See [the engineering guide](frontend-engineering-guide.md) for conventions.
Biome checks JavaScript, Vue, HTML, and JSON; Sass is compiled by Vite.
