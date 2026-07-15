"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { ChatPanel } from "./chat-panel";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [mode, setMode] = useState("BSJP");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const sidebarWidth = isMobile
    ? 0
    : sidebarCollapsed
    ? "var(--sidebar-w-collapsed)"
    : "var(--sidebar-w)";

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onMobileClose={() => setSidebarOpen(false)}
        isMobile={isMobile}
      />

      <div
        className="flex-1 flex flex-col overflow-hidden transition-all duration-300"
        style={{
          marginLeft: isMobile ? 0 : sidebarWidth,
        }}
      >
        <Header
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          onChatToggle={() => setChatOpen(!chatOpen)}
          chatOpen={chatOpen}
          mode={mode}
          onModeChange={setMode}
        />

        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Mobile sidebar drawer */}
      {isMobile && sidebarOpen && (
        <Sidebar
          collapsed={false}
          onToggle={() => {}}
          onMobileClose={() => setSidebarOpen(false)}
          isMobile={true}
        />
      )}

      {/* Chat panel */}
      {!isMobile && chatOpen && (
        <ChatPanel
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          mode={mode}
        />
      )}
    </div>
  );
}
