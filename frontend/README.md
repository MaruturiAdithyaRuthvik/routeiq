# RouteIQ frontend

The RouteIQ frontend is a React 18, Vite, TypeScript, and Tailwind application. It uses the API contract types in `src/api/types.ts` and calls the backend through `src/api/client.ts`.

## Run locally

```sh
npm install
npm run dev
```

By default, the app uses the backend at `/api/v1`. Set `VITE_API_BASE_URL` to override that base path. See `.env.example` for the supported environment variables.

For parallel UI development, run the deterministic, synthetic contract fixtures:

```sh
npm run dev:fixtures
```

Fixture mode is opt-in and development-only. It is off by default, and production builds always use the API even if `VITE_USE_FIXTURES=true` is set.

## Checks

```sh
npm run lint
npm run typecheck
npm run test
npm run build
```

The hidden `/design` route previews tokens and components in both themes. Theme preference follows the system until a user chooses light or dark mode.
