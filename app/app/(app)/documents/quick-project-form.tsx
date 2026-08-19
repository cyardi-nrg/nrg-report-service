'use client';

import { useRef } from 'react';
import { createQuickProject } from './actions';

export function QuickProjectForm() {
  const formRef = useRef<HTMLFormElement>(null);

  return (
    <form
      ref={formRef}
      action={async (formData) => {
        await createQuickProject(formData);
        formRef.current?.reset();
      }}
      style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
    >
      <input name="customer_name" placeholder="Customer / company name" required style={inputStyle} />
      <input name="site_address" placeholder="Site address (optional)" style={inputStyle} />
      <select name="project_type" style={inputStyle} defaultValue="residential_subsidy">
        <option value="residential_subsidy">Residential Subsidy</option>
        <option value="commercial_industrial">Commercial/Industrial</option>
      </select>
      <button type="submit" style={buttonStyle}>+ Create Project</button>
    </form>
  );
}

const inputStyle: React.CSSProperties = { padding: '9px 11px', borderRadius: 7, border: '1px solid #e7e9f3', fontSize: 13.5 };
const buttonStyle: React.CSSProperties = {
  padding: '9px 11px', borderRadius: 7, border: 'none', background: '#1f3bb8', color: '#fff', fontWeight: 700, fontSize: 13, cursor: 'pointer',
};
