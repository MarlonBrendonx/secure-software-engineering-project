import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useItemHistory } from "@/lib/billing/psp";
import type { ServiceRow } from "../types";
import AdditionalInformation from "./AdditionalInformation";
import ServiceDetail from "./ServiceDetail";
import Timeline from "./Timeline";
import TransactionCostInfo from "./TransactionCostInfo";

interface DetailReleaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  row: ServiceRow;
  clientName: string;
}

const DetailModalRelease = ({
  open,
  onOpenChange,
  row,
  clientName,
}: DetailReleaseDialogProps) => {
  const { data: history = [], isLoading: isHistoryLoading } = useItemHistory(
    row.itemId,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Detalhes do Lançamento</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <ServiceDetail row={row} clientName={clientName} />
          <TransactionCostInfo row={row} />

          <AdditionalInformation row={row} />

          {!row.itemId && (
            <div className="border-t pt-3 text-center py-6">
              <p className="text-muted-foreground text-sm">
                Este serviço ainda não possui lançamento para o período
                selecionado.
              </p>
            </div>
          )}

          <Timeline
            history={history}
            status={row.status}
            hasItem={!!row.itemId}
            isLoading={isHistoryLoading}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};
export default DetailModalRelease;
