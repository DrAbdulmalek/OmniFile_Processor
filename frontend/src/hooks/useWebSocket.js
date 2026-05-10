import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useWebSocket - Custom hook for WebSocket connection with auto-reconnect.
 *
 * @param {string} url - WebSocket URL
 * @param {object} options - Connection options
 * @param {number} options.reconnectInterval - Reconnect delay in ms (default: 3000)
 * @param {number} options.maxReconnects - Max reconnection attempts (default: 10)
 * @returns {{ data: object|null, isConnected: boolean, send: function, lastMessage: object|null }}
 */
export function useWebSocket(url, options = {}) {
  const { reconnectInterval = 3000, maxReconnects = 10 } = options;
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!url || wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
          setLastMessage(parsed);
        } catch {
          setData(event.data);
          setLastMessage(event.data);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);

        // Auto-reconnect
        if (reconnectCountRef.current < maxReconnects) {
          reconnectCountRef.current += 1;
          reconnectTimerRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      // Connection failed
    }
  }, [url, reconnectInterval, maxReconnects]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, []);

  return { data, isConnected, send, lastMessage };
}
