import { Info, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatCurrency } from "@/utils/formatter";
import type { ServiceRow } from "../../types";
import { getRuleTypeLabel } from "../../types";

interface MixedApprovalModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  updating: boolean;
  updatingAction: string | null;
  withClientApproval: ServiceRow[];
  withoutClientApproval: ServiceRow[];
  onConfirm: () => void;
}

const MONTH_NAMES = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

function formatReference(
  month: number | null | undefined,
  year: number | null | undefined,
) {
  if (!month || !year) return null;
  return `${MONTH_NAMES[month - 1]}/${year}`;
}

function ItemRow({ row }: { row: ServiceRow }) {
  const reference = formatReference(row.billingMonth, row.billingYear);

  return (
    <li className="flex items-start gap-3 py-1.5 border-b border-dashed last:border-0 border-current/15">
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono opacity-70">
            #{row.serviceCode}
          </span>
          <span className="text-sm font-medium truncate">
            {row.serviceName}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs opacity-70">
          <span>
            Regra:{" "}
            <span className="font-medium opacity-100">
              {getRuleTypeLabel(row.ruleType)}
            </span>
          </span>
          {row.programName && (
            <span>
              Programa:{" "}
              <span className="font-medium opacity-100">{row.programName}</span>
            </span>
          )}
          {reference && (
            <span>
              Ref: <span className="font-medium opacity-100">{reference}</span>
            </span>
          )}
          {row.quantity != null && (
            <span>
              Qtd:{" "}
              <span className="font-medium opacity-100">{row.quantity}</span>
            </span>
          )}
          {row.unitValue != null && (
            <span>
              Unit:{" "}
              <span className="font-medium opacity-100">
                {formatCurrency(row.unitValue)}
              </span>
            </span>
          )}
        </div>
      </div>
      <span className="text-sm font-semibold whitespace-nowrap shrink-0">
        {row.totalValue != null ? formatCurrency(row.totalValue) : "—"}
      </span>
    </li>
  );
}

function GroupTotal({ rows }: { rows: ServiceRow[] }) {
  const total = rows.reduce((sum, r) => sum + (r.totalValue ?? 0), 0);
  return (
    <div className="flex justify-between items-center pt-1.5 text-xs font-semibold">
      <span>{rows.length} lançamento(s)</span>
      <span>{formatCurrency(total)}</span>
    </div>
  );
}

export function MixedApprovalModal({
  open,
  onOpenChange,
  updating,
  updatingAction,
  withClientApproval,
  withoutClientApproval,
  onConfirm,
}: MixedApprovalModalProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!updating) onOpenChange(value);
      }}
    >
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Info className="h-5 w-5 text-warning" />
            Aprovação com destinos diferentes
          </DialogTitle>
          <DialogDescription>
            Os lançamentos selecionados possuem configurações diferentes de
            aprovação do cliente. Eles serão encaminhados de acordo com cada
            configuração.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2 overflow-y-auto pr-1">
          {withClientApproval.length > 0 && (
            <div className="rounded-md border border-current/20 bg-badge-cliente text-badge-cliente-fg p-3 space-y-2">
              <div className="flex items-center gap-2">
                {/* Chip sólido: inverte bg↔fg do mesmo par, então o contraste
                    se mantém correto nos dois temas. */}
                <Badge
                  variant="outline"
                  className="bg-badge-cliente-fg text-badge-cliente border-transparent"
                >
                  Aprovação do Cliente
                </Badge>
              </div>
              <ul className="space-y-0">
                {withClientApproval.map((row) => (
                  <ItemRow key={row.itemId} row={row} />
                ))}
              </ul>
              <GroupTotal rows={withClientApproval} />
            </div>
          )}

          {withoutClientApproval.length > 0 && (
            <div className="rounded-md border border-current/20 bg-badge-ativo text-badge-ativo-fg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="bg-badge-ativo-fg text-badge-ativo border-transparent"
                >
                  Revisão Financeira
                </Badge>
              </div>
              <ul className="space-y-0">
                {withoutClientApproval.map((row) => (
                  <ItemRow key={row.itemId} row={row} />
                ))}
              </ul>
              <GroupTotal rows={withoutClientApproval} />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updating}
          >
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={updating}>
            {updatingAction === "approve" && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            Confirmar Aprovação
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
