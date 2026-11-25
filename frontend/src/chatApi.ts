export type ChatAvailability = 'disabled' | 'unconfigured' | 'ready' | 'unavailable' | 'budget_exhausted';

export interface ChatStatus {
  enabled: boolean;
  model: string;
  availability: ChatAvailability;
  estimated_usage_usd: string | null;
  remaining_budget_usd: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatReply {
  answer: string;
  tools: { name: string; arguments: Record<string, number>; status: 'ok' | 'error' | 'truncated' }[];
  snapshot: { snapshot_at: string; metric_basis: string } | null;
  usage: Record<'input_tokens' | 'output_tokens' | 'cache_creation_input_tokens' | 'cache_read_input_tokens', number>;
  estimated_cost_usd: string;
  remaining_budget_usd: string;
}

async function request<T>(suffix: string, options: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/chat${suffix}`, { cache: 'no-store', ...options });
  if (!response.ok) {
    const messages: Record<number, string> = {
      403: 'Open the assistant from the local dashboard.',
      422: 'The question or conversation is too long. Shorten the question or clear the conversation.',
      429: 'The chat rate limit or application budget was reached. Check the budget before retrying.',
      502: 'The model provider did not return a usable answer.',
      503: 'The assistant is unavailable. Check the local backend configuration.',
      504: 'The assistant timed out. Unknown model usage remains reserved against the budget.',
    };
    throw new Error(messages[response.status] ?? 'The assistant request failed. Check the local backend.');
  }
  return await response.json() as T;
}

export const readChatStatus = (signal: AbortSignal) => request<ChatStatus>('/status', { signal });

export const sendChat = (question: string, history: ChatMessage[]) => request<ChatReply>('', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question, history }),
});

export function conversationContext(messages: ChatMessage[]): ChatMessage[] {
  return messages.slice(-6).map(({ role, content }) => ({ role, content: content.slice(0, 2000) }));
}
