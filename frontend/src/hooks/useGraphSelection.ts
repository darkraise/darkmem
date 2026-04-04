import { useState, useCallback } from "react";

export function useGraphSelection() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);

  const handleNodeSelect = useCallback((id: string | null) => {
    setSelectedNodeId(id);
    setSelectedEntityId(null);
    if (id) setShowPanel(true);
  }, []);

  const handleNavigate = useCallback((id: string) => {
    setSelectedNodeId(id);
    setSelectedEntityId(null);
    setShowPanel(true);
  }, []);

  const handleEntitySelect = useCallback((entityId: string | null) => {
    setSelectedEntityId(entityId);
    setSelectedNodeId(entityId ? `entity:${entityId}` : null);
    if (entityId) setShowPanel(true);
  }, []);

  return {
    selectedNodeId,
    setSelectedNodeId,
    selectedEntityId,
    setSelectedEntityId,
    showPanel,
    setShowPanel,
    handleNodeSelect,
    handleNavigate,
    handleEntitySelect,
  };
}
