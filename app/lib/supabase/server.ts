import { createServerClient, type CookieOptions } from '@supabase/ssr';
import { createClient as createSupabaseClient } from '@supabase/supabase-js';
import { cookies } from 'next/headers';

type CookieToSet = { name: string; value: string; options: CookieOptions };

// Used from Server Components / Route Handlers / Server Actions — reads
// and writes the session via cookies, respects Row-Level Security as the
// signed-in user (never elevates privilege).
export function createClient() {
  const cookieStore = cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Called from a Server Component that can't set cookies —
            // fine as long as middleware.ts is refreshing the session,
            // which it is (see middleware.ts).
          }
        },
      },
    },
  );
}

// Elevated, server-only client for the handful of routes that must act
// beyond what RLS would allow the signed-in user directly (e.g. writing
// an AI extraction result as the system, not as any one employee).
// NEVER import this from a Client Component or expose it to the browser.
export function createServiceRoleClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}
