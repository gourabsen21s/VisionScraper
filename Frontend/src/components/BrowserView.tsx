'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Monitor, Loader2, WifiOff, Play, Square } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BrowserViewProps {
  sessionId: string | null;
  backendUrl?: string;
  className?: string;
  onError?: (error: string) => void;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export default function BrowserView({
  sessionId,
  backendUrl = 'https://visionscraper-backend.internal.whitepebble-a73ac1ee.southindia.azurecontainerapps.io',
  className,
  onError
}: BrowserViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [fps, setFps] = useState(0);
  const frameCountRef = useRef(0);
  const lastFpsUpdateRef = useRef(Date.now());

  const connect = useCallback(() => {
    if (!sessionId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(`${backendUrl}/api/sessions/${sessionId}/screencast`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      frameCountRef.current = 0;
      lastFpsUpdateRef.current = Date.now();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'frame' && data.data) {
          renderFrame(data.data);
          frameCountRef.current++;
          
          const now = Date.now();
          if (now - lastFpsUpdateRef.current >= 1000) {
            setFps(frameCountRef.current);
            frameCountRef.current = 0;
            lastFpsUpdateRef.current = now;
          }
        }
      } catch (e) {
        console.error('Failed to parse screencast message:', e);
      }
    };

    ws.onerror = () => {
      setStatus('error');
      onError?.('WebSocket connection error');
    };

    ws.onclose = () => {
      setStatus('disconnected');
      wsRef.current = null;
    };
  }, [sessionId, backendUrl, onError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send('stop');
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
    setFps(0);
  }, []);

  const renderFrame = (base64Data: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      if (canvas.width !== img.width || canvas.height !== img.height) {
        canvas.width = img.width;
        canvas.height = img.height;
      }
      ctx.drawImage(img, 0, 0);
    };
    img.src = `data:image/jpeg;base64,${base64Data}`;
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  useEffect(() => {
    if (sessionId && status === 'disconnected') {
      connect();
    } else if (!sessionId && status !== 'disconnected') {
      disconnect();
    }
  }, [sessionId, status, connect, disconnect]);

  const statusColors: Record<ConnectionStatus, string> = {
    disconnected: 'text-muted-foreground',
    connecting: 'text-yellow-500',
    connected: 'text-green-500',
    error: 'text-red-500'
  };

  const statusLabels: Record<ConnectionStatus, string> = {
    disconnected: 'Disconnected',
    connecting: 'Connecting...',
    connected: 'Live',
    error: 'Error'
  };

  return (
    <div className={cn('flex flex-col rounded-xl border border-border/50 bg-card/30 backdrop-blur-sm overflow-hidden', className)}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-background/50">
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-foreground">Browser View</span>
        </div>
        <div className="flex items-center gap-3">
          {status === 'connected' && (
            <span className="text-xs text-muted-foreground font-mono">{fps} fps</span>
          )}
          <div className={cn('flex items-center gap-1.5 text-xs', statusColors[status])}>
            {status === 'connecting' && <Loader2 className="w-3 h-3 animate-spin" />}
            {status === 'connected' && <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />}
            {status === 'error' && <WifiOff className="w-3 h-3" />}
            <span>{statusLabels[status]}</span>
          </div>
          {sessionId && (
            <button
              onClick={status === 'connected' ? disconnect : connect}
              className="p-1.5 rounded-md hover:bg-foreground/10 transition-colors"
              title={status === 'connected' ? 'Stop streaming' : 'Start streaming'}
            >
              {status === 'connected' ? (
                <Square className="w-3.5 h-3.5 text-foreground" />
              ) : (
                <Play className="w-3.5 h-3.5 text-foreground" />
              )}
            </button>
          )}
        </div>
      </div>
      
      <div className="relative flex-1 min-h-[400px] bg-black/50 flex items-center justify-center">
        {!sessionId ? (
          <div className="text-center text-muted-foreground">
            <Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No active session</p>
            <p className="text-xs mt-1">Start a scraping task to view the browser</p>
          </div>
        ) : status === 'connecting' ? (
          <div className="text-center text-muted-foreground">
            <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin" />
            <p className="text-sm">Connecting to browser...</p>
          </div>
        ) : status === 'error' ? (
          <div className="text-center text-red-400">
            <WifiOff className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Connection failed</p>
            <button
              onClick={connect}
              className="mt-3 px-4 py-2 text-xs bg-foreground/10 rounded-lg hover:bg-foreground/20 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : null}
        
        <canvas
          ref={canvasRef}
          className={cn(
            'max-w-full max-h-full object-contain',
            status !== 'connected' && 'hidden'
          )}
        />
      </div>
    </div>
  );
}

