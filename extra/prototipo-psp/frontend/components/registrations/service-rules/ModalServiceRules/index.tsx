"use client";

import type { Dispatch, SetStateAction } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import type { Program } from "@/lib/registrations/programs";
import { initialServiceRuleFormData, type ServiceRuleFormData } from "../types";
import ModalContent from "./ModalContent";
import ModalFooter from "./ModalFooter";
import ModalHeader from "./ModalHeader";

type ModalServiceRulesProps = {
  isDialogOpen: boolean;
  editingId: string | null;
  formData: ServiceRuleFormData;
  programs: Program[];
  hasBillingItems: boolean;
  handleSave: () => void;
  setFormData: Dispatch<SetStateAction<ServiceRuleFormData>>;
  setEditingId: (id: string | null) => void;
  setIsDialogOpen: (open: boolean) => void;
  loadingSave: boolean;
};

const ModalServiceRules = ({
  isDialogOpen,
  editingId,
  formData,
  programs,
  hasBillingItems,
  handleSave,
  setFormData,
  setEditingId,
  setIsDialogOpen,
  loadingSave,
}: ModalServiceRulesProps) => {
  // ─── Validation ──────────────────────────────────────────────────────────
  const hasName = !!formData.name.trim();
  const hasRuleType = !!formData.rule_type;

  const isPercentageValid =
    formData.rule_type !== "percentage" ||
    (Number.parseFloat(formData.percentage) >= 0.01 &&
      Number.parseFloat(formData.percentage) <= 100);

  const isBaseValueValid =
    formData.rule_type !== "multiplication" ||
    Number.parseFloat(formData.base_value) > 0;

  const isRangeValid =
    formData.rule_type !== "range" ||
    (formData.ranges.length > 0 &&
      formData.ranges.every(
        (r) =>
          !!r.range_from &&
          (r.last_range || !!r.range_to) &&
          !!r.range_type &&
          Number.parseFloat(r.value) > 0,
      ));

  const hasRangeInverted =
    formData.rule_type === "range" &&
    formData.ranges.some(
      (r) =>
        !r.last_range &&
        !!r.range_from &&
        !!r.range_to &&
        Number.parseFloat(r.range_to) < Number.parseFloat(r.range_from),
    );

  const hasRangeOverlap = (() => {
    if (formData.rule_type !== "range" || formData.ranges.length < 2)
      return false;
    const bounded = formData.ranges.filter((r) => !r.last_range);
    if (bounded.length < 2) return false;
    const sorted = bounded
      .map((r) => ({
        from: Number.parseFloat(r.range_from) || 0,
        to: Number.parseFloat(r.range_to) || 0,
      }))
      .sort((a, b) => a.from - b.from);
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i].from <= sorted[i - 1].to) return true;
    }
    return false;
  })();

  const hasRangeGap = (() => {
    if (formData.rule_type !== "range" || formData.ranges.length < 2)
      return false;
    const nonLast = formData.ranges.filter((r) => !r.last_range);
    if (nonLast.length < 2) return false;
    const sorted = nonLast
      .map((r) => ({
        from: Number.parseInt(r.range_from, 10) || 0,
        to: Number.parseInt(r.range_to, 10) || 0,
      }))
      .sort((a, b) => a.from - b.from);
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i].from !== sorted[i - 1].to + 1) return true;
    }
    return false;
  })();

  const isFormValid =
    hasName &&
    hasRuleType &&
    isPercentageValid &&
    isBaseValueValid &&
    isRangeValid &&
    !hasRangeInverted &&
    !hasRangeOverlap &&
    !hasRangeGap;

  const getDisabledReason = (): string | null => {
    if (loadingSave || isFormValid) return null;
    const missing: string[] = [];
    if (!hasName) missing.push("Nome do serviço");
    if (!hasRuleType) missing.push("Tipo de regra");
    if (!isPercentageValid)
      missing.push("Percentual deve estar entre 0,01 e 100,00");
    if (!isBaseValueValid) missing.push("Valor base é obrigatório");
    if (!isRangeValid)
      missing.push("Preencha os campos de Range (De, Até, Tipo, Valor)");
    if (hasRangeInverted)
      missing.push(
        "O valor 'Até' deve ser maior ou igual ao 'De' em cada faixa",
      );
    if (hasRangeOverlap) missing.push("Faixas de range não podem se sobrepor");
    if (hasRangeGap)
      missing.push(
        "Há buracos entre as faixas de range (ex: 0-300 → 302 deixa 301 descoberto)",
      );
    return `Preencha: ${missing.join(", ")}`;
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingId(null);
    setFormData(initialServiceRuleFormData);
  };

  return (
    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col p-4 sm:p-6">
        <ModalHeader editingId={editingId} />
        <form
          className="space-y-4 sm:space-y-6 overflow-y-auto flex-1 min-h-0 px-1"
          onSubmit={(e) => e.preventDefault()}
        >
          <ModalContent
            formData={formData}
            setFormData={setFormData}
            programs={programs}
            hasBillingItems={hasBillingItems}
          />
          <ModalFooter
            loadingSave={loadingSave}
            isFormValid={isFormValid}
            editingId={editingId}
            handleSave={handleSave}
            handleCloseModal={handleCloseDialog}
            disabledReason={getDisabledReason()}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default ModalServiceRules;
