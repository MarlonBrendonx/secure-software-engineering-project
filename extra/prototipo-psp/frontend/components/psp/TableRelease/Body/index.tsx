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
import { Checkbox } from "@/components/ui/checkbox";
import { TableBody, TableCell, TableRow } from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import TruncatedText from "@/components/ui/truncated-text";
import { formatCurrency } from "@/utils/formatter";
import { DisplayStatus } from "@/utils/psp/statusMap";
import { getStatusBadge } from "../../Common/StatusBadge";
import type { ServiceRow } from "../../types";

type BodyProps = {
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

const Body = ({
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
}: BodyProps) => {
  return (
    <TableBody>
      {rows.map((row, idx) => {
        const isItem = row.itemId !== null;
        const isNoRelease = row.status === DisplayStatus.SemLancamento;
        const loading = actionLoading === row.itemId;
        const mediaKey = `${clientId}:${row.serviceId}`;
        const media = mediaMap.get(mediaKey);

        const status = getStatusBadge(row.status);

        const isLocked =
          row.status === DisplayStatus.AprovacaoGestao ||
          row.status === DisplayStatus.AprovacaoCliente ||
          row.status === DisplayStatus.RevisaoFinanceira ||
          row.status === DisplayStatus.Aprovado;

        return (
          <TableRow
            key={row.itemId || `${row.serviceId}-${idx}`}
            className={`${selectedIds.includes(row.itemId || "") ? "bg-primary/5" : ""} ${isNoRelease ? "opacity-60" : ""}`}
          >
            {isEditable && (
              <TableCell>
                {isItem ? (
                  <Checkbox
                    checked={selectedIds.includes(row.itemId as string)}
                    onCheckedChange={(checked) =>
                      handleSelectItem(row.itemId as string, !!checked)
                    }
                  />
                ) : (
                  <div className="w-4" />
                )}
              </TableCell>
            )}
            <TableCell className="max-w-[150px]">
              {(() => {
                const programs = row.programs ?? [];

                const programName = row.programName || programs[0]?.name || "";
                if (programs.length === 0 || programs.length === 1)
                  return (
                    <span className="truncate block cursor-default">
                      {programName}
                    </span>
                  );
                const display = `${programs[0].name}, ...`;
                const full = programs.map((p) => p.name).join(", ");
                return <TruncatedText content={full}>{display}</TruncatedText>;
              })()}
            </TableCell>
            <TableCell className="font-medium">{row.serviceName}</TableCell>
            <TableCell className="text-right">
              <span className="font-medium">
                {isItem ? formatCurrency(row.totalValue || 0) : "—"}
              </span>
            </TableCell>
            <TableCell className="text-right">
              {media !== undefined ? (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="inline-flex items-center gap-1 text-xs">
                        {formatCurrency(media)}
                        {isItem &&
                          row.totalValue !== null &&
                          (row.totalValue > media ? (
                            <TrendingUp className="h-3.5 w-3.5 text-success" />
                          ) : row.totalValue < media ? (
                            <TrendingDown className="h-3.5 w-3.5 text-destructive" />
                          ) : null)}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>Média dos últimos 3 meses</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : (
                <span className="text-xs text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {row.poNumber || "—"}
            </TableCell>
            <TableCell className="text-muted-foreground max-w-[150px] truncate">
              <TruncatedText>{row.invoiceDescription || "-"}</TruncatedText>
            </TableCell>
            <TableCell>{status}</TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                {(isNoRelease || (isEditable && isItem)) && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setEditRow(row)}
                    title={isNoRelease ? "Lançar" : "Editar"}
                    disabled={isLocked && !isOverview}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                )}
                {isItem && canDelete && (
                  <AlertDialog>
                    <AlertDialogTrigger
                      render={
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          disabled={loading}
                          title="Excluir conteúdo"
                        />
                      }
                    >
                      {loading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
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
                            <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                          )}
                          Excluir
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => setDetailRow(row)}
                  title="Detalhar"
                >
                  <Eye className="h-3.5 w-3.5" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        );
      })}
    </TableBody>
  );
};

export default Body;
