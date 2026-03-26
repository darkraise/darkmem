import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const qc = useQueryClient();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data as string) as { event?: string };
      if (msg.event?.startsWith("memory.") || msg.event?.startsWith("pipeline.")) {
        void qc.invalidateQueries({ queryKey: ["memories"] });
        void qc.invalidateQueries({ queryKey: ["stats"] });
        void qc.invalidateQueries({ queryKey: ["tags"] });
      }
    };

    ws.current.onclose = () => {
      setTimeout(connect, 3000);
    };
  }, [qc]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);
}
