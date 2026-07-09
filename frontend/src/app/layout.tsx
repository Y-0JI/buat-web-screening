import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BSJP AI — Riset Saham Indonesia",
  description: "AI Search untuk Analisis Saham Indonesia",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body className="bg-zinc-950 text-zinc-100 min-h-screen">{children}</body>
    </html>
  );
}
