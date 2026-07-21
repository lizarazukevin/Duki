# Duki Frontend

The mobile-first Duki web client uses Next.js App Router, TypeScript, Tailwind CSS,
Biome, and Supabase Auth.

Configure these public values in the PyCharm run configuration and in the deployment
provider; no dotenv file is required:

- `NEXT_PUBLIC_API_BASE_URL` — backend origin, such as `http://127.0.0.1:8000`
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — browser-safe Supabase publishable key

From `frontend/`, run `npm run dev` for local development, `npm run check` for lint and
strict type checking, and `npm run build` for the production build.
