"use client";

import { useState, useEffect, useRef } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { ChatPanel } from "./chat-panel";
import { WorkspaceView } from "@/components/workspace/workspace-view";
import { WorkspaceProvider, useWorkspace } from "@/lib/workspace-context";

function AppShellInner() {
  const { state, dispatch, setMode } = useWorkspace();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isViewChanging, setIsViewChanging] = useState(false);
  const viewChangeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => {
      window.removeEventListener("resize", check);
      if (viewChangeTimeoutRef.current) clearTimeout(viewChangeTimeoutRef.current);
    };
  }, []);

  const sidebarWidth = isMobile
    ? 0
    : sidebarCollapsed
    ? "var(--sidebar-w-collapsed)"
    : "var(--sidebar-w)";

  function handleViewChange() {
    if (viewChangeTimeoutRef.current) clearTimeout(viewChangeTimeoutRef.current);
    setIsViewChanging(true);
    viewChangeTimeoutRef.current = setTimeout(() => setIsViewChanging(false), 200);
  }

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
        style={{ marginLeft: isMobile ? 0 : sidebarWidth }}
      >
        <Header
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          onChatToggle={() => dispatch({ type: "TOGGLE_CHAT" })}
          chatOpen={state.isChatOpen}
          mode={state.activeMode}
          onModeChange={setMode}
        />

        <main className="flex-1 overflow-hidden relative">
          <div
            className={`h-full transition-opacity duration-200 ${
              isViewChanging ? "opacity-60" : "opacity-100"
            }`}
            onAnimationStart={handleViewChange}
          >
            <WorkspaceView />
          </div>
        </main>
      </div>

      {isMobile && sidebarOpen && (
        <Sidebar
          collapsed={false}
          onToggle={() => {}}
          onMobileClose={() => setSidebarOpen(false)}
          isMobile={true}
        />
      )}

      {!isMobile && state.isChatOpen && (
        <ChatPanel
          open={state.isChatOpen}
          onClose={() => dispatch({ type: "TOGGLE_CHAT", open: false })}
          mode={state.activeMode}
        />
      )}
    </div>
  );
}

export function AppShell() {
  return (
    <WorkspaceProvider>
      <AppShellInner />
    </WorkspaceProvider>
  );
}
