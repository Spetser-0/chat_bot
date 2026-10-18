import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';

export interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
}

export function MessageBubble({ role, content, timestamp, isStreaming = false }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--assistant'} animate-message-in`}>
      <div className="message__avatar">
        {isUser ? <User size={20} /> : <Bot size={20} />}
      </div>
      <div className="message__content">
        <div className={`message__bubble ${isUser ? 'message__bubble--user' : 'message__bubble--assistant'}`}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <div className="message__markdown">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
          {isStreaming && <span className="message__cursor" aria-hidden="true" />}
        </div>
        {timestamp && (
          <time className="message__timestamp" dateTime={timestamp}>
            {new Date(timestamp).toLocaleTimeString('ar-LY', { hour: '2-digit', minute: '2-digit' })}
          </time>
        )}
      </div>
    </div>
  );
}
