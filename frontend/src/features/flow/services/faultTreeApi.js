/**
 * Fault Tree API service
 */

export async function getFaultTrees() {
  const resp = await fetch('/api/fault-trees');
  if (!resp.ok) throw new Error(`Failed to fetch fault trees: ${resp.status}`);
  return resp.json();
}

export async function getFaultTree(id) {
  const resp = await fetch(`/api/fault-trees/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`Failed to fetch fault tree: ${resp.status}`);
  return resp.json();
}

export async function getFaultTreeByConversation(conversationId) {
  const resp = await fetch(`/api/fault-trees/conversation/${encodeURIComponent(conversationId)}`);
  if (!resp.ok) throw new Error(`Failed to fetch fault tree by conversation: ${resp.status}`);
  return resp.json();
}

export async function updateFaultTree(id, payload) {
  const resp = await fetch(`/api/fault-trees/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || err.message || `Save failed: ${resp.status}`);
  }
  return resp.json();
}

export async function deleteFaultTree(id) {
  const resp = await fetch(`/api/fault-trees/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed to delete fault tree: ${resp.status}`);
  return resp;
}
