"use client";

import { useState, type FormEvent } from "react";
import { Avatar } from "@/components/ui/avatar";
import { useAuth } from "@/lib/auth-context";

interface HeaderProps {
  onMenuToggle: () => void;
  onChatToggle: () => void;
  chatOpen: boolean;
  mode: string;
  onModeChange: (mode: string) => void;
}

export function Header({
  onMenuToggle,
  onChatToggle,
  chatOpen,
  mode,
  onModeChange,
}: HeaderProps) {
  const { isAuthenticated, user } = useAuth();
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Search is handled by parent page; this is the global search trigger
  };

  return (
    <header className="sticky top-0 z-30 h-14 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800">
      <div className="flex items-center h-full px-4 gap-4">
        {/* Mobile menu toggle */}
        <button
          onClick={onMenuToggle}
          className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors md:hidden"
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Search */}
        <form onSubmit={handleSubmit} className="flex-1 max-w-2xl">
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cari saham, berita, atau tanya AI..."
              className="w-full pl-10 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        </form>

        {/* Mode toggle */}
        <div className="hidden sm:flex items-center bg-zinc-900 border border-zinc-800 rounded-lg p-0.5">
          <button
            onClick={() => onModeChange("BSJP")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              mode === "BSJP"
                ? "bg-blue-600 text-white"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            BSJP
          </button>
          <button
            onClick={() => onModeChange("BPJS")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              mode === "BPJS"
                ? "bg-blue-600 text-white"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            BPJS
          </button>
        </div>

        {/* User / Chat toggle */}
        <div className="flex items-center gap-2">
          {isAuthenticated && user && (
            <div className="hidden sm:block">
              <Avatar name={user.username} size="sm" />
            </div>
          )}
          <button
            onClick={onChatToggle}
            className={`p-2 rounded-lg transition-colors ${
              chatOpen
                ? "bg-blue-600/15 text-blue-400"
                : "hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
            }`}
            aria-label="Toggle AI Assistant"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
