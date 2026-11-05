// Regressão: serviço sem programa derrubava a tela com "This page couldn't load".
// A linha lia `programs[0].name` sem checar a lista vazia. Regras cadastradas na tela
// de Serviços e Regras podem não ter programa, então a tabela precisa aguentar isso.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TableRelease from "@/components/psp/TableRelease";
import { apiServiceToRow } from "@/components/psp/types";
import { apiStatusToLabel } from "@/utils/psp/statusMap";

vi.mock("@/hooks/use-user-role", () => ({
  useUserRole: () => ({
    role: "analyst",
    canManageServiceRules: false,
    billing: { canSendToApproval: true, canApproveOrReject: false },
  }),
}));

// Formato real de um serviço sem lançamento e sem programa (resposta de GET /v1/billing).
const serviceWithoutProgram = {
  service_rule_uuid: "7ead37e7-0ff7-5a54-8a3a-cc14f83bd379",
  service_rule_name: "Taxa de Administração",
  service_rule_code: 201,
  rule_type: "fixed_value",
  percentage: null,
  base_value: null,
  item_base_value: null,
  programs: [],
  item_uuid: null,
  quantity: null,
  unit_value: null,
  total_value: null,
  po_number: null,
  invoice_description: null,
  notes: null,
  billing_month: null,
  billing_year: null,
  competence_month: null,
  competence_year: null,
  item_version: null,
  ranges: [],
  status: "NoEntry",
  billing_uuid: null,
  rejection_reason: null,
  billing_version: null,
  billing_total_value: null,
  requires_client_approval: false,
};

function renderTable() {
  // Mesmo caminho do app: o status da API vira o rótulo de exibição antes de montar a linha.
  const status = apiStatusToLabel(serviceWithoutProgram.status);
  const row = apiServiceToRow(
    { ...serviceWithoutProgram, status } as never,
    status,
  );
  const mutation = { mutateAsync: vi.fn(), mutate: vi.fn(), isPending: false };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TableRelease
        rows={[row]}
        clientId="79e6fdfa-f4ba-584c-b712-a0483f6bf85c"
        clientName="Farmácias Beta"
        statusFilter="todos"
        selectedYear={2026}
        selectedMonth={11}
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onUpdate={vi.fn()}
        mediaMap={new Map()}
        mutations={
          {
            createItem: mutation,
            updateItem: mutation,
            deleteItem: mutation,
            batchStatus: mutation,
            replicateItems: mutation,
          } as never
        }
      />
    </QueryClientProvider>,
  );
}

describe("tabela de lançamentos com serviço sem programa", () => {
  it("renderiza a linha e agrupa sob um rótulo, sem cabeçalho vazio", () => {
    renderTable();

    expect(screen.getAllByText("Taxa de Administração").length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("Sem programa").length).toBeGreaterThan(0);
  });

  it("abre o modal de lançamento", () => {
    renderTable();

    fireEvent.click(screen.getAllByTitle("Lançar")[0]);

    expect(screen.getByText("Novo Lançamento")).toBeTruthy();
  });

  it("abre o modal de detalhe", () => {
    renderTable();

    fireEvent.click(screen.getAllByTitle("Detalhar")[0]);

    expect(screen.getByText("Detalhes do Lançamento")).toBeTruthy();
  });
});
