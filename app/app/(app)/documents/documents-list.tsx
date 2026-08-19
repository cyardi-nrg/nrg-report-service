'use client';

import { useState, useTransition } from 'react';
import { readDocumentWithAI } from './actions';

type DocRow = {
  document_id: string;
  document_type: string | null;
  ai_status: string;
  ai_confidence: number | null;
  upload_date: string;
  project_label: string;
};

const STATUS_COLOR: Record<string, string> = {
  pending: '#9296a3',
  processing: '#E3A100',
  extracted: '#16a34a',
  failed: '#dc2626',
  confirmed: '#1f3bb8',
};

export function DocumentsList({ documents }: { documents: DocRow[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {documents.length === 0 ? (
        <p style={{ fontSize: 13, color: '#9296a3' }}>No documents uploaded yet.</p>
      ) : (
        documents.map((doc) => <DocumentRow key={doc.document_id} doc={doc} />)
      )}
    </div>
  );
}

function DocumentRow({ doc }: { doc: DocRow }) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 10,
        padding: '10px 12px',
        background: '#fff',
        border: '1px solid #e7e9f3',
        borderRadius: 9,
        fontSize: 13,
      }}
    >
      <div>
        <div style={{ fontWeight: 700, color: '#161a2e' }}>
          {doc.document_type ? doc.document_type.replace(/_/g, ' ') : 'Not yet classified'}
        </div>
        <div style={{ fontSize: 11.5, color: '#9296a3', marginTop: 2 }}>
          {doc.project_label} · {new Date(doc.upload_date).toLocaleDateString()}
          {doc.ai_confidence != null ? ` · ${Math.round(doc.ai_confidence * 100)}% confident` : ''}
        </div>
        {error ? <div style={{ color: '#dc2626', fontSize: 11.5, marginTop: 2 }}>{error}</div> : null}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            fontSize: 10.5,
            fontWeight: 700,
            padding: '3px 9px',
            borderRadius: 100,
            color: '#fff',
            background: STATUS_COLOR[doc.ai_status] ?? '#9296a3',
          }}
        >
          {doc.ai_status}
        </span>
        {(doc.ai_status === 'pending' || doc.ai_status === 'failed') && (
          <button
            disabled={isPending}
            onClick={() =>
              startTransition(async () => {
                setError(null);
                try {
                  await readDocumentWithAI(doc.document_id);
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Read failed.');
                }
              })
            }
            style={{
              border: '1px solid #1f3bb8', background: '#eef1fb', color: '#1f3bb8',
              borderRadius: 7, padding: '5px 10px', fontSize: 11.5, fontWeight: 700, cursor: 'pointer',
            }}
          >
            {isPending ? 'Reading…' : 'Read with AI'}
          </button>
        )}
      </div>
    </div>
  );
}
