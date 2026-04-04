import { useState, useMemo } from "react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { UnifiedGraphData, GraphEntity, EntityRelation } from "@/hooks/api";

export function useGraphFilters(
  data: UnifiedGraphData | undefined,
  entityLayerEnabled: boolean,
  selectedEntityTypes: Set<string>,
) {
  const [searchText, setSearchText] = useState("");
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [selectedClusters, setSelectedClusters] = useState<Set<number>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const debouncedSearchText = useDebouncedValue(searchText, 1000);

  function clearFilters() {
    setSearchText("");
    setSelectedTags(new Set());
    setSelectedTypes(new Set());
    setSelectedSources(new Set());
    setSelectedClusters(new Set());
  }

  const filteredMemories = useMemo(() => {
    if (!data) return [];
    const hasFilter =
      debouncedSearchText.trim() !== "" ||
      selectedTags.size > 0 ||
      selectedTypes.size > 0 ||
      selectedSources.size > 0 ||
      selectedClusters.size > 0;
    if (!hasFilter) return data.memories;
    return data.memories.filter((m) => {
      if (selectedTags.size > 0 && !m.tags.some((t) => selectedTags.has(t))) return false;
      if (selectedTypes.size > 0 && (!m.memory_type || !selectedTypes.has(m.memory_type))) return false;
      if (selectedSources.size > 0 && !selectedSources.has(m.source)) return false;
      if (selectedClusters.size > 0 && !selectedClusters.has(m.cluster)) return false;
      if (
        debouncedSearchText.trim() &&
        !m.content.toLowerCase().includes(debouncedSearchText.trim().toLowerCase())
      )
        return false;
      return true;
    });
  }, [data, debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters]);

  const filteredEdges = useMemo(() => {
    if (!data) return [];
    const filteredIds = new Set(filteredMemories.map((m) => m.id));
    return data.similarity_edges.filter(
      (e) => filteredIds.has(e.source) && filteredIds.has(e.target),
    );
  }, [data, filteredMemories]);

  const filteredEntities = useMemo((): GraphEntity[] => {
    if (!data?.entities || !entityLayerEnabled) return [];
    const memoryIdSet = new Set(filteredMemories.map((m) => m.id));
    return data.entities.filter((e) => {
      if (selectedEntityTypes.size > 0 && !selectedEntityTypes.has(e.entity_type)) return false;
      return e.memory_ids.some((mid) => memoryIdSet.has(mid));
    });
  }, [data, entityLayerEnabled, filteredMemories, selectedEntityTypes]);

  const filteredEntityRelations = useMemo((): EntityRelation[] => {
    if (!data?.entity_relations || !entityLayerEnabled) return [];
    const entityIdSet = new Set(filteredEntities.map((e) => e.id));
    return data.entity_relations.filter(
      (r) => entityIdSet.has(r.source) && entityIdSet.has(r.target),
    );
  }, [data, entityLayerEnabled, filteredEntities]);

  const allTags = useMemo((): [string, number][] => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const m of data.memories) {
      for (const t of m.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [data]);

  const allTypes = useMemo((): [string, number][] => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const m of data.memories) {
      const t = m.memory_type ?? "(none)";
      counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  const allSources = useMemo((): [string, number][] => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const m of data.memories) counts.set(m.source, (counts.get(m.source) ?? 0) + 1);
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  const allClusters = useMemo((): [number, number][] => {
    if (!data) return [];
    const counts = new Map<number, number>();
    for (const m of data.memories) {
      if (m.cluster >= 0) counts.set(m.cluster, (counts.get(m.cluster) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0] - b[0]);
  }, [data]);

  const allEntityTypes = useMemo((): [string, number][] => {
    if (!data?.entities) return [];
    const counts = new Map<string, number>();
    for (const e of data.entities) {
      counts.set(e.entity_type, (counts.get(e.entity_type) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  const tagGroups = useMemo((): [string, [string, number][]][] => {
    const groups = new Map<string, [string, number][]>();
    for (const [tag, count] of allTags) {
      const slash = tag.indexOf("/");
      const category = slash >= 0 ? tag.slice(0, slash) : "other";
      const arr = groups.get(category) ?? [];
      arr.push([tag, count]);
      groups.set(category, arr);
    }
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [allTags]);

  return {
    searchText,
    setSearchText,
    selectedTags,
    setSelectedTags,
    selectedTypes,
    setSelectedTypes,
    selectedSources,
    setSelectedSources,
    selectedClusters,
    setSelectedClusters,
    showFilters,
    setShowFilters,
    debouncedSearchText,
    filteredMemories,
    filteredEdges,
    filteredEntities,
    filteredEntityRelations,
    allTags,
    allTypes,
    allSources,
    allClusters,
    allEntityTypes,
    tagGroups,
    clearFilters,
  };
}
