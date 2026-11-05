import {
  ArrowRight,
  Clock,
  FileEdit,
  FilePlus,
  FileX,
  Loader2,
  RefreshCw,
} from "lucide-react";
import type {
  BillingHistoryChanges,
  BillingItemHistoryAction,
} from "@/components/psp/types";
import { formatDateTime } from "@/utils/psp/formatters";
import { getStatusBadge } from "../../Common/StatusBadge";

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

interface FieldConfig {
  label: string;
  format: "currency" | "integer" | "month" | "text";
}

const FIELD_CONFIG: Record<string, FieldConfig> = {
  valor_unitario: { label: "Valor unitário", format: "currency" },
  valor_total: { label: "Valor total", format: "currency" },
  quantidade: { label: "Quantidade", format: "integer" },
  observacoes: { label: "Observações", format: "text" },
  numero_po: { label: "Nº PO", format: "text" },
  descricao_fatura: { label: "Descrição da fatura", format: "text" },
  mes_competencia: { label: "Mês competência", format: "month" },
  ano_competencia: { label: "Ano competência", format: "integer" },
};

function fieldLabel(field: string): string {
  return FIELD_CONFIG[field]?.label ?? field.replaceAll("_", " ");
}

function formatValue(value: string | null, field?: string): string {
  if (value === null || value === "") return "—";

  const format = field ? FIELD_CONFIG[field]?.format : undefined;

  if (format === "month") {
    const idx = Number(value) - 1;
    return MONTH_NAMES[idx] ?? value;
  }

  if (format === "integer") {
    const num = Number(value);
    return Number.isNaN(num) ? value : String(Math.round(num));
  }

  if (format === "currency") {
    const num = Number(value);
    if (!Number.isNaN(num)) {
      return num.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }
  }

  // Fallback: se for numérico decimal sem config, formata como currency
  if (!format) {
    const num = Number(value);
    if (!Number.isNaN(num) && /^\d+\.\d+$/.test(value)) {
      return num.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }
  }

  return value;
}

function ChangesDetail({ changes }: { changes: BillingHistoryChanges }) {
  return (
    <div className="mt-2 rounded border bg-muted/30 p-2 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <FileEdit className="h-3 w-3" />
        <span>{changes.item_label}</span>
      </div>
      <div className="space-y-1">
        {changes.fields.map((f) => (
          <div
            key={f.field}
            className="flex items-center gap-1.5 text-xs flex-wrap"
          >
            <span className="font-medium text-foreground/80 shrink-0">
              {fieldLabel(f.field)}:
            </span>
            <span className="text-destructive/80 line-through">
              {formatValue(f.old, f.field)}
            </span>
            <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
            <span className="text-success font-medium">
              {formatValue(f.new, f.field)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const ACTION_LABELS: Record<BillingItemHistoryAction, string> = {
  lancamento_criado: "Lançamento criado",
  lancamento_atualizado: "Lançamento atualizado",
  lancamento_deletado: "Lançamento excluído",
  mudanca_status: "Mudança de status",
};

const ACTION_ICONS: Record<BillingItemHistoryAction, typeof Clock> = {
  lancamento_criado: FilePlus,
  lancamento_atualizado: FileEdit,
  lancamento_deletado: FileX,
  mudanca_status: RefreshCw,
};

export interface HistoryItem {
  id: string;
  itemId: string;
  action?: BillingItemHistoryAction;
  previousStatus: string | null;
  newStatus: string;
  notes: string;
  changedBy: string | null;
  created_at: string;
  changes: BillingHistoryChanges | null;
}

interface TimelineProps {
  history: HistoryItem[];
  status: string;
  hasItem: boolean;
  isLoading?: boolean;
}

const Timeline = ({ history, status, hasItem, isLoading }: TimelineProps) => {
  return (
    <div className="border-t pt-3">
      <h4 className="text-sm font-semibold mb-3">Histórico de Status</h4>
      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : history.length > 0 ? (
        <div className="relative ml-3 max-h-60 overflow-y-auto pr-1">
          <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-border" />
          <div className="space-y-4">
            {history.map((h, idx) => {
              const ActionIcon = h.action ? ACTION_ICONS[h.action] : Clock;
              const actionLabel = h.action
                ? ACTION_LABELS[h.action]
                : undefined;

              return (
                <div key={h.id} className="relative pl-6">
                  <div
                    className={`absolute left-0 top-1 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                      idx === history.length - 1
                        ? "bg-primary border-primary"
                        : "bg-background border-muted-foreground/30"
                    }`}
                  >
                    <ActionIcon
                      className={`h-2.5 w-2.5 ${idx === history.length - 1 ? "text-primary-foreground" : "text-muted-foreground"}`}
                    />
                  </div>
                  <div>
                    {actionLabel && (
                      <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                        {actionLabel}
                      </span>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                      {h.previousStatus && h.previousStatus !== h.newStatus && (
                        <>
                          {getStatusBadge(h.previousStatus)}
                          <span className="text-xs text-muted-foreground">
                            →
                          </span>
                        </>
                      )}
                      {getStatusBadge(h.newStatus)}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDateTime(h.created_at)}
                      {h.changedBy && (
                        <span className="ml-2 text-foreground/70">
                          por <span className="font-medium">{h.changedBy}</span>
                        </span>
                      )}
                    </p>
                    {h.notes && (
                      <p className="text-xs mt-1 p-2 bg-muted/50 rounded text-foreground">
                        {h.notes}
                      </p>
                    )}
                    {h.changes && h.changes.fields.length > 0 && (
                      <ChangesDetail changes={h.changes} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : hasItem ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <div className="h-2 w-2 rounded-full bg-primary" />
            <span className="text-muted-foreground">Status atual:</span>
            {getStatusBadge(status)}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Nenhum histórico disponível.
        </p>
      )}
    </div>
  );
};

export default Timeline;
