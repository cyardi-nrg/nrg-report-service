#!/usr/bin/env node
// Nightly Supabase backup, free-tier-friendly.
//
// Supabase's own automatic daily backups / point-in-time recovery are a
// paid-plan feature. This does the same job for free: pg_dump the whole
// database to a single compressed file, then upload it into a Google
// Drive folder using the SAME service account NRG SolarConnect already
// uses for document storage (see nrg-solar-connect-app/lib/google-drive.ts)
// — no new credentials to create, just the existing ones added as GitHub
// secrets on this repo. Meant to run from
// .github/workflows/backup-supabase.yml on a daily schedule.
//
// Required environment variables (set as GitHub Actions secrets):
//   SUPABASE_DB_URL                  postgres://... direct connection string
//                                     (Supabase dashboard -> Project Settings
//                                     -> Database -> Connection string ->
//                                     "URI", direct connection, NOT the
//                                     pooler/pgbouncer one -- pg_dump needs
//                                     a plain session, not a transaction pool)
//   GOOGLE_SERVICE_ACCOUNT_EMAIL      same value as the app's own env var
//   GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY  same value as the app's own env var
//   GOOGLE_DRIVE_BACKUP_FOLDER_ID     a Shared Drive folder the service
//                                     account can write into (same rule as
//                                     the app's own uploads -- a personal
//                                     "My Drive" folder will not work, see
//                                     lib/google-drive.ts's own comment)
//
// Optional:
//   BACKUP_RETENTION_COUNT           how many backups to keep in Drive
//                                     before pruning the oldest (default 30
//                                     -- about a month of nightly runs)

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createReadStream, statSync, unlinkSync } from 'node:fs';
import { google } from 'googleapis';

const execFileAsync = promisify(execFile);

function requireEnv(name) {
  const v = process.env[name];
  if (!v) {
    console.error(`Missing required environment variable: ${name}`);
    process.exit(1);
  }
  return v;
}

function driveClient() {
  const privateKey = requireEnv('GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY').replace(/\\n/g, '\n');
  const auth = new google.auth.JWT({
    email: requireEnv('GOOGLE_SERVICE_ACCOUNT_EMAIL'),
    key: privateKey,
    scopes: ['https://www.googleapis.com/auth/drive'],
  });
  return google.drive({ version: 'v3', auth });
}

async function dumpDatabase(dbUrl, outPath) {
  console.log('Running pg_dump...');
  // Custom format: compressed, and the only format pg_restore can do a
  // selective/parallel restore from later if a full restore isn't wanted.
  await execFileAsync('pg_dump', [dbUrl, '--format=custom', '--no-owner', '--no-privileges', '--file', outPath], {
    maxBuffer: 1024 * 1024 * 1024,
  });
  const { size } = statSync(outPath);
  console.log(`Dump complete: ${outPath} (${(size / 1024 / 1024).toFixed(1)} MB)`);
}

async function uploadToDrive(drive, folderId, filePath, filename) {
  console.log(`Uploading ${filename} to Drive folder ${folderId}...`);
  const res = await drive.files.create({
    requestBody: { name: filename, parents: [folderId] },
    media: { mimeType: 'application/octet-stream', body: createReadStream(filePath) },
    fields: 'id, webViewLink',
    supportsAllDrives: true,
  });
  console.log(`Uploaded: ${res.data.webViewLink}`);
  return res.data.id;
}

async function pruneOldBackups(drive, folderId, keep) {
  const res = await drive.files.list({
    q: `'${folderId}' in parents and trashed = false`,
    orderBy: 'createdTime desc',
    fields: 'files(id, name, createdTime)',
    pageSize: 1000,
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });
  const files = res.data.files ?? [];
  const toDelete = files.slice(keep);
  if (!toDelete.length) return;
  console.log(`Pruning ${toDelete.length} backup(s) older than the most recent ${keep}...`);
  for (const f of toDelete) {
    await drive.files.delete({ fileId: f.id, supportsAllDrives: true });
    console.log(`  deleted ${f.name}`);
  }
}

async function main() {
  const dbUrl = requireEnv('SUPABASE_DB_URL');
  const folderId = requireEnv('GOOGLE_DRIVE_BACKUP_FOLDER_ID');
  const keep = parseInt(process.env.BACKUP_RETENTION_COUNT ?? '30', 10);

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `nrg-solarconnect-${stamp}.dump`;
  const outPath = `/tmp/${filename}`;

  await dumpDatabase(dbUrl, outPath);

  const drive = driveClient();
  await uploadToDrive(drive, folderId, outPath, filename);
  await pruneOldBackups(drive, folderId, keep);

  unlinkSync(outPath);
  console.log('Backup complete.');
}

main().catch((err) => {
  console.error('Backup failed:', err);
  process.exit(1);
});
