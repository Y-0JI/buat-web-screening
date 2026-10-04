import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/theme-provider";

export const metadata: Metadata = {
  title: "Analisis Saham AI — IDX Copilot",
  description: "Asisten AI untuk riset saham IDX (data IDX Edge PRO).",
};

const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("idx_theme");if(t!=="light"&&t!=="dark")t="dark";document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme="dark";}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" data-theme="dark">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="bg-surface-0 text-text-primary min-h-screen antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
