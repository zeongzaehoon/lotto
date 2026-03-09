import { useState, useRef, useCallback } from 'react';

export interface LogMessage {
  type: 'airflow_log' | 'training_log' | 'dag_state' | 'task_state' | 'done';
  content?: string;
  message?: string;
  task_id?: string;
  state?: string;
  source?: string;
}

export interface UseLogStreamReturn {
  logs: LogMessage[];
  dagState: string | null;
  taskStates: Record<string, string>;
  isConnected: boolean;
  isDone: boolean;
  label: string | null;
  connectDag: (dagId: string, dagRunId: string, label: string) => void;
  connectTrain: (sessionId: string, label: string) => void;
  disconnect: () => void;
  clear: () => void;
}

export function useLogStream(): UseLogStreamReturn {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [dagState, setDagState] = useState<string | null>(null);
  const [taskStates, setTaskStates] = useState<Record<string, string>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [label, setLabel] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const handleMessage = useCallback((event: MessageEvent) => {
    const msg: LogMessage = JSON.parse(event.data);
    switch (msg.type) {
      case 'dag_state':
        setDagState(msg.state || null);
        break;
      case 'task_state':
        if (msg.task_id && msg.state) {
          setTaskStates((prev) => ({ ...prev, [msg.task_id!]: msg.state! }));
        }
        break;
      case 'airflow_log':
      case 'training_log':
        setLogs((prev) => [...prev, msg]);
        break;
      case 'done':
        setIsDone(true);
        setDagState(msg.state || 'success');
        break;
    }
  }, []);

  const reset = useCallback(() => {
    setLogs([]);
    setDagState(null);
    setTaskStates({});
    setIsDone(false);
  }, []);

  const openWs = useCallback((url: string, lbl: string) => {
    wsRef.current?.close();
    reset();
    setLabel(lbl);

    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setIsConnected(true);
    ws.onmessage = handleMessage;
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);
  }, [handleMessage, reset]);

  const connectDag = useCallback((dagId: string, dagRunId: string, lbl: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    openWs(`${protocol}//${window.location.host}/api/ws/logs/${dagId}/${encodeURIComponent(dagRunId)}`, lbl);
  }, [openWs]);

  const connectTrain = useCallback((sessionId: string, lbl: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    openWs(`${protocol}//${window.location.host}/api/ws/train/${sessionId}`, lbl);
  }, [openWs]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const clear = useCallback(() => {
    disconnect();
    reset();
    setLabel(null);
  }, [disconnect, reset]);

  return { logs, dagState, taskStates, isConnected, isDone, label, connectDag, connectTrain, disconnect, clear };
}
