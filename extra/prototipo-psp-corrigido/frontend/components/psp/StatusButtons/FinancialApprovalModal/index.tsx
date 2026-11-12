import { CheckCircle2, Loader2 } from "lucide-react";
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

interface FinancialApprovalModalProps {
  updating: boolean;
  updatingAction: string | null;
  hasSelection: boolean;
  selectedCount: number;
  onConfirm: () => Promise<void> | void;
}

export function FinancialApprovalModal({
  updating,
  updatingAction,
  hasSelection,
  selectedCount,
  onConfirm,
}: FinancialApprovalModalProps) {
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
            className="gap-2 bg-success hover:bg-success/90 text-success-foreground"
            disabled={updating || !hasSelection}
          />
        }
      >
        {updatingAction === "approve" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <CheckCircle2 className="h-4 w-4" />
        )}
        Aprovar Faturamento
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Aprovar Faturamento?</AlertDialogTitle>
          <AlertDialogDescription>
            {selectedCount} lançamento(s) será(ão) marcado(s) como Aprovado.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            className="bg-success hover:bg-success/90 text-success-foreground"
            disabled={updating}
            onClick={handleConfirm}
          >
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
