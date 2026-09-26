# IoTMonitor frontend

React with strict TypeScript, Vite, SCSS, and Biome. Use Node.js 24 LTS and npm.

Run from `frontend/`:

```sh
npm ci
npm run dev
```

Open the local URL printed by Vite (normally http://localhost:5173).

## Commands

```sh
npm run check       # Biome lint, formatting, and import checks
npm run check:fix   # Apply safe Biome fixes
npm run format     # Format supported files
npm run typecheck  # TypeScript checks
npm run build      # TypeScript checks and production build into dist/
npm run preview    # Preview the production build locally
```

Edit `src/App.tsx` and `src/App.scss` to start building the UI. Global styles live
in `src/styles.scss`. Vite compiles SCSS using Sass.

Biome checks TypeScript, TSX, and JSON. SCSS is excluded because Biome does not
yet provide stable SCSS linting/formatting; the production build validates Sass
compilation. No backend connection is configured yet.
