// Browser-to-Django contract. The Django server is responsible for calling
// external AI providers; never put provider credentials in frontend code.
const API = {
  send: '/api/chat/',
  conversations: '/api/conversations/',
  models: '/api/models/',
};

function csrfToken() {
  const cookie = document.cookie.split('; ').find(part => part.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

async function request(url, options = {}) {
  let response;
  try {
    response = await fetch(url, { credentials: 'same-origin', ...options });
  } catch {
    throw new Error('Cannot connect to KilatChat. Check your connection and try again.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(data?.error || 'Please log in to use KilatChat.');
    }
    if (response.status === 404 || response.status === 405) {
      throw new Error('The chat API is not configured yet. Connect the Django endpoint to an AI provider.');
    }
    throw new Error(data?.error || data?.detail || `Request failed (HTTP ${response.status}).`);
  }
  return data;
}

export async function sendChatMessage({ message, model, conversationId, requestId, onDelta, onMeta }) {
  let response;
  try {
    response = await fetch(API.send, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream, application/json', 'X-CSRFToken': csrfToken() },
    body: JSON.stringify({
      message,
      model,
      conversation_id: conversationId,
      request_id: requestId,
    }),
  });
  } catch {
    throw new Error('Cannot connect to KilatChat. Check your connection and try again.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    if (response.status === 404 || response.status === 405) {
      throw new Error('The chat API is not configured yet. Connect the Django endpoint to an AI provider.');
    }
    if (response.status === 401 || response.status === 403) {
      throw new Error(data?.error || 'Please log in to use KilatChat.');
    }
    throw new Error(data?.error || data?.detail || `Request failed (HTTP ${response.status}).`);
  }
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('text/event-stream')) {
    const data = await response.json().catch(() => null);
    if (!data || data.conversation_id == null || typeof data.reply !== 'string') {
      throw new Error('Unexpected chat response. Expected conversation_id and reply.');
    }
    onMeta?.(data);
    onDelta?.(data.reply);
    return data;
  }
  if (!response.body) throw new Error('Streaming is not available in this browser.');

  // SSE frames can be fragmented across network reads, including UTF-8 characters.
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let reply = '';
  let meta = {};
  let finished = false;
  function processFrame(frame) {
    const lines = frame.split(/\r?\n/);
    const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim() || 'message';
    const payload = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
    if (!payload || payload === '[DONE]') return;
    let data;
    try { data = JSON.parse(payload); }
    catch { throw new Error('Malformed event received from the chat server.'); }
    if (event === 'error') throw new Error(data.error || 'The provider could not finish the response.');
    if (event === 'meta') {
      meta = { ...meta, ...data };
      onMeta?.(meta);
    } else if (event === 'delta') {
      if (typeof data.text !== 'string') throw new Error('Invalid text delta from server.');
      reply += data.text;
      onDelta?.(data.text);
    } else if (event === 'done') {
      finished = true;
      meta = { ...meta, ...data };
      if (typeof data.reply === 'string' && !reply) {
        reply = data.reply;
        onDelta?.(reply);
      }
      onMeta?.(meta);
    }
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      // Normalize CRLF so separators split at chunk boundaries are handled.
      buffer = buffer.replace(/\r\n/g, '\n');
      let separator;
      while ((separator = buffer.indexOf('\n\n')) !== -1) {
        processFrame(buffer.slice(0, separator));
        buffer = buffer.slice(separator + 2);
      }
      if (done) break;
    }
    if (buffer.trim()) processFrame(buffer);
  } finally {
    reader.releaseLock();
  }
  if (!finished || meta.conversation_id == null) {
    throw new Error('The response stream ended before confirmation. Refresh your history before retrying to avoid duplicate requests.');
  }
  return { ...meta, reply };
}

export async function fetchConversations() {
  const data = await request(API.conversations);
  if (!data || !Array.isArray(data.conversations)) {
    throw new Error('Unexpected conversation list response.');
  }
  return data.conversations;
}

export async function fetchModels() {
  const data = await request(API.models);
  if (!data || !Array.isArray(data.models)) {
    throw new Error('Unexpected model list response.');
  }
  return data.models;
}

export async function fetchConversation(id) {
  const data = await request(`${API.conversations}${encodeURIComponent(id)}/`);
  if (!data || !Array.isArray(data.messages)) {
    throw new Error('Unexpected conversation response.');
  }
  return data;
}
