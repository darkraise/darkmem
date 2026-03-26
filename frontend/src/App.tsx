import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "@/components/Sidebar";
import { useWebSocket } from "@/hooks/useWebSocket";
import Overview from "@/pages/Overview";
import Memories from "@/pages/Memories";
import KnowledgeGraph from "@/pages/KnowledgeGraph";
import VectorSpace from "@/pages/VectorSpace";
import Search from "@/pages/Search";
import Analytics from "@/pages/Analytics";
import ApiKeys from "@/pages/ApiKeys";
import LlmConfig from "@/pages/LlmConfig";
import Settings from "@/pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function AppContent() {
  useWebSocket();
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/memories" element={<Memories />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/vectors" element={<VectorSpace />} />
          <Route path="/search" element={<Search />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/keys" element={<ApiKeys />} />
          <Route path="/llm" element={<LlmConfig />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
