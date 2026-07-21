# Duky Frontend

The mobile-first Duky web client uses Next.js App Router, TypeScript, Tailwind CSS,
Biome, and Supabase Auth.

Configure these public values in the PyCharm run configuration and in the deployment
provider; no dotenv file is required:

- `NEXT_PUBLIC_API_BASE_URL` — backend origin, such as `http://127.0.0.1:8000`
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — browser-safe Supabase publishable key

Allow `http://localhost:3000/auth/callback` in the Supabase Auth redirect URL list.
For a deployed frontend, add its callback URL there and set the backend
`ALLOWED_CORS_ORIGINS` value to the frontend origin.

From `frontend/`, run `npm run dev` for local development, `npm run check` for lint and
strict type checking, and `npm run build` for the production build.
