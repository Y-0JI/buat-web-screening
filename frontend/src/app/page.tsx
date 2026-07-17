"use client";

import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-zinc-950">
          <div className="text-zinc-500 text-sm animate-pulse">Memuat...</div>
        </div>
      }
    >
      <AppShell />
    </Suspense>
  );
}
