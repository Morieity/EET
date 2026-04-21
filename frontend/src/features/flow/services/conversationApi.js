/**
 * Conversation API service
 */

export async function getConversations() {
  const resp = await fetch('/api/conversations');
  if (!resp.ok) throw new Error(`Failed to fetch conversations: ${resp.status}`);
  return resp.json();
}

export async function getConversation(id) {
  const resp = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`Failed to fetch conversation: ${resp.status}`);
  return resp.json();
}

export async function deleteConversation(id) {
  const resp = await fetch(`/api/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!resp.ok) throw new Error(`Failed to delete conversation: ${resp.status}`);
  return resp;
}
