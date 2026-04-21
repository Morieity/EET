/**
 * Chat API service
 */

export async function sendChatMessage(question, conversationId, signal) {
  const body = { question };
  if (conversationId) body.conversation_id = conversationId;

  return fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}
