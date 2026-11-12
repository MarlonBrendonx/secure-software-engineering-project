import { Loader2, XCircle } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";

interface RejectionModalProps {
  updating: boolean;
  updatingAction: string | null;
  hasSelection: boolean;
  itemCount?: number;
  onReject: (motivo: string) => void;
}

export function RejectionModal({
  updating,
  updatingAction,
  hasSelection,
  itemCount,
  onReject,
}: RejectionModalProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  const handleReject = () => {
    if (!reason.trim()) {
      toast({
        title: "Erro",
        description: "Informe o motivo da reprovação.",
        variant: "destructive",
      });
      return;
    }
    onReject(reason.trim());
    setOpen(false);
    setReason("");
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) setReason("");
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="destructive"
          className="gap-2"
          disabled={updating || !hasSelection}
        >
          {updatingAction === "reject" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          Reprovar
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reprovar lançamento</DialogTitle>
          <DialogDescription>
            {itemCount !== undefined ? (
              <>
                Você está prestes a reprovar{" "}
                <strong>
                  {itemCount} lançamento{itemCount === 1 ? "" : "s"}
                </strong>
                . {itemCount === 1 ? "Ele poderá" : "Eles poderão"} ser
                reenviado{itemCount === 1 ? "" : "s"} após correção. Informe o
                motivo da reprovação.
              </>
            ) : (
              "O lançamento será reprovado e poderá ser reenviado após correção. Informe o motivo da reprovação."
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="motivo">Motivo da reprovação *</Label>
          <Textarea
            id="motivo"
            placeholder="Descreva o motivo da reprovação..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            maxLength={500}
          />
          <p className="text-xs text-muted-foreground text-right">
            {reason.length}/500
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button
            variant="destructive"
            onClick={handleReject}
            disabled={updating || !reason.trim()}
          >
            {updatingAction === "reject" ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            Confirmar Reprovação
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
