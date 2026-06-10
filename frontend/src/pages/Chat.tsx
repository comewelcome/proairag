import { useState, useEffect, useRef } from 'react';
import { Plus, Send, FileText, GitBranch, Bot, User, MessageSquare } from 'lucide-react';
import { api } from '../lib/api';
import { EmptyState } from '../components/common/EmptyState';
import { toast } from 'sonner';
import type { Conversation, ChatMessage } from '../types';

export function Chat() {
  const [sessions, setSessions] = useState<Conversation[]>([]);
  const [currentSession, setCurrentSession] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadSessions = async () => {
    try {
      const { data } = await api.get<Conversation[]>('/chat/sessions/');
      setSessions(Array.isArray(data) ? data : []);
    } catch {
      // chat sessions endpoint may not exist yet
    }
  };

  useEffect(() => { loadSessions(); }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSession = async (session: Conversation) => {
    setCurrentSession(session);
    setLoading(true);
    try {
      const { data } = await api.get<ChatMessage[]>(`/chat/sessions/${session.id}`);
      setMessages(Array.isArray(data) ? data : []);
    } catch {
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const createSession = async () => {
    try {
      const { data } = await api.post<Conversation>('/chat/sessions/', { title: 'Nouvelle conversation' });
      setSessions([data, ...sessions]);
      setCurrentSession(data);
      setMessages([]);
    } catch {
      toast.error('Impossible de creer une conversation');
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    if (!currentSession) {
      await createSession();
      return;
    }

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: currentSession.id,
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);

    try {
      const { data } = await api.post<ChatMessage>(`/chat/sessions/${currentSession.id}/send`, {
        message: userMsg.content,
      });
      setMessages(prev => [...prev, data]);
    } catch {
      toast.error('Erreur lors de lenvoi du message');
      setMessages(prev => prev.filter(m => m.id !== userMsg.id));
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <div className="w-64 border-r border-border bg-bg-secondary/30 flex flex-col">
        <div className="p-3">
          <button onClick={createSession} className="w-full btn-primary flex items-center justify-center gap-2 text-sm">
            <Plus size={16} />
            Nouvelle conversation
          </button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {sessions.map(session => (
            <button
              key={session.id}
              onClick={() => loadSession(session)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                currentSession?.id === session.id
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-muted hover:bg-bg-card hover:text-text'
              }`}
            >
              <div className="truncate">{session.title}</div>
              <div className="text-xs text-text-muted/50 mt-0.5">
                {new Date(session.updated_at).toLocaleDateString('fr-FR')}
              </div>
            </button>
          ))}
          {sessions.length === 0 && (
            <div className="text-text-muted/50 text-sm text-center py-8">
              Aucune conversation
            </div>
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-text-muted">Chargement...</div>
        ) : messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState
              icon={<MessageSquare size={48} />}
              title="Bienvenue dans le Chat RAG"
              description="Posez des questions sur vos documents. Les responses sont basees sur le contenu de vos fichiers et le graphe de connaissances."
              action={<button onClick={createSession} className="btn-primary">+ Commencer une conversation</button>}
            />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-6 space-y-4">
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex gap-2 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.role === 'user' ? 'bg-accent' : 'bg-bg-card'
                  }`}>
                    {msg.role === 'user' ? <User size={16} className="text-white" /> : <Bot size={16} className="text-accent" />}
                  </div>
                  <div>
                    <div className={`rounded-xl px-4 py-2 ${
                      msg.role === 'user' ? 'bg-accent/10 text-text' : 'bg-bg-card text-text'
                    }`}>
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                    </div>

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {msg.sources.map((src, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
                            <FileText size={12} />
                            <span>{src.doc_title}</span>
                            <span className="text-accent/60">({src.score.toFixed(3)})</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Graph context */}
                    {msg.graph_context && msg.graph_context.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {msg.graph_context.map((gc, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-text-muted">
                            <GitBranch size={12} />
                            <span>{gc.entity} ({gc.type})</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input */}
        <div className="p-4 border-t border-border">
          <div className="flex gap-2">
            <textarea
              className="input-base flex-1 resize-none"
              rows={1}
              placeholder="Posez une question sur vos documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
            />
            <button
              onClick={sendMessage}
              disabled={sending || !input.trim()}
              className="btn-primary flex items-center gap-2 self-end"
            >
              {sending ? '...' : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
