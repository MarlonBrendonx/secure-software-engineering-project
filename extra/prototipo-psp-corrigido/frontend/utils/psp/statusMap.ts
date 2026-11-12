export enum ApiStatus {
  New = "New",
  ManagementApproval = "ManagementApproval",
  ClientApproval = "ClientApproval",
  FinancialReview = "FinancialReview",
  Approved = "Approved",
  Rejected = "Rejected",
  NoEntry = "NoEntry",
}

export enum DisplayStatus {
  Novo = "Novo",
  AprovacaoGestao = "Aprovação (Gestão)",
  AprovacaoCliente = "Aprovação (Cliente)",
  RevisaoFinanceira = "Revisão financeira",
  Aprovado = "Aprovado",
  Reprovado = "Reprovado",
  SemLancamento = "Sem lançamento",
}

const API_TO_DISPLAY: Record<ApiStatus, DisplayStatus> = {
  [ApiStatus.New]: DisplayStatus.Novo,
  [ApiStatus.ManagementApproval]: DisplayStatus.AprovacaoGestao,
  [ApiStatus.ClientApproval]: DisplayStatus.AprovacaoCliente,
  [ApiStatus.FinancialReview]: DisplayStatus.RevisaoFinanceira,
  [ApiStatus.Approved]: DisplayStatus.Aprovado,
  [ApiStatus.Rejected]: DisplayStatus.Reprovado,
  [ApiStatus.NoEntry]: DisplayStatus.SemLancamento,
};

const DISPLAY_TO_API: Record<DisplayStatus, ApiStatus> = {
  [DisplayStatus.Novo]: ApiStatus.New,
  [DisplayStatus.AprovacaoGestao]: ApiStatus.ManagementApproval,
  [DisplayStatus.AprovacaoCliente]: ApiStatus.ClientApproval,
  [DisplayStatus.RevisaoFinanceira]: ApiStatus.FinancialReview,
  [DisplayStatus.Aprovado]: ApiStatus.Approved,
  [DisplayStatus.Reprovado]: ApiStatus.Rejected,
  [DisplayStatus.SemLancamento]: ApiStatus.NoEntry,
};

export function apiStatusToLabel(apiStatus: string): string {
  return API_TO_DISPLAY[apiStatus as ApiStatus] ?? apiStatus;
}

export function labelToApiStatus(label: string): string {
  return DISPLAY_TO_API[label as DisplayStatus] ?? label;
}
