/**
 * File API service
 */

export async function getFiles() {
  const resp = await fetch('/api/files');
  if (!resp.ok) throw new Error(`Failed to fetch files: ${resp.status}`);
  return resp.json();
}

export async function uploadFile(formData) {
  const resp = await fetch('/api/files', {
    method: 'POST',
    body: formData,
  });
  const data = await resp.json();
  if (!resp.ok && resp.status !== 202) {
    throw new Error(data.error || `Upload failed: ${resp.status}`);
  }
  return { data, status: resp.status };
}

export async function deleteFile(fileName) {
  const resp = await fetch(`/api/files/${encodeURIComponent(fileName)}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed to delete file: ${resp.status}`);
  return resp;
}

export async function openUploadsFolder() {
  const resp = await fetch('/api/files/open-folder', { method: 'POST' });
  if (!resp.ok) throw new Error(`Failed to open folder: ${resp.status}`);
  return resp.json();
}
