"use client";

import { LogOut, ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { signOut } from "@/features/auth/lib/auth-client";

interface AccessDeniedProps {
  userName?: string;
}

// Usuário autenticado sem perfil (role "none") não acessa o protótipo.
export function AccessDenied({ userName }: AccessDeniedProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="mx-auto max-w-md text-center space-y-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <ShieldX className="h-8 w-8 text-destructive" />
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-foreground">
            Acesso não autorizado
          </h1>
          <p className="text-muted-foreground">
            {userName ? (
              <>
                Olá, <strong>{userName}</strong>.
              </>
            ) : null}{" "}
            Sua conta não possui um perfil de acesso atribuído.
          </p>
        </div>

        <Button
          variant="outline"
          className="gap-2 cursor-pointer"
          onClick={() => signOut()}
        >
          <LogOut className="h-4 w-4" />
          Sair
        </Button>
      </div>
    </div>
  );
}
