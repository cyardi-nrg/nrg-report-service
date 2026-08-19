'use client';

import { Suspense } from 'react';
import { useFormState, useFormStatus } from 'react-dom';
import { useSearchParams } from 'next/navigation';
import { signIn, type LoginState } from './actions';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} style={styles.button}>
      {pending ? 'Signing in…' : 'Sign in'}
    </button>
  );
}

export default function LoginPage() {
  // useSearchParams() opts a page out of static prerendering unless it's
  // wrapped in Suspense — without this, `next build` fails outright.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const searchParams = useSearchParams();
  const next = searchParams.get('next') ?? '/documents';
  const [state, formAction] = useFormState<LoginState, FormData>(signIn, undefined);

  return (
    <main style={styles.page}>
      <form action={formAction} style={styles.card}>
        <div style={styles.brand}>NRG SolarConnect</div>
        <p style={styles.sub}>Sign in with the email and password your admin set up for you.</p>

        <input type="hidden" name="next" value={next} />

        <label style={styles.label}>
          Email
          <input type="email" name="email" required autoComplete="email" style={styles.input} />
        </label>

        <label style={styles.label}>
          Password
          <input type="password" name="password" required autoComplete="current-password" style={styles.input} />
        </label>

        {state?.error ? <p style={styles.error}>{state.error}</p> : null}

        <SubmitButton />
      </form>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(160deg,#f6f8ff 0%,#eef1fb 60%,#f7f5ff 100%)',
  },
  card: {
    width: 340,
    background: '#fff',
    border: '1px solid #e7e9f3',
    borderRadius: 14,
    padding: '28px 26px',
    boxShadow: '0 24px 48px -18px rgba(22,41,138,.15)',
  },
  brand: { fontWeight: 800, fontSize: 19, color: '#161a2e' },
  sub: { fontSize: 12.5, color: '#6b7280', marginTop: 4, marginBottom: 20 },
  label: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12.5, fontWeight: 600, color: '#161a2e', marginBottom: 14 },
  input: { padding: '10px 12px', borderRadius: 8, border: '1px solid #e7e9f3', fontSize: 14 },
  error: { color: '#dc2626', fontSize: 12.5, marginBottom: 12 },
  button: {
    width: '100%',
    padding: '11px',
    borderRadius: 9,
    border: 'none',
    background: '#1f3bb8',
    color: '#fff',
    fontWeight: 700,
    fontSize: 13.5,
    cursor: 'pointer',
    marginTop: 4,
  },
};
