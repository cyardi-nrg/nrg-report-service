import { google } from 'googleapis';
import { Readable } from 'node:stream';

// Server-only — never import from a Client Component. Auths as the
// service account (see app/SETUP.md for how that's created); that
// service account must be shared as an Editor on whichever Drive folder
// it needs to write into (NRG's real project folders, per
// projects.google_drive_folder_id — see HANDOVER Section "Google Drive
// folder linking").
function getDriveClient() {
  const privateKey = (process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY ?? '').replace(/\\n/g, '\n');

  const auth = new google.auth.JWT({
    email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    key: privateKey,
    scopes: ['https://www.googleapis.com/auth/drive'],
  });

  return google.drive({ version: 'v3', auth });
}

/**
 * Uploads a file into a Drive folder and returns its file ID — the
 * durable link stored on documents.google_drive_file_id (0002). Never
 * derive identity from the filename or folder name later; this ID is
 * the only thing to trust.
 */
export async function uploadFileToDrive(params: {
  folderId: string;
  filename: string;
  mimeType: string;
  buffer: Buffer;
}): Promise<{ fileId: string; webViewLink: string }> {
  const drive = getDriveClient();

  const res = await drive.files.create({
    requestBody: {
      name: params.filename,
      parents: [params.folderId],
    },
    media: {
      mimeType: params.mimeType,
      body: Readable.from(params.buffer),
    },
    fields: 'id, webViewLink',
  });

  if (!res.data.id) {
    throw new Error('Drive upload succeeded but returned no file ID — unexpected API response.');
  }

  return { fileId: res.data.id, webViewLink: res.data.webViewLink ?? '' };
}

/** Downloads a Drive file's raw bytes — used by the extraction pipeline to read a document back. */
export async function downloadFileFromDrive(fileId: string): Promise<Buffer> {
  const drive = getDriveClient();
  const res = await drive.files.get(
    { fileId, alt: 'media' },
    { responseType: 'arraybuffer' },
  );
  return Buffer.from(res.data as ArrayBuffer);
}

/**
 * Creates a new project subfolder under the root folder — mirrors the
 * "New projects should auto-create their Drive folder via a service
 * account" instruction from HANDOVER-FOR-BUILD-SESSION.md. Returns the
 * folder ID to store on projects.google_drive_folder_id.
 */
export async function createProjectFolder(params: {
  parentFolderId: string;
  projectName: string;
}): Promise<string> {
  const drive = getDriveClient();
  const res = await drive.files.create({
    requestBody: {
      name: params.projectName,
      mimeType: 'application/vnd.google-apps.folder',
      parents: [params.parentFolderId],
    },
    fields: 'id',
  });

  if (!res.data.id) {
    throw new Error('Drive folder creation succeeded but returned no folder ID.');
  }

  return res.data.id;
}
