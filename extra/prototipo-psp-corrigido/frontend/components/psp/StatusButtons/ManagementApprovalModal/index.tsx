import { CheckCircle, Loader2 } from "lucide-react";
import { useState } from "react";
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

interface ManagementApprovalModalProps {
  updating: boolean;
  updatingAction: string | null;
  hasSelection: boolean;
  selectedCount: number;
  isMixedApproval: boolean;
  hasClientApprovalItems: boolean;
  onConfirm: () => Promise<void> | void;
}

export function ManagementApprovalModal({
  updating,
  updatingAction,
  hasSelection,
  selectedCount,
  isMixedApproval,
  hasClientApprovalItems,
  onConfirm,
}: ManagementApprovalModalProps) {
  const [open, setOpen] = useState(false);

  const handleConfirm = async () => {
    await onConfirm();
    setOpen(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger
        render={
          <Button
            variant="default"
            className="gap-2"
            disabled={updating || !hasSelection}
          />
        }
      >
        {updatingAction === "approve" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <CheckCircle className="h-4 w-4" />
        )}
        Aprovar lançamento
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Aprovar lançamento?</AlertDialogTitle>
          <AlertDialogDescription>
            {selectedCount} lançamento(s) será(ão) aprovado(s).
            {isMixedApproval
              ? " Alguns lançamentos requerem aprovação do cliente e outros seguirão direto para revisão financeira."
              : hasClientApprovalItems
                ? " O próximo passo será a aprovação do cliente."
                : " O lançamento seguirá para revisão financeira."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction disabled={updating} onClick={handleConfirm}>
            {updatingAction === "approve" && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Confirmar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
