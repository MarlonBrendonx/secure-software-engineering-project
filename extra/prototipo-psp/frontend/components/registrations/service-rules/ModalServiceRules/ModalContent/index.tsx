"use client";

import { Info, MinusCircle, PlusCircle } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Program } from "@/lib/registrations/programs";
import {
  RANGE_TYPES,
  RULE_TYPES,
  type ServiceRangeFormData,
  type ServiceRuleFormData,
} from "../../types";

type ModalContentProps = {
  formData: ServiceRuleFormData;
  setFormData: Dispatch<SetStateAction<ServiceRuleFormData>>;
  programs: Program[];
  hasBillingItems: boolean;
};

const ModalContent = ({
  formData,
  setFormData,
  programs,
  hasBillingItems,
}: ModalContentProps) => {
  // ─── Range helpers ──────────────────────────────────────────────────────

  const syncLastRangeFrom = (
    ranges: ServiceRangeFormData[],
  ): ServiceRangeFormData[] => {
    if (ranges.length < 2) return ranges;
    const lastIdx = ranges.length - 1;
    if (!ranges[lastIdx].last_range) return ranges;
    const prev = ranges[lastIdx - 1];
    const nextFrom = prev.range_to
      ? String(Math.floor(Number.parseFloat(prev.range_to)) + 1)
      : "";
    if (ranges[lastIdx].range_from === nextFrom) return ranges;
    return ranges.map((r, i) =>
      i === lastIdx ? { ...r, range_from: nextFrom } : r,
    );
  };

  // ─── Range handlers ─────────────────────────────────────────────────────

  const addRange = () => {
    setFormData((prev) => {
      // First click: create first range (from=0) + last range
      if (prev.ranges.length === 0) {
        return {
          ...prev,
          ranges: [
            {
              id: crypto.randomUUID(),
              range_from: "0",
              range_to: "",
              range_type: "fixed_value",
              value: "",
              last_range: false,
            },
            {
              id: crypto.randomUUID(),
              range_from: "",
              range_to: "",
              range_type: "fixed_value",
              value: "",
              last_range: true,
            },
          ],
        };
      }

      // Subsequent clicks: insert new range before the last range
      const lastIdx = prev.ranges.length - 1;
      const rangesWithoutLast = prev.ranges.slice(0, lastIdx);
      const lastRange = prev.ranges[lastIdx];
      const prevRange = rangesWithoutLast[rangesWithoutLast.length - 1];

      const newFrom = prevRange?.range_to
        ? String(Math.floor(Number.parseFloat(prevRange.range_to)) + 1)
        : "";

      const newRange: ServiceRangeFormData = {
        id: crypto.randomUUID(),
        range_from: newFrom,
        range_to: "",
        range_type: "fixed_value",
        value: "",
        last_range: false,
      };

      return {
        ...prev,
        ranges: syncLastRangeFrom([...rangesWithoutLast, newRange, lastRange]),
      };
    });
  };

  const removeRange = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      ranges: syncLastRangeFrom(prev.ranges.filter((_, i) => i !== index)),
    }));
  };

  const updateRange = (
    index: number,
    field: keyof ServiceRangeFormData,
    val: string,
  ) => {
    setFormData((prev) => {
      let newRanges = prev.ranges.map((r, i) =>
        i === index ? { ...r, [field]: val } : r,
      );
      if (field === "range_to") {
        newRanges = syncLastRangeFrom(newRanges);
      }
      return { ...prev, ranges: newRanges };
    });
  };

  // ─── Program handlers ────────────────────────────────────────────────────

  const isProgramSelected = (programUuid: string) =>
    formData.selected_programs.some((p) => p.program_uuid === programUuid);

  // Programa inativo só aparece se já estiver vinculado, para a edição não perdê-lo em silêncio.
  const visiblePrograms = programs.filter(
    (p) => p.status === "Ativo" || isProgramSelected(p.uuid),
  );

  const toggleProgram = (programUuid: string) => {
    if (isProgramSelected(programUuid)) {
      setFormData((prev) => ({
        ...prev,
        selected_programs: prev.selected_programs.filter(
          (p) => p.program_uuid !== programUuid,
        ),
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        selected_programs: [
          ...prev.selected_programs,
          { program_uuid: programUuid },
        ],
      }));
    }
  };

  return (
    <div className="space-y-6">
      {hasBillingItems && (
        <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
          <Info className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            Este serviço já possui lançamentos. Somente o{" "}
            <strong>status</strong> pode ser alterado.
          </span>
        </div>
      )}

      {/* ── Seção 1: Dados Básicos ────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="name">Nome do Serviço *</Label>
          <Input
            id="name"
            placeholder="Nome do serviço"
            maxLength={100}
            value={formData.name}
            disabled={hasBillingItems}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="status">Status</Label>
          <Select
            value={formData.status}
            onValueChange={(value) =>
              setFormData({ ...formData, status: value })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Ativo">Ativo</SelectItem>
              <SelectItem value="Inativo">Inativo</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="requires_client_approval">
          Exige aprovação do cliente
        </Label>
        <Select
          value={formData.requires_client_approval ? "true" : "false"}
          disabled={hasBillingItems}
          onValueChange={(value) =>
            setFormData({
              ...formData,
              requires_client_approval: value === "true",
            })
          }
        >
          <SelectTrigger id="requires_client_approval">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="true">Sim</SelectItem>
            <SelectItem value="false">Não</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Com "Sim", o lançamento só segue pela aprovação do cliente, e o
          cliente precisa ter o contrato com aprovação habilitada.
        </p>
      </div>

      {/* ── Seção 2: Programas Vinculados ───────────────────────── */}
      <div className="space-y-2">
        <Label>Vínculo de Programas</Label>
        <Card>
          <CardContent className="p-6 space-y-3">
            <Label>Programas Vinculados</Label>
            {visiblePrograms.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Nenhum programa ativo para este cliente.
              </p>
            ) : (
              <div className="rounded-md border p-4 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {visiblePrograms.map((program) => (
                    <div
                      key={program.uuid}
                      className="flex items-center gap-2 min-w-0"
                    >
                      <Checkbox
                        id={`prog-${program.uuid}`}
                        checked={isProgramSelected(program.uuid)}
                        onCheckedChange={() => toggleProgram(program.uuid)}
                        disabled={hasBillingItems}
                        className="shrink-0"
                      />
                      <Label
                        htmlFor={`prog-${program.uuid}`}
                        className="text-sm font-normal cursor-pointer truncate"
                      >
                        {program.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Seção 3: Tipo de Regra ────────────────────────────────── */}
      <div className="space-y-2">
        <Label htmlFor="rule_type">Tipo de Regra *</Label>
        <Select
          value={formData.rule_type}
          disabled={hasBillingItems}
          onValueChange={(value) =>
            setFormData({
              ...formData,
              rule_type: value,
              percentage: "",
              base_value: "",
              ranges: [],
            })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Selecione o tipo de regra" />
          </SelectTrigger>
          <SelectContent>
            {RULE_TYPES.map((rt) => (
              <SelectItem key={rt.value} value={rt.value}>
                {rt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* ── Campos dinâmicos por tipo de regra ────────────────────── */}
      {formData.rule_type === "percentage" && (
        <div className="space-y-2">
          <Label htmlFor="percentage">Percentual (0,01 - 100,00) *</Label>
          <Input
            id="percentage"
            type="number"
            step="0.01"
            min="0.01"
            max="100"
            placeholder="Ex: 15.00"
            value={formData.percentage}
            disabled={hasBillingItems}
            onChange={(e) =>
              setFormData({
                ...formData,
                percentage: e.target.value,
              })
            }
          />
        </div>
      )}

      {formData.rule_type === "multiplication" && (
        <div className="space-y-2">
          <Label htmlFor="base_value">Valor Base R$ *</Label>
          <Input
            id="base_value"
            type="number"
            step="0.01"
            min="0.01"
            placeholder="Ex: 2.50"
            value={formData.base_value}
            disabled={hasBillingItems}
            onChange={(e) =>
              setFormData({
                ...formData,
                base_value: e.target.value,
              })
            }
          />
        </div>
      )}

      {/* ── Seção 4: Faixas de Range ──────────────────────────────── */}
      {formData.rule_type === "range" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>Faixas de Range</Label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2 cursor-pointer"
              onClick={addRange}
              disabled={hasBillingItems}
            >
              <PlusCircle className="h-4 w-4" />
              Adicionar Faixa
            </Button>
          </div>

          {formData.ranges.length > 0 && (
            <div className="rounded-md border p-4 space-y-3">
              <div className="grid grid-cols-[1fr_1fr_1.2fr_1fr_auto] gap-3">
                <Label className="text-xs text-muted-foreground">De</Label>
                <Label className="text-xs text-muted-foreground">Até</Label>
                <Label className="text-xs text-muted-foreground">Tipo</Label>
                <Label className="text-xs text-muted-foreground">
                  Valor (R$)
                </Label>
                <div className="w-9" />
              </div>

              {formData.ranges.map((range, index) => {
                const isFirst = index === 0;
                const isLast = range.last_range;
                const isLocked = isFirst || isLast || hasBillingItems;

                return (
                  <div
                    key={range.id}
                    className="grid grid-cols-[1fr_1fr_1.2fr_1fr_auto] gap-3 items-center"
                  >
                    <Input
                      type="number"
                      step="1"
                      min="0"
                      placeholder="0"
                      value={range.range_from}
                      disabled={isLocked}
                      onChange={(e) =>
                        updateRange(index, "range_from", e.target.value)
                      }
                    />
                    {isLast ? (
                      <Input disabled placeholder="∞" value="" />
                    ) : (
                      <Input
                        type="number"
                        step="1"
                        min="0"
                        placeholder="0"
                        value={range.range_to}
                        onChange={(e) =>
                          updateRange(index, "range_to", e.target.value)
                        }
                      />
                    )}
                    <Select
                      value={range.range_type}
                      onValueChange={(v) => updateRange(index, "range_type", v)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione" />
                      </SelectTrigger>
                      <SelectContent>
                        {RANGE_TYPES.map((rt) => (
                          <SelectItem key={rt.value} value={rt.value}>
                            {rt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0"
                      value={range.value}
                      onChange={(e) =>
                        updateRange(index, "value", e.target.value)
                      }
                    />
                    {isLocked ? (
                      <div className="w-9" />
                    ) : (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                        onClick={() => removeRange(index)}
                      >
                        <MinusCircle className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModalContent;
