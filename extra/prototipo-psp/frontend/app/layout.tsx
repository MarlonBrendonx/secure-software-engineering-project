import type { Metadata, Viewport } from "next";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import type React from "react";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster as ShadcnToaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/features/auth/lib/auth-context";
import { QueryProvider } from "@/lib/providers/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Faturamento PSP",
    template: "%s | Faturamento PSP",
  },
  description: "Protótipo acadêmico de faturamento PSP",
  applicationName: "Faturamento PSP",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ),
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f8fa" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1d20" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <QueryProvider>
          <NuqsAdapter>
            <ThemeProvider>
              <AuthProvider>{children}</AuthProvider>
            </ThemeProvider>
          </NuqsAdapter>
        </QueryProvider>
        <Toaster
          position="bottom-center"
          style={
            {
              "--normal-bg": "var(--popover)",
              "--normal-text": "var(--popover-foreground)",
              "--normal-border": "var(--border)",
              "--border-radius": "var(--radius)",
            } as React.CSSProperties
          }
          toastOptions={{
            classNames: {
              success: "!border-l-4 !border-l-success",
              error: "!border-l-4 !border-l-destructive",
              warning: "!border-l-4 !border-l-warning",
            },
          }}
        />
        <ShadcnToaster />
      </body>
    </html>
  );
}
