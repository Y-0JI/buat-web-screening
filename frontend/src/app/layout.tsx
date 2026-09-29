import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Analisis Saham AI — IDX Copilot",
  description: "Asisten AI untuk riset saham IDX (data IDX Edge PRO).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body className="bg-zinc-950 text-zinc-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
