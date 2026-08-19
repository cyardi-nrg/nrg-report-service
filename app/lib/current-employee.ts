import { createClient } from '@/lib/supabase/server';

export type CurrentEmployee = {
  employee_id: string;
  name: string;
  role: string;
  is_owner: boolean;
  is_admin: boolean;
};

/**
 * Resolves the signed-in Supabase Auth user to their employees row via
 * employees.auth_user_id (0045). Returns null if this person signed in
 * but has no employees row yet — an admin needs to add them to the
 * roster (People screen) before they can do anything past login.
 */
export async function getCurrentEmployee(): Promise<CurrentEmployee | null> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return null;

  const { data, error } = await supabase
    .from('employees')
    .select('employee_id, name, role, is_owner, is_admin')
    .eq('auth_user_id', user.id)
    .maybeSingle();

  if (error || !data) return null;
  return data as CurrentEmployee;
}
