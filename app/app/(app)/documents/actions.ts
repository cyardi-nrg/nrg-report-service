'use server';

import { revalidatePath } from 'next/cache';
import { createClient } from '@/lib/supabase/server';
import { getCurrentEmployee } from '@/lib/current-employee';
import { createProjectFolder, uploadFileToDrive, downloadFileFromDrive } from '@/lib/google-drive';
import { classifyDocument, extractElectricalTestRecord } from '@/lib/ai-extraction';

// document_type values that map to the one type-specific extractor
// built so far (see lib/ai-extraction.ts) — everything else stops at
// classification until its own extractor is built.
const CEIG_TYPES = new Set(['ceig_test_inspection_application', 'ceig_inspection_report']);

export async function createQuickProject(formData: FormData) {
  const customerName = String(formData.get('customer_name') ?? '').trim();
  const siteAddress = String(formData.get('site_address') ?? '').trim();
  const projectType = String(formData.get('project_type') ?? 'residential_subsidy');

  if (!customerName) throw new Error('Customer name is required.');

  const supabase = createClient();

  const { data: customer, error: customerError } = await supabase
    .from('customers')
    .insert({ name: customerName })
    .select('customer_id')
    .single();
  if (customerError) throw new Error(`Could not create customer: ${customerError.message}`);

  let driveFolderId: string | null = null;
  const rootFolderId = process.env.GOOGLE_DRIVE_ROOT_FOLDER_ID;
  if (rootFolderId) {
    // Best-effort — a project can exist before its Drive folder does,
    // but we try eagerly so uploads have somewhere real to land.
    try {
      driveFolderId = await createProjectFolder({ parentFolderId: rootFolderId, projectName: customerName });
    } catch {
      driveFolderId = null;
    }
  }

  const { error: projectError } = await supabase.from('projects').insert({
    customer_id: customer.customer_id,
    site_address: siteAddress || null,
    project_type: projectType,
    google_drive_folder_id: driveFolderId,
  });
  if (projectError) throw new Error(`Could not create project: ${projectError.message}`);

  revalidatePath('/documents');
}

export async function uploadDocument(formData: FormData) {
  const file = formData.get('file') as File | null;
  const projectId = String(formData.get('project_id') ?? '');

  if (!file || file.size === 0) throw new Error('Choose a file to upload.');
  if (!projectId) throw new Error('Pick a project first.');

  const employee = await getCurrentEmployee();
  if (!employee) throw new Error('Your login is not linked to a staff record yet — ask an admin.');

  const supabase = createClient();

  const { data: project, error: projectLookupError } = await supabase
    .from('projects')
    .select('google_drive_folder_id')
    .eq('project_id', projectId)
    .single();
  if (projectLookupError || !project) throw new Error('Project not found.');
  if (!project.google_drive_folder_id) {
    throw new Error('This project has no Drive folder linked yet — set GOOGLE_DRIVE_ROOT_FOLDER_ID and recreate the project, or link a folder manually.');
  }

  const buffer = Buffer.from(await file.arrayBuffer());

  const { fileId } = await uploadFileToDrive({
    folderId: project.google_drive_folder_id,
    filename: file.name,
    mimeType: file.type || 'application/octet-stream',
    buffer,
  });

  const { error: insertError } = await supabase.from('documents').insert({
    project_id: projectId,
    google_drive_file_id: fileId,
    uploaded_by: employee.employee_id,
    ai_status: 'pending',
  });
  if (insertError) throw new Error(`Uploaded to Drive but failed to record it: ${insertError.message}`);

  revalidatePath('/documents');
}

/**
 * Reads a document back with AI: always classifies (document_type +
 * confidence, writes onto documents itself); for the one type-specific
 * extractor built so far (CEIG test records), also writes the
 * structured fields into electrical_test_records. Every other type
 * stops at classification — see lib/ai-extraction.ts for why CEIG was
 * picked first.
 */
export async function readDocumentWithAI(documentId: string) {
  const supabase = createClient();

  const { data: doc, error: docError } = await supabase
    .from('documents')
    .select('document_id, project_id, google_drive_file_id')
    .eq('document_id', documentId)
    .single();
  if (docError || !doc) throw new Error('Document not found.');

  await supabase.from('documents').update({ ai_status: 'processing' }).eq('document_id', documentId);

  try {
    const buffer = await downloadFileFromDrive(doc.google_drive_file_id);
    // Real MIME type isn't stored on documents today — inferred as
    // JPEG for now (see the PDF caveat in lib/ai-extraction.ts).
    const mimeType = 'image/jpeg';

    const classification = await classifyDocument({
      buffer,
      mimeType,
      filename: doc.google_drive_file_id,
    });

    await supabase
      .from('documents')
      .update({
        document_type: classification.document_type,
        ai_confidence: classification.ai_confidence,
        ai_status: 'extracted',
      })
      .eq('document_id', documentId);

    if (CEIG_TYPES.has(classification.document_type)) {
      const extraction = await extractElectricalTestRecord({ buffer, mimeType });
      await supabase.from('electrical_test_records').insert({
        project_id: doc.project_id,
        application_document_id: documentId,
        file_no: extraction.file_no,
        consumer_number: extraction.consumer_number,
        inspection_date: extraction.inspection_date,
        issuing_authority: extraction.issuing_authority,
        megger_r_y: extraction.megger_r_y,
        megger_y_b: extraction.megger_y_b,
        megger_r_b: extraction.megger_r_b,
        megger_ryb_earth: extraction.megger_ryb_earth,
        earth_pit_resistance: extraction.earth_pit_resistance,
        contractor_license_no: extraction.contractor_license_no,
        supervisor_license_no: extraction.supervisor_license_no,
        status: extraction.status,
        ai_confidence: extraction.ai_confidence,
      });
    }
  } catch (err) {
    await supabase.from('documents').update({ ai_status: 'failed' }).eq('document_id', documentId);
    throw err;
  }

  revalidatePath('/documents');
}
