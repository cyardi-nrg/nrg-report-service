import { redirect } from 'next/navigation';

// Root just forwards into the app — middleware.ts already enforces the
// real auth gate, this only decides where a signed-in visit lands.
export default function RootPage() {
  redirect('/documents');
}
