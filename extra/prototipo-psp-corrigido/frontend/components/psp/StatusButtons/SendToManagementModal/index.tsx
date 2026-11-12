import { Loader2, Send } from "lucide-react";
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

interface SendToManagementModalProps {
  updating: boolean;
  updatingAction: string | null;
  hasSelection: boolean;
  selectedCount: number;
  onConfirm: () => Promise<void> | void;
}

export function SendToManagementModal({
  updating,
  updatingAction,
  hasSelection,
  selectedCount,
  onConfirm,
}: SendToManagementModalProps) {
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
        {updatingAction === "send" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
        Enviar para validação da gestão
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Enviar para validação da gestão?</AlertDialogTitle>
          <AlertDialogDescription>
            {selectedCount} lançamento(s) será(ão) enviado(s) para aprovação da
            gestão. Após esta ação, os valores não poderão mais ser editados.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction disabled={updating} onClick={handleConfirm}>
            {updatingAction === "send" && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Confirmar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
