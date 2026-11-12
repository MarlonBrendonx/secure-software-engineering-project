"use client";

import { usePathname } from "next/navigation";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { AccessDenied } from "@/components/layout/AccessDenied";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { Banner } from "@/components/layout/Banner";
import { UserMenu } from "@/components/layout/UserMenu";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  redirectToLogin,
  signOut,
  useSession,
} from "@/features/auth/lib/auth-client";
import { cn } from "@/lib/utils";

// Tabela de lançamentos precisa de largura; o menu recolhe automaticamente nessas rotas.
const AUTO_COLLAPSE_ROUTES = ["/psp"];

export default function SharedDashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, isPending } = useSession();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const onToggle = useCallback(() => setCollapsed((p) => !p), []);

  useEffect(() => {
    if (AUTO_COLLAPSE_ROUTES.some((route) => pathname.startsWith(route))) {
      setCollapsed(true);
    }
  }, [pathname]);

  useEffect(() => {
    if (!isPending && !session?.user) {
      redirectToLogin();
    }
  }, [isPending, session?.user]);

  if (isPending || !session?.user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Carregando...</div>
      </div>
    );
  }

  if (session.user.role === "none") {
    return (
      <AccessDenied userName={session.user.display_name ?? session.user.name} />
    );
  }

  const displayName =
    session.user.name ??
    session.user.username ??
    session.user.email ??
    "Usuário";

  return (
    <div className="min-h-screen bg-background">
      <AppSidebar collapsed={collapsed} onToggle={onToggle} />

      <div
        className={cn(
          "min-h-screen ml-0 transition-[margin-left] duration-300 ease-out",
          collapsed ? "md:ml-16" : "md:ml-64",
        )}
      >
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <span className="font-medium">Plataforma de Faturamento</span>
          <Banner stylesTag="rounded-md" />
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <UserMenu
              userName={displayName}
              userInitials={displayName.charAt(0).toUpperCase()}
              userEmail={session.user.email ?? session.user.username}
              onLogout={() => signOut()}
            />
          </div>
        </header>
        <main className="p-2 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
