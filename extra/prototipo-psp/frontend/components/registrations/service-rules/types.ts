// ─── Rule Type Constants ─────────────────────────────────────────────────────

export const RULE_TYPES = [
  { value: "fixed_value", label: "Valor Fixo" },
  { value: "percentage", label: "% Percentual" },
  { value: "multiplication", label: "Multiplicação" },
  { value: "range", label: "Range" },
  { value: "variable_value", label: "Valor Variável" },
] as const;

export const RANGE_TYPES = [
  { value: "fixed_value", label: "Valor Fixo" },
  { value: "per_unit_value", label: "Valor por Unidade" },
] as const;

export function getRuleTypeLabel(value: string): string {
  const found = RULE_TYPES.find((rt) => rt.value === value);
  return found?.label ?? value;
}

// ─── API Response Interfaces ─────────────────────────────────────────────────

export interface ServiceRuleProgram {
  program_uuid: string;
  program_name?: string;
}

export interface ServiceRange {
  range_from: number;
  range_to: number | null;
  range_type: string;
  value: number | null;
  last_range: boolean;
}

export interface ServiceRule {
  uuid: string;
  client_uuid: string;
  code: number;
  name: string;
  status: string;
  rule_type: string;
  percentage: number | null;
  base_value: number | null;
  requires_client_approval: boolean;
  ranges: ServiceRange[];
  programs: ServiceRuleProgram[];
  has_billing_items: boolean;
  created_at: string;
  updated_at: string;
  version: number;
}

// ─── Form State Interfaces ───────────────────────────────────────────────────

export interface SelectedProgram {
  program_uuid: string;
}

export interface ServiceRangeFormData {
  id: string;
  range_from: string;
  range_to: string;
  range_type: string;
  value: string;
  last_range: boolean;
}

export type ServiceRuleFormData = {
  name: string;
  status: string;
  rule_type: string;
  percentage: string;
  base_value: string;
  requires_client_approval: boolean;
  ranges: ServiceRangeFormData[];
  selected_programs: SelectedProgram[];
};

export const initialServiceRuleFormData: ServiceRuleFormData = {
  name: "",
  status: "Ativo",
  rule_type: "",
  percentage: "",
  base_value: "",
  requires_client_approval: false,
  ranges: [],
  selected_programs: [],
};
