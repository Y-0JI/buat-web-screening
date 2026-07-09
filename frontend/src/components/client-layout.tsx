"use client";

import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/navbar";

export function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <Navbar />
      {children}
    </AuthProvider>
  );
}
