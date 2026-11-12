import { Loader2, RotateCcw } from "lucide-react";
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

interface ResendApprovalModalProps {
  updating: boolean;
  updatingAction: string | null;
  hasSelection: boolean;
  selectedCount: number;
  onConfirm: () => Promise<void> | void;
}

export function ResendApprovalModal({
  updating,
  updatingAction,
  hasSelection,
  selectedCount,
  onConfirm,
}: ResendApprovalModalProps) {
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
        {updatingAction === "resend" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RotateCcw className="h-4 w-4" />
        )}
        Reenviar para aprovação
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Reenviar para aprovação?</AlertDialogTitle>
          <AlertDialogDescription>
            {selectedCount} lançamento(s) reprovado(s) será(ão) reenviado(s)
            para aprovação da gestão.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction disabled={updating} onClick={handleConfirm}>
            {updatingAction === "resend" && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Confirmar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
