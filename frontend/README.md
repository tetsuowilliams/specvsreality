# SpecVsReality Frontend

SvelteKit UI for SpecVsReality. See the [root README](../README.md) for setup.

## Native development

```bash
cp .env.example .env
npm ci
npm run dev
```

Dev server: http://localhost:5180 (port 5173 is reserved for Opik).

Set `PUBLIC_API_BASE_URL` in `.env` (default `http://localhost:8800`).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server |
| `npm run build` | Production build |
| `npm test` | Vitest unit tests |
| `npm run check` | svelte-check typecheck |
