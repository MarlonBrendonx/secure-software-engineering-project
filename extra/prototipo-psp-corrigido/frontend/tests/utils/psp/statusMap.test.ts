import { describe, expect, it } from "vitest";
import {
  ApiStatus,
  apiStatusToLabel,
  DisplayStatus,
  labelToApiStatus,
} from "@/utils/psp/statusMap";

describe("apiStatusToLabel", () => {
  it.each([
    [ApiStatus.New, DisplayStatus.Novo],
    [ApiStatus.ManagementApproval, DisplayStatus.AprovacaoGestao],
    [ApiStatus.ClientApproval, DisplayStatus.AprovacaoCliente],
    [ApiStatus.FinancialReview, DisplayStatus.RevisaoFinanceira],
    [ApiStatus.Approved, DisplayStatus.Aprovado],
    [ApiStatus.Rejected, DisplayStatus.Reprovado],
    [ApiStatus.NoEntry, DisplayStatus.SemLancamento],
  ])("maps %s to %s", (api, display) => {
    expect(apiStatusToLabel(api)).toBe(display);
  });

  it("returns the input unchanged for an unknown status", () => {
    expect(apiStatusToLabel("SomethingElse")).toBe("SomethingElse");
    expect(apiStatusToLabel("")).toBe("");
  });
});

describe("labelToApiStatus", () => {
  it.each([
    [DisplayStatus.Novo, ApiStatus.New],
    [DisplayStatus.AprovacaoGestao, ApiStatus.ManagementApproval],
    [DisplayStatus.AprovacaoCliente, ApiStatus.ClientApproval],
    [DisplayStatus.RevisaoFinanceira, ApiStatus.FinancialReview],
    [DisplayStatus.Aprovado, ApiStatus.Approved],
    [DisplayStatus.Reprovado, ApiStatus.Rejected],
    [DisplayStatus.SemLancamento, ApiStatus.NoEntry],
  ])("maps %s back to %s", (display, api) => {
    expect(labelToApiStatus(display)).toBe(api);
  });

  it("returns the input unchanged for an unknown label", () => {
    expect(labelToApiStatus("Desconhecido")).toBe("Desconhecido");
  });
});

describe("round trip", () => {
  it("api -> label -> api is stable for every known status", () => {
    for (const api of Object.values(ApiStatus)) {
      expect(labelToApiStatus(apiStatusToLabel(api))).toBe(api);
    }
  });
});
