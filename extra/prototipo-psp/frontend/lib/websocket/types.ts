export interface WSAuthMessage {
  type: "auth";
  token: string;
  channels?: string[];
}

export interface WSAuthOk {
  type: "auth_ok";
  sub: string;
}

export interface WSAuthError {
  type: "auth_error";
  reason: string;
}

export type WSControlMessage = WSAuthOk | WSAuthError;

export interface WSEventMessage<T = unknown> {
  channel: string;
  event: string;
  data: T;
  timestamp: string;
}

// O aviso é só de invalidação: o back não manda valores, o front busca de novo pela API.
export interface WSBillingChangedData {
  client_uuid: string;
}

export const WS_CLOSE_CODES = {
  AUTH_TIMEOUT: 4001,
  TOKEN_EXPIRED: 4003,
  NORMAL: 1000,
} as const;
