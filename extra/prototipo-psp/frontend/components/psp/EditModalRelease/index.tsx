import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatCurrency } from "@/utils/formatter";
import type { PspMutations } from "../Accordion";
import type { ServiceRow } from "../types";
import Form from "./Form";
import { useReleaseForm } from "./hooks/useReleaseForm";
import { useSaveRelease } from "./hooks/useSaveRelease";
import RuleSummaryCard from "./RuleSummaryCard";

interface EditReleaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  row: ServiceRow;
  clientId: string;
  clientName: string;
  selectedYear: number;
  selectedMonth: number;
  onSuccess: () => void;
  mutations?: PspMutations;
}

const EditModalRelease = ({
  open,
  onOpenChange,
  row,
  clientId,
  clientName,
  selectedYear,
  selectedMonth,
  onSuccess,
  mutations,
}: EditReleaseDialogProps) => {
  const form = useReleaseForm({
    open,
    row,
    selectedYear,
    selectedMonth,
  });

  const save = useSaveRelease({
    row,
    clientId,
    selectedYear,
    selectedMonth,
    mutations,
    onClose: () => onOpenChange(false),
    onSuccess,
    totalValue: form.totalValue,
    quantity: form.quantity,
    baseValue: form.baseValue,
    poNumber: form.poNumber,
    invoiceDescription: form.invoiceDescription,
    notes: form.notes,
    parsedPeriod: form.parsedPeriod,
    parsedCompetence: form.parsedCompetence,
  });

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {row.itemId ? "Editar" : "Novo"} Lançamento
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <RuleSummaryCard clientName={clientName} row={row} />

            <Form
              service={form.service}
              quantity={form.quantity}
              setQuantity={form.setQuantity}
              inputValue={form.inputValue}
              setInputValue={form.setInputValue}
              baseValue={form.baseValue}
              setBaseValue={form.setBaseValue}
              totalValue={form.totalValue}
              poNumber={form.poNumber}
              setPoNumber={form.setPoNumber}
              referencePeriod={form.referencePeriod}
              competencePeriod={form.competencePeriod}
              setCompetencePeriod={form.setCompetencePeriod}
              billingPeriod={form.billingPeriod}
              setBillingPeriod={form.setBillingPeriod}
              invoiceDescription={form.invoiceDescription}
              setInvoiceDescription={form.setInvoiceDescription}
              notes={form.notes}
              setNotes={form.setNotes}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button
              onClick={save.handleSave}
              disabled={save.saving || form.totalValue === 0}
            >
              {save.saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {row.itemId ? "Salvar Alterações" : "Criar Lançamento"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={save.showSubsequentDialog}
        onOpenChange={save.setShowSubsequentDialog}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Replicar para meses subsequentes?</DialogTitle>
            <DialogDescription>
              Deseja replicar este lançamento de{" "}
              <strong>{formatCurrency(form.totalValue)}</strong> para meses
              subsequentes?
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2">
            <Label className="whitespace-nowrap">Quantidade de meses:</Label>
            <Input
              type="number"
              min="1"
              max="12"
              value={save.subsequentMonths}
              onChange={(e) => save.setSubsequentMonths(e.target.value)}
              placeholder="Ex: 3"
              className="w-24"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={save.handleSubsequentCancel}>
              Não, apenas este mês
            </Button>
            <Button
              onClick={save.handleSubsequentConfirm}
              disabled={
                !save.subsequentMonths ||
                parseInt(save.subsequentMonths, 10) <= 0
              }
            >
              Sim, replicar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default EditModalRelease;
