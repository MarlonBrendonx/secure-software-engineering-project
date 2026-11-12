import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useUserRole } from "@/hooks/use-user-role";
import { useBillingAverage } from "@/lib/billing/psp";
import { formatCurrency } from "@/utils/formatter";
import { labelToApiStatus } from "@/utils/psp/statusMap";
import { StatusButtons } from "../StatusButtons";
import type { StatusFilter } from "../Summary";
import TableRelease from "../TableRelease";
import type {
  BatchStatusPayload,
  BillingClientResponse,
  ChangeBillingStatusPayload,
  CreateBillingItemPayload,
  ReplicateBillingItemPayload,
  ServiceRow,
  UpdateBillingItemPayload,
} from "../types";
import { apiServiceToRow } from "../types";

export interface PspMutations {
  createItem: {
    mutateAsync: (data: CreateBillingItemPayload) => Promise<unknown>;
  };
  updateItem: {
    mutateAsync: (args: {
      uuid: string;
      data: UpdateBillingItemPayload;
    }) => Promise<unknown>;
  };
  deleteItem: { mutateAsync: (uuid: string) => Promise<unknown> };
  replicateItems: {
    mutateAsync: (data: ReplicateBillingItemPayload) => Promise<unknown>;
  };
  changeStatus: {
    mutateAsync: (args: {
      itemUuid: string;
      data: ChangeBillingStatusPayload;
    }) => Promise<unknown>;
  };
  batchStatus: {
    mutateAsync: (data: BatchStatusPayload) => Promise<unknown>;
  };
}

interface ClientAccordionProps {
  clients: BillingClientResponse[];
  selectedYear: number;
  selectedMonth: number;
  statusFilter: StatusFilter;
  expandedClients: string[];
  setExpandedClients: (value: string[]) => void;
  selectedItemsByClient: Record<string, string[]>;
  setSelectedItemsByClient: React.Dispatch<
    React.SetStateAction<Record<string, string[]>>
  >;
  onRefetch: () => void;
  mutations: PspMutations;
}

function buildRows(client: BillingClientResponse): ServiceRow[] {
  return client.services
    .map((s) => apiServiceToRow(s, s.status))
    .sort((a, b) => a.serviceCode - b.serviceCode);
}

interface ClientItemProps {
  client: BillingClientResponse;
  isExpanded: boolean;
  selectedYear: number;
  selectedMonth: number;
  statusFilter: StatusFilter;
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onRefetch: () => void;
  mutations: PspMutations;
}

function ClientAccordionItem({
  client,
  isExpanded,
  selectedYear,
  selectedMonth,
  statusFilter,
  selectedIds,
  onSelectionChange,
  onRefetch,
  mutations,
}: ClientItemProps) {
  const queryClient = useQueryClient();
  const {
    billing: { canSendToApproval, canApproveOrReject },
  } = useUserRole();
  const { averageMap } = useBillingAverage(
    isExpanded ? client.client_uuid : null,
    selectedYear,
    selectedMonth,
  );

  const mediaMap = useMemo(() => {
    const map = new Map<string, number>();
    averageMap.forEach((val, key) => {
      map.set(`${client.client_uuid}:${key}`, val);
    });
    return map;
  }, [averageMap, client.client_uuid]);

  const allRows = useMemo(() => buildRows(client), [client]);

  const rows = useMemo(() => {
    if (statusFilter === "todos") return allRows;
    return allRows.filter((r) => r.status === statusFilter);
  }, [allRows, statusFilter]);

  const itemCount = rows.filter((r) => r.itemId !== null).length;
  const filteredTotal = useMemo(
    () => rows.reduce((sum, r) => sum + (r.totalValue ?? 0), 0),
    [rows],
  );

  const mutatingRef = useRef(false);

  const handleChangeStatus = async (
    newStatus: string,
    _statusLabel: string,
    motivo?: string,
    filterItemIds?: string[],
  ) => {
    if (mutatingRef.current) return;

    const idsToUse = filterItemIds ?? selectedIds;
    const itemUuids = new Set<string>();
    for (const row of rows) {
      if (row.itemId && idsToUse.includes(row.itemId)) {
        itemUuids.add(row.itemId);
      }
    }

    const uuids = Array.from(itemUuids);
    if (uuids.length === 0) return;

    mutatingRef.current = true;

    try {
      await mutations.batchStatus.mutateAsync({
        item_uuids: uuids,
        new_status: labelToApiStatus(newStatus),
        ...(motivo ? { rejection_reason: motivo } : {}),
      });

      // Wait for cache to reflect committed data before re-enabling UI
      await queryClient.invalidateQueries({ queryKey: ["billings"] });

      onSelectionChange([]);
    } catch {
      // Error toast handled globally by MutationCache
    } finally {
      mutatingRef.current = false;
    }
  };

  const tableProps = {
    clientId: client.client_uuid,
    clientName: client.client_name,
    statusFilter,
    selectedYear,
    selectedMonth,
    selectedIds,
    onSelectionChange,
    onUpdate: onRefetch,
    mediaMap,
    mutations,
  };

  return (
    <AccordionItem
      value={client.client_uuid}
      className="border rounded-lg mb-3"
    >
      <AccordionTrigger className="hover:no-underline px-3 sm:px-4 py-3 sm:py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between w-full pr-4 gap-1 sm:gap-3">
          <div className="flex flex-col sm:flex-row sm:items-center gap-0.5 sm:gap-3 min-w-0">
            <span className="font-semibold text-sm sm:text-base truncate text-left">
              {client.client_name}
            </span>
            <span className="self-start text-[11px] sm:text-xs text-muted-foreground">
              ({itemCount} lançamento{itemCount !== 1 ? "s" : ""} /{" "}
              {rows.length} serviço{rows.length !== 1 ? "s" : ""})
            </span>
          </div>
          <span className="text-sm sm:text-lg font-bold text-left sm:text-right shrink-0">
            {formatCurrency(
              statusFilter !== "todos" ? filteredTotal : client.total_value,
            )}
          </span>
        </div>
      </AccordionTrigger>
      <AccordionContent className="px-2 sm:px-4 pb-3 sm:pb-4 space-y-4">
        <div className="overflow-x-auto">
          <TableRelease rows={rows} {...tableProps} />
        </div>
        {statusFilter !== "todos" && (
          <StatusButtons
            currentStatus={statusFilter}
            selectedItemIds={selectedIds}
            selectedRows={rows}
            canSendToApproval={canSendToApproval}
            canApproveOrReject={canApproveOrReject}
            onChangeStatus={handleChangeStatus}
          />
        )}
      </AccordionContent>
    </AccordionItem>
  );
}

const ClientAccordion = ({
  clients,
  statusFilter,
  expandedClients,
  setExpandedClients,
  selectedItemsByClient,
  setSelectedItemsByClient,
  selectedYear,
  selectedMonth,
  onRefetch,
  mutations,
}: ClientAccordionProps) => {
  const filteredClients = useMemo(() => {
    return clients.filter((client) => {
      if (statusFilter === "todos") return true;
      return client.services.some((s) => s.status === statusFilter);
    });
  }, [clients, statusFilter]);

  return (
    <Accordion
      type="multiple"
      value={expandedClients}
      onValueChange={setExpandedClients}
      className="w-full cursor-pointer"
    >
      {filteredClients.map((client) => (
        <ClientAccordionItem
          key={client.client_uuid}
          client={client}
          isExpanded={expandedClients.includes(client.client_uuid)}
          selectedYear={selectedYear}
          selectedMonth={selectedMonth}
          statusFilter={statusFilter}
          selectedIds={selectedItemsByClient[client.client_uuid] || []}
          onSelectionChange={(ids) =>
            setSelectedItemsByClient((prev) => ({
              ...prev,
              [client.client_uuid]: ids,
            }))
          }
          onRefetch={onRefetch}
          mutations={mutations}
        />
      ))}
    </Accordion>
  );
};

export default ClientAccordion;
