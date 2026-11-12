import { TriangleAlert } from "lucide-react";

type BannerProps = {
  styles?: string;
  stylesTag?: string;
};

const ENV_COLORS: Record<string, { bg: string; text: string }> = {
  DEV: { bg: "bg-ep-azul", text: "text-ep-chumbo" },
  QA: { bg: "bg-ep-laranja", text: "text-ep-chumbo" },
  STG: { bg: "bg-ep-pink", text: "text-white" },
};

export function Banner({ styles, stylesTag }: BannerProps) {
  const env = process.env.NEXT_PUBLIC_ENV_BANNER;

  if (!env || !ENV_COLORS[env]) return null;

  const colors = ENV_COLORS[env];

  return (
    <div className={styles}>
      <span
        className={`pointer-events-auto flex w-full items-center justify-center gap-1.5  px-3 py-1 text-xs  ${colors.bg} ${colors.text} ${stylesTag}`}
      >
        <TriangleAlert className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">
          [{env}] - Ambiente de Testes/Sandbox - Não utilize dados reais
        </span>
      </span>
    </div>
  );
}
