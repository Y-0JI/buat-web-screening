"use client";

import { useAuth } from "@/lib/auth-context";
import { Avatar } from "@/components/ui/avatar";
import { Tooltip } from "@/components/ui/tooltip";
import { useWorkspace, type WorkspaceView } from "@/lib/workspace-context";
import { ResultHistory } from "@/components/workspace/result-history";

interface NavItem {
  icon: React.ReactNode;
  label: string;
  view: WorkspaceView;
  requiresAuth?: boolean;
}

const navItems: NavItem[] = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
    label: "Beranda",
    view: "dashboard",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    label: "Riset",
    view: "research",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
      </svg>
    ),
    label: "Screening",
    view: "screening",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    label: "Perbandingan",
    view: "compare",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
      </svg>
    ),
    label: "Watchlist",
    view: "watchlist",
    requiresAuth: true,
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onMobileClose: () => void;
  isMobile: boolean;
}

export function Sidebar({ collapsed, onToggle, onMobileClose, isMobile }: SidebarProps) {
  const { isAuthenticated, user, logout } = useAuth();
  const { state, dispatch } = useWorkspace();

  const sidebarWidth = collapsed ? "w-16" : "w-60";

  function handleNavClick(view: WorkspaceView) {
    dispatch({ type: "SET_VIEW", view });
    onMobileClose();
  }

  return (
    <>
      {isMobile && (
        <div className="fixed inset-0 bg-black/50 z-40" onClick={onMobileClose} />
      )}

      <aside className={`fixed top-0 left-0 h-full bg-zinc-950 border-r border-zinc-800 z-50 transition-all duration-300 flex flex-col ${isMobile ? "w-60" : sidebarWidth}`}>
        <div className="flex items-center justify-between px-4 h-14 border-b border-zinc-800">
          {!collapsed && (
            <button onClick={() => handleNavClick("dashboard")} className="text-lg font-bold text-zinc-100">
              BSJP AI
            </button>
          )}
          {!isMobile && (
            <button onClick={onToggle} className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
              <svg className={`w-5 h-5 transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>
          )}
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            if (item.requiresAuth && !isAuthenticated) return null;
            const isActive = state.view === item.view;
            const content = (
              <button
                key={item.label}
                onClick={() => handleNavClick(item.view)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left ${
                  isActive
                    ? "bg-blue-600/15 text-blue-400"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60"
                }`}
              >
                <span className={isActive ? "text-blue-400" : "text-zinc-500"}>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </button>
            );

            if (collapsed && !isMobile) {
              return <Tooltip key={item.label} content={item.label} side="right">{content}</Tooltip>;
            }
            return content;
          })}
        </nav>

        {!collapsed && !isMobile && (
          <div className="px-2 py-2 border-t border-zinc-800 max-h-[30vh] overflow-y-auto">
            <ResultHistory />
          </div>
        )}

        <div className="border-t border-zinc-800 px-2 py-3">
          {isAuthenticated && user ? (
            collapsed && !isMobile ? (
              <Tooltip content={user.username} side="right">
                <div className="flex items-center justify-center px-3 py-2">
                  <Avatar name={user.username} size="sm" />
                </div>
              </Tooltip>
            ) : (
              <div className="flex items-center gap-3 px-3 py-2">
                <Avatar name={user.username} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-zinc-200 truncate">{user.username}</div>
                </div>
                <button onClick={logout} className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-red-400 transition-colors" aria-label="Logout">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            )
          ) : (
            <button onClick={() => { window.location.href = "/login"; onMobileClose(); }} className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors">
              {!collapsed && <span>Login</span>}
            </button>
          )}
        </div>
      </aside>
    </>
  );
}