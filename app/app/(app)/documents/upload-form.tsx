'use client';

import { useRef, useState } from 'react';
import { uploadDocument } from './actions';

export function UploadForm({ projects }: { projects: { project_id: string; label: string }[] }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      ref={formRef}
      action={async (formData) => {
        setPending(true);
        setError(null);
        try {
          await uploadDocument(formData);
          formRef.current?.reset();
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Upload failed.');
        } finally {
          setPending(false);
        }
      }}
      style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
    >
      <select name="project_id" required style={inputStyle}>
        <option value="">Select a project…</option>
        {projects.map((p) => (
          <option key={p.project_id} value={p.project_id}>{p.label}</option>
        ))}
      </select>
      <input type="file" name="file" required accept="image/*,application/pdf" style={inputStyle} />
      {error ? <p style={{ color: '#dc2626', fontSize: 12.5, margin: 0 }}>{error}</p> : null}
      <button type="submit" disabled={pending} style={buttonStyle}>
        {pending ? 'Uploading…' : 'Upload to Drive'}
      </button>
    </form>
  );
}

const inputStyle: React.CSSProperties = { padding: '9px 11px', borderRadius: 7, border: '1px solid #e7e9f3', fontSize: 13.5 };
const buttonStyle: React.CSSProperties = {
  padding: '9px 11px', borderRadius: 7, border: 'none', background: '#1f3bb8', color: '#fff', fontWeight: 700, fontSize: 13, cursor: 'pointer',
};
