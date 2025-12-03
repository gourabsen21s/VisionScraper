'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import StarBorder from './StarBorder';
import ShinyText from './ShinyText';
import MessageBubble, { Message } from './MessageBubble';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const addMessage = useCallback((type: Message['type'], content: string, status?: Message['status']) => {
    const newMessage: Message = {
      id: crypto.randomUUID(),
      type,
      content,
      timestamp: new Date(),
      status
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  }, []);

  const updateMessage = useCallback((id: string, updates: Partial<Message>) => {
    setMessages(prev => 
      prev.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
    );
  }, []);

  const simulateScraping = useCallback(async (url: string) => {
    setIsProcessing(true);
    setConnectionStatus('connecting');

    addMessage('user', `Scrape: ${url}`);

    await new Promise(r => setTimeout(r, 500));
    setConnectionStatus('connected');

    const statusId = addMessage('status', 'Initializing browser session...', 'processing');
    await new Promise(r => setTimeout(r, 1200));

    updateMessage(statusId, { content: 'Navigating to target URL...', status: 'processing' });
    await new Promise(r => setTimeout(r, 1500));

    updateMessage(statusId, { content: 'Analyzing page structure...', status: 'processing' });
    await new Promise(r => setTimeout(r, 1800));

    updateMessage(statusId, { content: 'Extracting data with AI...', status: 'processing' });
    await new Promise(r => setTimeout(r, 2000));

    updateMessage(statusId, { content: 'Scraping completed successfully!', status: 'success' });

    const mockResult = {
      url,
      title: 'Sample Product Page',
      products: [
        { name: 'Product A', price: '$29.99', rating: '4.5/5' },
        { name: 'Product B', price: '$49.99', rating: '4.8/5' },
        { name: 'Product C', price: '$19.99', rating: '4.2/5' }
      ],
      scrapedAt: new Date().toISOString()
    };

    addMessage('assistant', '```json\n' + JSON.stringify(mockResult, null, 2) + '\n```');

    setIsProcessing(false);
    setConnectionStatus('disconnected');
  }, [addMessage, updateMessage]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    
    const url = inputValue.trim();
    if (!url || isProcessing) return;

    try {
      new URL(url);
    } catch {
      addMessage('status', 'Please enter a valid URL (e.g., https://example.com)', 'error');
      return;
    }

    setInputValue('');
    simulateScraping(url);
  }, [inputValue, isProcessing, addMessage, simulateScraping]);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-400';
      case 'connecting': return 'bg-yellow-400 pulse-glow';
      case 'error': return 'bg-red-400';
      default: return 'bg-white/30';
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className={`flex flex-col w-full max-w-3xl mx-auto px-6 ${hasMessages ? 'h-[80vh]' : 'h-auto'}`}>
      {/* Header - Always visible */}
      <div className="flex flex-col items-center text-center mb-8">
        {/* Logo/Brand */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
          </div>
        </div>

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-6">
          <ShinyText text="AI Web Scraper" speed={3} className="text-sm font-medium" />
        </div>

        {/* Hero Text */}
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 leading-tight">
          Extract data from<br />any website
        </h1>
        <p className="text-white/60 text-lg max-w-md mb-2">
          Paste a URL and let AI navigate, understand, and extract structured data in real-time.
        </p>

        {/* Status indicator */}
        <div className="flex items-center gap-2 mt-4">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span className="text-xs text-white/50 capitalize">{connectionStatus}</span>
        </div>
      </div>

      {/* Messages Area - Only shown when there are messages */}
      {hasMessages && (
        <div className="flex-1 overflow-y-auto mb-6 glass rounded-2xl p-4 min-h-0">
          {messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Area */}
      <div className="w-full">
        <form onSubmit={handleSubmit}>
          <StarBorder
            as="div"
            color="cyan"
            speed="5s"
            thickness={2}
            className="w-full"
          >
            <div className="flex items-center gap-3 bg-black/40 backdrop-blur-md rounded-[18px] px-5">
              <svg className="w-5 h-5 text-white/40 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Enter URL to scrape (e.g., https://example.com)"
                disabled={isProcessing}
                className="flex-1 bg-transparent py-4 text-white placeholder-white/40 focus:outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isProcessing || !inputValue.trim()}
                className="flex-shrink-0 w-10 h-10 rounded-xl bg-white text-black flex items-center justify-center transition-all hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 disabled:bg-white/20 disabled:text-white/50"
              >
                {isProcessing ? (
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                )}
              </button>
            </div>
          </StarBorder>
        </form>
        <p className="text-center text-xs text-white/40 mt-4">
          Press Enter to start scraping
        </p>
      </div>
    </div>
  );
}
