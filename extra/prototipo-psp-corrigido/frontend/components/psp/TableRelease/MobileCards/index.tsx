import {
  Eye,
  Loader2,
  Pencil,
  Trash2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { formatCurrency } from "@/utils/formatter";
import { DisplayStatus } from "@/utils/psp/statusMap";
import { getStatusBadge } from "../../Common/StatusBadge";
import type { ServiceRow } from "../../types";

type MobileCardsProps = {
  rows: ServiceRow[];
  mediaMap: Map<string, number>;
  selectedIds: string[];
  actionLoading: string | null;
  clientId: string;
  isEditable: boolean;
  isOverview: boolean;
  canDelete: boolean;
  handleSelectItem: (itemId: string, checked: boolean) => void;
  handleDeleteContent: (row: ServiceRow) => Promise<void>;
  setEditRow: (row: ServiceRow) => void;
  setDetailRow: (row: ServiceRow) => void;
};

const MobileCards = ({
  rows,
  mediaMap,
  actionLoading,
  selectedIds,
  clientId,
  isEditable,
  isOverview,
  canDelete,
  handleSelectItem,
  handleDeleteContent,
  setEditRow,
  setDetailRow,
}: MobileCardsProps) => {
  return (
    <div className="space-y-2">
      {rows.map((row, idx) => {
        const isItem = row.itemId !== null;
        const isSemLancamento = row.status === "Sem lançamento";
        const loading = actionLoading === row.itemId;
        const mediaKey = `${clientId}:${row.serviceId}`;
        const media = mediaMap.get(mediaKey);
        const isSelected = selectedIds.includes(row.itemId || "");
        const isLocked =
          row.status === DisplayStatus.AprovacaoGestao ||
          row.status === DisplayStatus.AprovacaoCliente ||
          row.status === DisplayStatus.RevisaoFinanceira ||
          row.status === DisplayStatus.Aprovado;

        return (
          <Card
            key={row.itemId || `${row.serviceId}-${idx}`}
            className={`${isSelected ? "ring-1 ring-primary bg-primary/5" : ""} ${isSemLancamento ? "opacity-60" : ""}`}
          >
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5 min-w-0 flex-1">
                  {isEditable && isItem && (
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={(checked) =>
                        handleSelectItem(row.itemId as string, !!checked)
                      }
                      className="mt-1"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold truncate leading-relaxed">
                      {row.serviceName}
                    </p>
                    {row.programName && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {row.programName}
                      </p>
                    )}
                  </div>
                </div>
                {getStatusBadge(row.status)}
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs pt-1">
                <div className="space-y-0.5">
                  <span className="text-muted-foreground block">Total</span>
                  <span className="font-semibold text-sm">
                    {isItem ? formatCurrency(row.totalValue || 0) : "—"}
                  </span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-muted-foreground block">Média 3m</span>
                  {media !== undefined ? (
                    <span className="inline-flex items-center gap-0.5 font-semibold text-sm">
                      {formatCurrency(media)}
                      {isItem &&
                        row.totalValue !== null &&
                        (row.totalValue > media ? (
                          <TrendingUp className="h-3 w-3 text-success" />
                        ) : row.totalValue < media ? (
                          <TrendingDown className="h-3 w-3 text-destructive" />
                        ) : null)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </div>
                {row.poNumber && (
                  <div className="space-y-0.5">
                    <span className="text-muted-foreground block">Nº PO</span>
                    <span className="font-medium">{row.poNumber}</span>
                  </div>
                )}
                {row.invoiceDescription && (
                  <div className="col-span-2 space-y-0.5">
                    <span className="text-muted-foreground block">
                      Descrição
                    </span>
                    <span className="font-medium truncate block">
                      {row.invoiceDescription}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-1 pt-2 border-t overflow-x-auto">
                {(isSemLancamento || (isEditable && isItem)) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => setEditRow(row)}
                    disabled={isLocked && !isOverview}
                  >
                    <Pencil className="h-3 w-3 mr-1" />
                    {isSemLancamento ? "Lançar" : "Editar"}
                  </Button>
                )}
                {isItem && canDelete && (
                  <AlertDialog>
                    <AlertDialogTrigger
                      render={
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                          disabled={loading}
                        />
                      }
                    >
                      {loading ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <Trash2 className="h-3 w-3 mr-1" />
                      )}
                      Excluir
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Excluir conteúdo?</AlertDialogTitle>
                        <AlertDialogDescription>
                          O conteúdo deste lançamento será removido.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={loading}>
                          Cancelar
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={async () => {
                            await handleDeleteContent(row);
                          }}
                          disabled={loading}
                        >
                          {loading && (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          )}
                          Excluir
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs ml-auto"
                  onClick={() => setDetailRow(row)}
                >
                  <Eye className="h-3 w-3 mr-1" />
                  Detalhes
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};

export default MobileCards;
