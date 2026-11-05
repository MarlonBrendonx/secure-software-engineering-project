import { useState } from "react";
import { toast } from "sonner";
import type { PspMutations } from "../../Accordion";
import type { ServiceRow } from "../../types";

interface UseSaveReleaseParams {
  row: ServiceRow;
  clientId: string;
  selectedYear: number;
  selectedMonth: number;
  mutations?: PspMutations;
  onClose: () => void;
  onSuccess: () => void;
  // Values from useReleaseForm
  totalValue: number;
  quantity: string;
  baseValue: string;
  poNumber: string;
  invoiceDescription: string;
  notes: string;
  parsedPeriod: { year: number; month: number };
  parsedCompetence: { year: number; month: number };
}

export function useSaveRelease({
  row,
  clientId,
  selectedYear,
  selectedMonth,
  mutations,
  onClose,
  onSuccess,
  totalValue,
  quantity,
  baseValue,
  poNumber,
  invoiceDescription,
  notes,
  parsedPeriod,
  parsedCompetence,
}: UseSaveReleaseParams) {
  const [saving, setSaving] = useState(false);
  const [showSubsequentDialog, setShowSubsequentDialog] = useState(false);
  const [subsequentMonths, setSubsequentMonths] = useState("");

  const doSave = async (extraMonths: number = 0) => {
    if (totalValue === 0) {
      toast.error("O valor total não pode ser zero.");
      return;
    }

    setSaving(true);
    try {
      const isPercentage = row.ruleType === "percentual";
      const isMultiplication = row.ruleType === "multiplicacao";
      const parsedQuantity = parseFloat(quantity) || 0;

      const ruleSpecific: Record<string, number> = isPercentage
        ? { base_value: parseFloat(baseValue) || 0 }
        : { quantity: parsedQuantity };

      if (!isPercentage && !isMultiplication) {
        ruleSpecific.unit_value = totalValue / (parsedQuantity || 1);
      }

      const basePayload = {
        ...ruleSpecific,
        total_value: totalValue,
        po_number: poNumber || null,
        invoice_description: invoiceDescription || null,
        notes: notes || null,
        billing_month: parsedPeriod.month,
        billing_year: parsedPeriod.year,
        competence_month: parsedCompetence.month,
        competence_year: parsedCompetence.year,
      };

      if (row.itemId) {
        await mutations?.updateItem.mutateAsync({
          uuid: row.itemId,
          data: { version: row.version ?? 0, ...basePayload },
        });
        toast.success("Lançamento atualizado.");
      } else if (extraMonths > 0) {
        await mutations?.replicateItems.mutateAsync({
          client_uuid: clientId,
          reference_year: selectedYear,
          reference_month: selectedMonth,
          service_rule_uuid: row.serviceId,
          subsequent_months: extraMonths,
          program_uuid: row.programId,
          ...basePayload,
        });
        toast.success(
          `Lançamento criado e replicado para ${extraMonths} mês(es) subsequente(s).`,
        );
      } else {
        await mutations?.createItem.mutateAsync({
          client_uuid: clientId,
          reference_year: selectedYear,
          reference_month: selectedMonth,
          service_rule_uuid: row.serviceId,
          program_uuid: row.programId,
          ...basePayload,
        });
        toast.success("Lançamento criado.");
      }

      onClose();
      onSuccess();
    } catch {
      // Error toast handled globally by MutationCache
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    if (totalValue === 0) {
      toast.error("O valor total não pode ser zero.");
      return;
    }
    if (row.ruleType === "valor_fixo" && !row.itemId) {
      setShowSubsequentDialog(true);
      return;
    }
    await doSave(0);
  };

  const handleSubsequentConfirm = async () => {
    const months = parseInt(subsequentMonths, 10) || 0;
    setShowSubsequentDialog(false);
    setSubsequentMonths("");
    await doSave(months);
  };

  const handleSubsequentCancel = async () => {
    setShowSubsequentDialog(false);
    setSubsequentMonths("");
    await doSave(0);
  };

  return {
    saving,
    handleSave,
    // Subsequent dialog
    showSubsequentDialog,
    setShowSubsequentDialog,
    subsequentMonths,
    setSubsequentMonths,
    handleSubsequentConfirm,
    handleSubsequentCancel,
  };
}
