"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        Erro 404
      </p>
      <h1 className="mt-3 text-4xl font-bold text-foreground">
        Página não encontrada
      </h1>
      <p className="mt-4 max-w-sm text-base text-muted-foreground">
        O endereço acessado não existe ou está desativado neste ambiente.
      </p>
      <Link href="/psp" className={buttonVariants({ className: "mt-8 gap-2" })}>
        <ArrowLeft className="h-4 w-4" />
        Voltar ao início
      </Link>
    </div>
  );
}
