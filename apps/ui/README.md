# slick-ui

The local web dashboard (Next.js App Router + TypeScript + Tailwind). Mobile-friendly,
LAN-only in v1, gated by a single shared password (`UI_ADMIN_PASSWORD`).

## Routes

- `/` — dashboard overview (businesses, agents, tasks, cost)
- `/businesses` + `/businesses/[slug]` — compartment rooms
- `/agents` + `/agents/[id]` — registry + inspector
- `/tasks` — task list + status
- `/costs` — budget meter + breakdown + recent events
- `/spaceship` — placeholder for the future immersive UI
- `/login` — password gate

## Data

Client components fetch the gateway at `NEXT_PUBLIC_GATEWAY_URL` (default
`http://localhost:8000`). CORS is open in v1 (LAN-only).

## Local dev

```bash
npm install
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000 npm run dev
```

See `docs/10-ui-vision.md`.
