import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Markdown from 'react-markdown';
import { assistantMarkdown, displayBudget, displayCost, displayModel } from '../assistantPresentation';
import { conversationContext, readChatStatus, sendChat } from '../chatApi';
import type { ChatAvailability, ChatMessage, ChatReply } from '../chatApi';
import { formatCount, formatSnapshot } from '../format';
import { useResource } from '../useResource';

const suggestions = [
  'Summarize the current business KPIs.',
  'Which categories have the highest gross cart value?',
  'Which products have low stock?',
  'Which products combine high cart activity with low inventory?',
];

const availabilityText: Record<ChatAvailability, string> = {
  disabled: 'The assistant is disabled in local settings.',
  unconfigured: 'The backend needs an Anthropic API key.',
  unavailable: 'The assistant configuration or usage ledger is unavailable.',
  budget_exhausted: 'The remaining application budget cannot cover another model call.',
  ready: 'Available',
};

type Message = ChatMessage & { reply?: ChatReply };

function AssistantIcon() {
  return <span className="assistant-icon" aria-hidden="true">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.4-3.1a7.5 7.5 0 1 1 13.6-4.4Z" />
      <path d="M9 13.5v-2m3 2V8m3 5.5v-3" />
    </svg>
  </span>;
}

function ReplyDetails({ reply }: { reply: ChatReply }) {
  const snapshot = reply.snapshot?.snapshot_at;
  return <div className="assistant-metadata">
    {snapshot && Number.isFinite(Date.parse(snapshot)) && <div>
      <strong>Snapshot</strong> <time dateTime={snapshot}>{formatSnapshot(snapshot)}</time>
    </div>}
    {reply.tools.length > 0 && <details>
      <summary>MCP tools used ({reply.tools.length})</summary>
      <ul>{reply.tools.map((tool, index) => <li key={index}>
        <code>{tool.name}</code> · {tool.status}
        {Object.entries(tool.arguments).map(([key, value]) => <span key={key}> · {key} {value}</span>)}
      </li>)}</ul>
    </details>}
    <div><strong>Estimated request cost</strong> {displayCost(reply.estimated_cost_usd)}
      {' · '}{formatCount(reply.usage.input_tokens)} input / {formatCount(reply.usage.output_tokens)} output tokens</div>
  </div>;
}

export function Assistant() {
  const [revision, checkStatus] = useState(0);
  const status = useResource(readChatStatus, revision);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [error, setError] = useState('');
  const [remaining, setRemaining] = useState<string | null>(null);
  const transcript = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const pending = pendingQuestion !== '';
  const available = status.status === 'ready' && status.data.availability === 'ready';
  const budget = (status.status === 'ready' ? status.data.remaining_budget_usd : null) ?? remaining;

  useEffect(() => {
    if (transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight;
  }, [messages, pending]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!available || pending || !text) return;
    setError('');
    setPendingQuestion(text);
    setQuestion('');
    try {
      const reply = await sendChat(text, conversationContext(messages));
      setRemaining(reply.remaining_budget_usd);
      setMessages(previous => [...previous, { role: 'user', content: text },
        { role: 'assistant', content: reply.answer, reply }]);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The assistant request failed.');
      setQuestion(text);
    } finally {
      checkStatus(value => value + 1);
      setPendingQuestion('');
    }
  }

  return <div className="panel assistant-panel">
    <div className="assistant-summary">
      <div className="assistant-status">
        <AssistantIcon />
        <div role="status">
          {status.status === 'loading' ? 'Checking assistant availability…'
          : status.status === 'error' ? 'Cannot reach the local assistant. Check that FastAPI is running.'
          : <><strong>{displayModel(status.data.model)}</strong> · {availabilityText[status.data.availability]}</>}
          {budget !== null && <div>Remaining estimated budget <strong>{displayBudget(budget)}</strong></div>}
        </div>
      </div>
      <button className="button" type="button" disabled={pending || (!messages.length && !question && !error)}
        onClick={() => { setMessages([]); setQuestion(''); setError(''); }}>Clear conversation</button>
    </div>
    <div className="assistant-transcript" aria-label="Conversation" role="log" tabIndex={0} ref={transcript}>
      {messages.length === 0 && !pending && <div className="assistant-suggestions">
        <h2>What would you like to explore?</h2>
        <p>Start with a question about simulated carts, product rankings, or inventory.</p>
        {suggestions.map(suggestion => <button className="button" key={suggestion} type="button"
          disabled={!available} onClick={() => { setQuestion(suggestion); input.current?.focus(); }}>
          {suggestion}</button>)}
      </div>}
      {messages.map((message, index) => <article key={index} className={`assistant-message ${message.role}`}>
        <div className="assistant-speaker">{message.role === 'user' ? 'You' : 'Assistant'}</div>
        {message.role === 'assistant' ? <div className="assistant-markdown">
          <Markdown {...assistantMarkdown}>{message.content}</Markdown>
        </div> : <p>{message.content}</p>}
        {message.reply && <ReplyDetails reply={message.reply} />}
      </article>)}
      {pending && <>
        <article className="assistant-message user"><div className="assistant-speaker">You</div><p>{pendingQuestion}</p></article>
        <p role="status">Assistant is working…</p>
      </>}
    </div>
    <form className="assistant-form" onSubmit={submit}>
      {error && <p role="alert" className="assistant-error">{error}</p>}
      <label htmlFor="assistant-question">Business question</label>
      <textarea id="assistant-question" rows={2} maxLength={2000} value={question} ref={input}
        onChange={event => setQuestion(event.target.value)} disabled={pending || !available} />
      <button className="button assistant-send" type="submit"
        disabled={pending || !available || !question.trim()}>Send</button>
    </form>
  </div>;
}
