import { signOut } from '../login/actions';
import { getCurrentEmployee } from '@/lib/current-employee';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const employee = await getCurrentEmployee();

  return (
    <div style={{ minHeight: '100vh', background: '#f6f8ff' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 22px',
          background: '#fff',
          borderBottom: '1px solid #e7e9f3',
        }}
      >
        <div style={{ fontWeight: 800, color: '#161a2e' }}>NRG SolarConnect</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 13, color: '#6b7280' }}>
          {employee ? <span>{employee.name} · {employee.role}</span> : <span style={{ color: '#dc2626' }}>No staff record linked</span>}
          <form action={signOut}>
            <button
              type="submit"
              style={{ border: '1px solid #e7e9f3', background: '#fff', borderRadius: 7, padding: '6px 12px', fontSize: 12.5, cursor: 'pointer' }}
            >
              Sign out
            </button>
          </form>
        </div>
      </header>
      <main style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px' }}>{children}</main>
    </div>
  );
}
