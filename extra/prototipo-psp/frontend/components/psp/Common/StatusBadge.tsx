import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { DisplayStatus } from "@/utils/psp/statusMap";

const BADGE_SHAPE =
  "border-current/30 whitespace-nowrap text-[11px] px-1.5 py-0";

const STATUS_CLASSES: Record<string, string> = {
  [DisplayStatus.Novo]: "bg-badge-fin text-badge-fin-fg",
  [DisplayStatus.Reprovado]: `bg-badge-pend text-badge-pend-fg ${BADGE_SHAPE}`,
  [DisplayStatus.SemLancamento]: `bg-badge-arq text-badge-arq-fg ${BADGE_SHAPE}`,
  [DisplayStatus.AprovacaoGestao]: `bg-badge-rasc text-badge-rasc-fg ${BADGE_SHAPE}`,
  [DisplayStatus.AprovacaoCliente]: `bg-badge-cliente text-badge-cliente-fg ${BADGE_SHAPE}`,
  [DisplayStatus.RevisaoFinanceira]: `bg-badge-ativo text-badge-ativo-fg ${BADGE_SHAPE}`,
  [DisplayStatus.Aprovado]:
    "bg-badge-pub text-badge-pub-fg border-current/30 whitespace-nowrap",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "outline"> = {
  [DisplayStatus.Novo]: "secondary",
  [DisplayStatus.Reprovado]: "outline",
  [DisplayStatus.AprovacaoGestao]: "outline",
  [DisplayStatus.AprovacaoCliente]: "outline",
  [DisplayStatus.RevisaoFinanceira]: "outline",
  [DisplayStatus.Aprovado]: "default",
};

export function getStatusBadge(status: string) {
  if (status === DisplayStatus.SemLancamento) {
    return (
      <Badge
        className={cn(
          "whitespace-nowrap text-[11px] px-1.5 py-0",
          STATUS_CLASSES[status],
        )}
      >
        {DisplayStatus.SemLancamento}
      </Badge>
    );
  }

  const variant = STATUS_VARIANTS[status] ?? "outline";

  return (
    <Badge variant={variant} className={STATUS_CLASSES[status]}>
      {status}
    </Badge>
  );
}
