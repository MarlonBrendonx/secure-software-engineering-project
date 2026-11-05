// ─── Existing UI Types ─────────────────────────────────────────────────────

export interface ServiceRow {
  serviceId: string;
  serviceName: string;
  serviceCode: number;
  ruleType: string;
  programId: string | null;
  programName: string | null;
  itemId: string | null;
  quantity: number | null;
  unitValue: number | null;
  totalValue: number | null;
  poNumber: string | null;
  invoiceDescription: string | null;
  notes: string | null;
  status: string;
  billingId: string | null;
  // Extended fields from API
  itemBaseValue?: number | null;
  ruleBaseValue?: number | null;
  rulePercentage?: number | null;
  ranges?: ApiRange[] | null;
  version?: number | null;
  billingVersion?: number | null;
  rejectionReason?: string | null;
  billingMonth?: number | null;
  billingYear?: number | null;
  competenceMonth?: number | null;
  competenceYear?: number | null;
  programs?: ProgramInfo[] | null;
  requiresClientApproval: boolean;
}

export interface Client {
  id: string;
  name: string;
  code: number;
}

export interface ServiceRange {
  id: string;
  serviceId: string;
  valueFrom: number;
  valueTo: number;
  value: number;
  calculationType: string;
  order: number;
}

export interface ProgramInfo {
  uuid: string;
  name: string;
}

export interface ApiRange {
  uuid: string;
  range_from: number;
  range_to: number | null;
  last_range: boolean;
  range_type: string;
  value: number;
  created_at: string;
}

export interface BillingServiceRowResponse {
  service_rule_uuid: string;
  service_rule_name: string;
  service_rule_code: number;
  rule_type: string;
  percentage: number | null;
  base_value: number | null;
  item_base_value: number | null;
  programs: ProgramInfo[];
  program_uuid: string | null;
  item_uuid: string | null;
  quantity: number | null;
  unit_value: number | null;
  total_value: number | null;
  po_number: string | null;
  invoice_description: string | null;
  notes: string | null;
  billing_month: number | null;
  billing_year: number | null;
  competence_month: number | null;
  competence_year: number | null;
  item_version: number | null;
  ranges: ApiRange[] | null;
  status: string;
  billing_uuid: string | null;
  rejection_reason: string | null;
  billing_version: number | null;
  billing_total_value: number | null;
  requires_client_approval: boolean;
}

export interface BillingClientResponse {
  client_uuid: string;
  client_name: string;
  total_value: number;
  services: BillingServiceRowResponse[];
}

export interface StatusSummaryItem {
  status: string;
  count: number;
  total_value: number;
}

export interface BillingListPagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface BillingListResponse {
  data: BillingClientResponse[];
  pagination: BillingListPagination;
  status_summary: StatusSummaryItem[];
}

export interface BillingHistoryFieldChange {
  field: string;
  old: string | null;
  new: string | null;
}

export interface BillingHistoryChanges {
  item_uuid: string;
  item_label: string;
  fields: BillingHistoryFieldChange[];
}

export interface BillingHistoryEntry {
  uuid: string;
  previous_status: string | null;
  new_status: string;
  notes: string | null;
  changed_by: string | null;
  created_at: string;
  changes: BillingHistoryChanges | null;
}

export type BillingItemHistoryAction =
  | "lancamento_criado"
  | "lancamento_atualizado"
  | "lancamento_deletado"
  | "mudanca_status";

export interface BillingItemHistoryEntry {
  uuid: string;
  billing_item_uuid: string;
  action: BillingItemHistoryAction;
  previous_status: string | null;
  new_status: string;
  notes: string | null;
  changed_by: string | null;
  created_at: string;
  changes: BillingHistoryChanges | null;
}

export interface BillingAverageResponse {
  data: Record<string, number>;
}

export interface CreateBillingItemPayload {
  client_uuid: string;
  reference_year: number;
  reference_month: number;
  service_rule_uuid: string;
  billing_month: number;
  billing_year: number;
  competence_month?: number | null;
  competence_year?: number | null;
  program_uuid?: string | null;
  quantity?: number;
  unit_value?: number;
  total_value?: number;
  po_number?: string | null;
  invoice_description?: string | null;
  notes?: string | null;
}

export interface UpdateBillingItemPayload {
  version: number;
  quantity?: number | null;
  unit_value?: number | null;
  total_value?: number | null;
  po_number?: string | null;
  invoice_description?: string | null;
  notes?: string | null;
  billing_month?: number | null;
  billing_year?: number | null;
  competence_month?: number | null;
  competence_year?: number | null;
}

export interface ChangeBillingStatusPayload {
  new_status: string;
  rejection_reason?: string;
}

export interface BatchStatusPayload {
  item_uuids: string[];
  new_status: string;
  rejection_reason?: string | null;
}

export interface BatchStatusBilling {
  uuid: string;
  client_uuid: string;
  client_name: string;
  service_rule_uuid: string;
  service_rule_name: string;
  reference_year: number;
  reference_month: number;
  status: string;
  total_value: number;
  rejection_reason: string | null;
  items: unknown[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface BatchStatusResponse {
  success: boolean;
  data: {
    updated_count: number;
    billings: BatchStatusBilling[];
  };
  meta: {
    request_id: string;
  };
}

export interface ReplicateBillingItemPayload {
  client_uuid: string;
  reference_year: number;
  reference_month: number;
  service_rule_uuid: string;
  billing_month: number;
  billing_year: number;
  competence_month?: number | null;
  competence_year?: number | null;
  subsequent_months: number;
  program_uuid?: string | null;
  quantity?: number;
  unit_value?: number;
  total_value?: number;
  po_number?: string | null;
  invoice_description?: string | null;
  notes?: string | null;
}

const RULE_TYPE_MAP: Record<string, string> = {
  fixed_value: "valor_fixo",
  multiplication: "multiplicacao",
  variable_value: "valor_variavel",
  percentage: "percentual",
  range: "range",
};

function normalizeRuleType(apiType: string): string {
  return RULE_TYPE_MAP[apiType] ?? apiType;
}

export function apiServiceToRow(
  s: BillingServiceRowResponse,
  displayStatus: string,
): ServiceRow {
  return {
    serviceId: s.service_rule_uuid,
    serviceName: s.service_rule_name,
    serviceCode: s.service_rule_code,
    ruleType: normalizeRuleType(s.rule_type),
    programId: s.programs?.[0]?.uuid ?? null,
    programName: s.programs?.[0]?.name ?? null,
    itemId: s.item_uuid,
    quantity: s.quantity,
    unitValue: s.unit_value,
    totalValue: s.total_value,
    poNumber: s.po_number,
    invoiceDescription: s.invoice_description,
    notes: s.notes,
    status: displayStatus,
    billingId: s.billing_uuid,
    itemBaseValue: s.item_base_value,
    ruleBaseValue: s.base_value,
    rulePercentage: s.percentage,
    ranges: s.ranges,
    version: s.item_version,
    billingVersion: s.billing_version,
    rejectionReason: s.rejection_reason,
    billingMonth: s.billing_month,
    billingYear: s.billing_year,
    competenceMonth: s.competence_month,
    competenceYear: s.competence_year,
    programs: s.programs,
    requiresClientApproval: s.requires_client_approval ?? false,
  };
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function getRuleTypeLabel(ruleType: string) {
  const labels: Record<string, string> = {
    valor_fixo: "Valor Fixo",
    fixed_value: "Valor Fixo",
    multiplicacao: "Multiplicação",
    multiplication: "Multiplicação",
    range: "Range",
    valor_variavel: "Valor Variável",
    variable_value: "Valor Variável",
    percentual: "Percentual",
    percentage: "Percentual",
  };
  return labels[ruleType] || ruleType;
}
