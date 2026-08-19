import { createBrowserClient } from '@supabase/ssr';

// Used from Client Components — reads the two public env vars only,
// never the service_role key.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
