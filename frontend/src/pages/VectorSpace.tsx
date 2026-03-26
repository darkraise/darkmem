import { useMemories } from "@/hooks/useApi";

export default function VectorSpace() {
  const { data: memories } = useMemories();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Vector Space</h2>
      <p className="text-muted-foreground mb-4">
        2D/3D projection of memory embeddings. Requires running the pipeline with an embedding model.
      </p>
      <div className="bg-card border border-border rounded-lg p-6 text-center" style={{ height: "60vh" }}>
        <div className="flex items-center justify-center h-full">
          <div>
            <p className="text-muted-foreground text-lg">Vector visualization</p>
            <p className="text-muted-foreground text-sm mt-2">
              {memories?.length ?? 0} memories indexed.
              UMAP/t-SNE projection will be available when embedding data is accessible via API.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
