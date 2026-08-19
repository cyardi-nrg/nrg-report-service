import { createClient } from '@/lib/supabase/server';
import { QuickProjectForm } from './quick-project-form';
import { UploadForm } from './upload-form';
import { DocumentsList } from './documents-list';

export const dynamic = 'force-dynamic';

export default async function DocumentsPage() {
  const supabase = createClient();

  const { data: projects } = await supabase
    .from('projects')
    .select('project_id, site_address, customers(name)')
    .order('created_at', { ascending: false });

  const projectOptions = (projects ?? []).map((p: any) => ({
    project_id: p.project_id,
    label: p.customers?.name ? `${p.customers.name}${p.site_address ? ' — ' + p.site_address : ''}` : p.project_id,
  }));

  const { data: documents } = await supabase
    .from('documents')
    .select('document_id, document_type, ai_status, ai_confidence, upload_date, projects(customers(name))')
    .order('upload_date', { ascending: false })
    .limit(30);

  const documentRows = (documents ?? []).map((d: any) => ({
    document_id: d.document_id,
    document_type: d.document_type,
    ai_status: d.ai_status,
    ai_confidence: d.ai_confidence,
    upload_date: d.upload_date,
    project_label: d.projects?.customers?.name ?? 'Unknown project',
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 19, fontWeight: 800, color: '#161a2e', margin: 0 }}>Documents</h1>
        <p style={{ fontSize: 12.5, color: '#6b7280', marginTop: 4 }}>
          Upload → saved to the project's real Google Drive folder → read with AI when you're ready.
        </p>
      </div>

      {projectOptions.length === 0 ? (
        <Card title="Start here — create your first project">
          <QuickProjectForm />
        </Card>
      ) : (
        <>
          <Card title="Upload a document">
            <UploadForm projects={projectOptions} />
          </Card>
          <Card title="Recent uploads">
            <DocumentsList documents={documentRows} />
          </Card>
          <Card title="Add another project">
            <QuickProjectForm />
          </Card>
        </>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e7e9f3', borderRadius: 12, padding: '16px 18px' }}>
      <h2 style={{ fontSize: 13.5, fontWeight: 800, color: '#161a2e', margin: '0 0 12px' }}>{title}</h2>
      {children}
    </div>
  );
}
