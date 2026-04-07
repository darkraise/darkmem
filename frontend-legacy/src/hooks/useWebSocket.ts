import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface PipelineStatus {
  memory_id: string;
  embed: string;
  extract: string;
  qdrant: string;
  neo4j: string;
  entities_count: number;
  relations_count: number;
  error: string | null;
}

function showPipelineToast(event: string, data: PipelineStatus) {
  const id = data.memory_id.slice(0, 8);

  if (event === "pipeline.completed") {
    toast.success(`Memory ${id} processed`, {
      description: `${data.entities_count} entities, ${data.relations_count} relations extracted`,
    });
  } else if (event === "pipeline.partial") {
    const failed = [
      data.embed === "error" && "embedding",
      data.extract === "error" && "extraction",
      data.qdrant === "error" && "vector store",
      data.neo4j === "error" && "graph store",
    ].filter(Boolean).join(", ");
    toast.warning(`Memory ${id} partially processed`, {
      description: `Failed: ${failed}`,
    });
  } else if (event === "pipeline.failed") {
    toast.error(`Memory ${id} processing failed`, {
      description: data.error || "All pipeline steps failed",
    });
  }
}

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const retryCount = useRef<number>(0);
  const qc = useQueryClient();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data as string) as { event?: string; data?: Record<string, unknown> };

      if (msg.event?.startsWith("pipeline.") && msg.data) {
        showPipelineToast(msg.event, msg.data as PipelineStatus);
        void qc.invalidateQueries({ queryKey: ["memories"] });
        void qc.invalidateQueries({ queryKey: ["stats"] });
        void qc.invalidateQueries({ queryKey: ["tags"] });
        void qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      } else if (msg.event?.startsWith("memory.")) {
        void qc.invalidateQueries({ queryKey: ["memories"] });
        void qc.invalidateQueries({ queryKey: ["stats"] });
        void qc.invalidateQueries({ queryKey: ["tags"] });
      }

      if (msg.event?.startsWith("repo.")) {
        void qc.invalidateQueries({ queryKey: ["repos"] });
        void qc.invalidateQueries({ queryKey: ["repoTasks"] });
        void qc.invalidateQueries({ queryKey: ["repoStats"] });

        if (msg.event === "repo.clone_completed") {
          toast.success(`Repository ${msg.data?.name} cloned`);
        } else if (msg.event === "repo.clone_failed") {
          toast.error(`Clone failed: ${msg.data?.error}`);
        } else if (msg.event === "repo.indexing_completed") {
          toast.success(`Indexed ${msg.data?.files_changed} files, ${msg.data?.symbols_indexed} symbols`);
        } else if (msg.event === "repo.indexing_failed") {
          toast.error(`Indexing failed: ${msg.data?.error}`);
        }
      }

      if (msg.event?.startsWith("enrichment.")) {
        void qc.invalidateQueries({ queryKey: ["repoStats"] });
      }
    };

    ws.current.onopen = () => {
      retryCount.current = 0;
    };

    ws.current.onclose = () => {
      const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
      retryCount.current++;
      setTimeout(connect, delay);
    };
  }, [qc]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);
}
