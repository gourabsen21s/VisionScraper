'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import GlassSurface from './GlassSurface';
import BrowserView from './BrowserView';
import ReasoningPanel from './ReasoningPanel';
import { useAgentSession } from '@/hooks/useAgentSession';
import { Send, Loader2, Power, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export default function ScrapeChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    sessionId,
    isLoading,
    isRunning,
    error,
    steps,
    currentStep,
    goal,
    closeSession,
    executeGoal,
    setError
  } = useAgentSession();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isRunning) return;

    const userGoal = input.trim();
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: userGoal,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');

    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Starting browser automation...',
    };
    setMessages(prev => [...prev, assistantMessage]);

    const result = await executeGoal(userGoal);

    if (result) {
      const summary = result.completed
        ? `Task completed successfully in ${result.steps.length} steps.`
        : `Task stopped after ${result.steps.length} steps. ${result.reason || ''}`;
      
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { ...msg, content: summary }
            : msg
        )
      );
    } else if (error) {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { ...msg, content: `Error: ${error}` }
            : msg
        )
      );
    }

    inputRef.current?.focus();
  }, [input, isRunning, executeGoal, error]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const hasMessages = messages.length > 0;
  const showPanels = sessionId || steps.length > 0;

  return (
    <div className="relative z-10 w-full h-[calc(100vh-100px)] mt-[80px] px-4 pb-4 flex flex-col">
      {error && (
        <div className="mb-4 mx-auto max-w-3xl w-full">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-xs hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className={cn(
        "flex-1 flex gap-4 transition-all duration-500",
        showPanels ? "opacity-100" : "opacity-0 pointer-events-none h-0"
      )}>
        <div className="flex-1 min-w-0">
          <BrowserView
            sessionId={sessionId}
            className="h-full"
            onError={(err) => setError(err)}
          />
        </div>
        <div className="w-80 shrink-0">
          <ReasoningPanel
            steps={steps}
            currentStep={currentStep}
            isRunning={isRunning}
            goal={goal}
            className="h-full"
          />
        </div>
      </div>

      <div className={cn(
        "flex flex-col transition-all duration-500 ease-out",
        showPanels ? "mt-4" : "flex-1 justify-center"
      )}>
        {hasMessages && !showPanels && (
          <div className="flex-1 overflow-y-auto mb-4 space-y-4 scrollbar-thin max-w-3xl mx-auto w-full">
            {messages.map((message, index) => {
              const isLast = index === messages.length - 1;
              const isAssistant = message.role === 'assistant';
              const showCursor = isRunning && isLast && isAssistant;

              return (
                <div
                  key={message.id}
                  className={cn(
                    "flex animate-in slide-in-from-bottom-4 duration-300",
                    isAssistant ? "justify-start" : "justify-end"
                  )}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <GlassSurface
                    width="auto"
                    height="auto"
                    borderRadius={16}
                    className={cn(
                      "max-w-[80%] px-4 py-3",
                      isAssistant ? "" : "bg-white/10"
                    )}
                  >
                    <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                      {message.content}
                      {showCursor && (
                        <span className="inline-block w-2 h-4 ml-0.5 bg-purple-400 animate-pulse align-middle" />
                      )}
                    </p>
                  </GlassSurface>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="max-w-3xl mx-auto w-full">
          <div className="flex items-center gap-3">
            {sessionId && (
              <button
                onClick={closeSession}
                disabled={isRunning}
                className="p-3 rounded-full bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors disabled:opacity-50"
                title="End session"
              >
                <Power className="w-5 h-5" />
              </button>
            )}
            
            <GlassSurface
              width="100%"
              height={56}
              borderRadius={9999}
              className="pointer-events-auto flex-1"
            >
              <div className="flex items-center w-full gap-3 px-4">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={sessionId ? "Describe next action..." : "Enter a goal like 'Go to google.com and search for cats'"}
                  disabled={isRunning || isLoading}
                  className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-foreground/50 text-sm"
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || isRunning || isLoading}
                  className="p-2 rounded-full hover:bg-foreground/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isRunning || isLoading ? (
                    <Loader2 className="w-4 h-4 text-foreground animate-spin" />
                  ) : (
                    <Send className="w-4 h-4 text-foreground" />
                  )}
                </button>
              </div>
            </GlassSurface>
          </div>
        </div>

        {!hasMessages && !showPanels && (
          <p className="text-center text-foreground/50 text-sm mt-4">
            Enter a goal to start the browser automation
          </p>
        )}
      </div>
    </div>
  );
}
