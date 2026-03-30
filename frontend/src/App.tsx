import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "@/components/Sidebar";
import { useWebSocket } from "@/hooks/useWebSocket";
import { checkSetupStatus, isAuthenticated, clearAuthToken } from "@/lib/api";
import Overview from "@/pages/Overview";
import Memories from "@/pages/Memories";
import KnowledgeGraph from "@/pages/KnowledgeGraph";
import VectorSpace from "@/pages/VectorSpace";
import UnifiedGraph from "@/pages/UnifiedGraph";
import Search from "@/pages/Search";
import Analytics from "@/pages/Analytics";
import LlmConfig from "@/pages/LlmConfig";
import Settings from "@/pages/Settings";
import Setup from "@/pages/Setup";
import Login from "@/pages/Login";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

type AuthState = "loading" | "setup" | "login" | "authenticated";

function AppContent({ onLogout }: { onLogout: () => void }) {
  useWebSocket();
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar onLogout={onLogout} />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/memories" element={<Memories />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/unified-graph" element={<UnifiedGraph />} />
          <Route path="/vectors" element={<VectorSpace />} />
          <Route path="/search" element={<Search />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/llm" element={<LlmConfig />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const [authState, setAuthState] = useState<AuthState>("loading");

  useEffect(() => {
    checkSetupStatus()
      .then(({ initialized }) => {
        if (!initialized) {
          setAuthState("setup");
        } else if (isAuthenticated()) {
          setAuthState("authenticated");
        } else {
          setAuthState("login");
        }
      })
      .catch(() => {
        if (isAuthenticated()) {
          setAuthState("authenticated");
        } else {
          setAuthState("login");
        }
      });
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    setAuthState("login");
  };

  if (authState === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (authState === "setup") {
    return <Setup onComplete={() => setAuthState("authenticated")} />;
  }

  if (authState === "login") {
    return <Login onSuccess={() => setAuthState("authenticated")} />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent onLogout={handleLogout} />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
