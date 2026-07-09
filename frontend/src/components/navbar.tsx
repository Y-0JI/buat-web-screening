"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <nav className="flex items-center justify-between px-6 py-3 border-b border-zinc-800 bg-zinc-950">
      <Link href="/" className="text-lg font-bold text-zinc-100">
        BSJP AI
      </Link>

      <div className="flex items-center gap-4">
        {isAuthenticated ? (
          <>
            <Link
              href="/dashboard"
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Dashboard
            </Link>
            <span className="text-sm text-zinc-500">{user?.username}</span>
            <button
              onClick={logout}
              className="text-sm text-red-400 hover:text-red-300 transition-colors"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="text-sm px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
            >
              Daftar
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
