"use client";

import {
  ClipboardCheck,
  FileText,
  PanelLeft,
  PanelLeftClose,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Módulos do protótipo. Novos módulos entram aqui como novos itens.
const MENU_ITEMS = [
  { title: "Faturamento PSP", path: "/psp", icon: FileText },
  { title: "Serviços e Regras", path: "/service-rules", icon: ClipboardCheck },
];

interface AppSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function AppSidebar({ collapsed, onToggle }: AppSidebarProps) {
  const pathname = usePathname();

  const isActive = (path: string) => pathname.startsWith(path);

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "hidden md:flex fixed left-0 top-0 z-40 h-screen flex-col bg-sidebar border-r border-sidebar-border shadow-sm dark:shadow-none transition-[width] duration-300 ease-out",
          collapsed ? "w-16" : "w-64",
        )}
      >
        <div
          className={cn(
            "flex h-16 items-center border-b border-sidebar-border shrink-0",
            collapsed ? "justify-center px-2" : "gap-3 px-6",
          )}
        >
          {collapsed ? (
            <span className="text-sm font-bold text-sidebar-primary">e</span>
          ) : (
            <span className="text-lg font-bold text-sidebar-primary">PSP</span>
          )}
        </div>

        <div
          className={cn(
            "flex border-b border-sidebar-border shrink-0",
            collapsed ? "justify-center p-2" : "justify-end px-4 py-2",
          )}
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
            className="h-8 w-8 text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground cursor-pointer"
          >
            {collapsed ? (
              <PanelLeft className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </Button>
        </div>

        <nav
          className={cn(
            "flex-1 overflow-y-auto flex flex-col gap-1",
            collapsed ? "p-2" : "p-4",
          )}
        >
          {MENU_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            if (collapsed) {
              return (
                <Tooltip key={item.path}>
                  <TooltipTrigger asChild>
                    <Link
                      href={item.path}
                      className={cn(
                        "flex items-center justify-center rounded-lg p-2.5 transition-all duration-200",
                        active
                          ? "bg-primary text-primary-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-primary",
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">{item.title}</TooltipContent>
                </Tooltip>
              );
            }

            return (
              <Link
                key={item.path}
                href={item.path}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-primary",
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="flex-1">{item.title}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
    </TooltipProvider>
  );
}
