"use client";

import { Eye, EyeOff, Pill } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import { Banner } from "@/components/layout/Banner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signIn } from "@/features/auth/lib/auth-client";

const DEFAULT_PATH = "/psp";

// Aceita só caminhos da própria origem, para o parâmetro callbackUrl não virar open redirect.
// A origem é conferida depois de resolver a URL com o parser do navegador: ele normaliza
// `\` e tabs antes de navegar, então `/\evil.com` passaria numa checagem só por prefixo.
function safeCallbackUrl(raw: string | null): string {
  if (!raw) return DEFAULT_PATH;
  try {
    const url = new URL(raw, window.location.origin);
    // Depois de remover segmentos como "/./", o pathname pode virar "//host"; devolvido como
    // caminho relativo, ele trocaria de host. Por isso também se rejeita o prefixo "//".
    if (
      url.origin !== window.location.origin ||
      url.pathname === "/" ||
      url.pathname.startsWith("//")
    ) {
      return DEFAULT_PATH;
    }
    // href absoluto: o navegador não resolve o destino uma segunda vez.
    return url.href;
  } catch {
    return DEFAULT_PATH;
  }
}

function LoginForm() {
  const searchParams = useSearchParams();
  const rawCallbackUrl = searchParams.get("callbackUrl");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await signIn({ username, password, otp });

      if (result.error) {
        toast.error(result.error.message);
        return;
      }

      // Os cookies de sessão vêm do backend. Basta redirecionar.
      // Resolvido só no clique: `window` não existe na renderização do servidor.
      window.location.replace(safeCallbackUrl(rawCallbackUrl));
    } catch (_err) {
      toast.error("Ocorreu um erro inesperado");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[400px]">
      <Card className="border-0 bg-ep-chumbo shadow-xl ring-1 ring-white/10">
        <CardHeader className="space-y-3 pb-6 text-center">
          <div className="flex items-center justify-center gap-2 text-white">
            <Pill className="h-6 w-6" aria-hidden="true" />
            <span className="text-2xl font-bold tracking-tight">
              Faturamento PSP
            </span>
          </div>
          <CardTitle className="text-xl font-semibold tracking-tight text-white">
            Entrar
          </CardTitle>
          <CardDescription className="text-white/60">
            Acesse o Faturamento PSP com seu usuário e senha
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-white/80">
                Usuário
              </Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="Digite seu usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="h-11 rounded-lg border-white/20 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-2 focus-visible:ring-accent"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-white/80">
                Senha
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Digite sua senha"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 rounded-lg border-white/20 bg-white/10 pr-11 text-white placeholder:text-white/50 focus-visible:ring-2 focus-visible:ring-accent"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 h-8 w-8 -translate-y-1/2 text-white/60 hover:bg-white/15 hover:text-white"
                  onClick={() => setShowPassword((p) => !p)}
                  aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="otp" className="text-white/80">
                Código MFA (OTP){" "}
                <span className="text-white/50">(opcional)</span>
              </Label>
              <Input
                id="otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="Somente se sua conta exigir"
                value={otp}
                onChange={(e) => setOtp(e.target.value.trim())}
                className="h-11 rounded-lg border-white/20 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-2 focus-visible:ring-accent"
              />
            </div>

            <Button
              type="submit"
              className="h-11 w-full rounded-lg font-medium bg-primary text-primary-foreground hover:bg-primary/90"
              disabled={isLoading}
            >
              {isLoading ? "Entrando..." : "Entrar"}
            </Button>
          </form>

          <p className="text-center text-xs text-white/60">
            Usuários de demonstração (admin, analyst, manager) estão descritos
            no README do projeto.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-bg-app via-bg-surface to-bg-surface-2 p-4">
      <Banner styles="fixed inset-x-0 top-0 z-50 flex w-full justify-center pointer-events-none" />
      <Suspense
        fallback={
          <Card className="w-full max-w-[400px] border-0 bg-ep-chumbo shadow-xl ring-1 ring-white/10">
            <CardHeader className="text-center">
              <CardTitle className="text-xl text-white">
                Carregando...
              </CardTitle>
            </CardHeader>
          </Card>
        }
      >
        <LoginForm />
      </Suspense>
    </main>
  );
}
