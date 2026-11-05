import { useEffect, useMemo, useState } from "react";
import type { StatusFilter } from "@/components/psp/Summary";
import { useDebounce } from "@/hooks/use-debounce";
import {
  useBatchBillingStatus,
  useBillings,
  useChangeBillingStatus,
  useCreateBillingItem,
  useDeleteBillingItem,
  useReplicateBillingItems,
  useUpdateBillingItem,
} from "@/lib/billing/psp";
import { DisplayStatus } from "@/utils/psp/statusMap";

export function usePspManager() {
  const [selectedYear, setSelectedYear] = useState<number | null>(() =>
    new Date().getFullYear(),
  );
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const debouncedSearch = useDebounce(searchTerm, 300);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("todos");
  const [page, setPage] = useState(1);

  const [expandedClients, setExpandedClients] = useState<string[]>([]);
  const [selectedItemsByClient, setSelectedItemsByClient] = useState<
    Record<string, string[]>
  >({});

  // Reset page when filters change
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset page on filter change
  useEffect(() => {
    setPage(1);
    setExpandedClients([]);
    setSelectedItemsByClient({});
  }, [selectedYear, selectedMonth, debouncedSearch]);

  const { clients, statusSummary, pagination, isLoading, isError, refetch } =
    useBillings(
      selectedYear,
      selectedMonth,
      page,
      debouncedSearch || undefined,
    );

  const createItem = useCreateBillingItem();
  const updateItem = useUpdateBillingItem();
  const deleteItem = useDeleteBillingItem();
  const replicateItems = useReplicateBillingItems();
  const changeStatus = useChangeBillingStatus();
  const batchStatus = useBatchBillingStatus();

  const summaryProps = useMemo(() => {
    const find = (displayStatus: string) =>
      statusSummary.find((s) => s.status === displayStatus) ?? {
        count: 0,
        total_value: 0,
      };

    const noEntry = find(DisplayStatus.SemLancamento);
    const newEntry = find(DisplayStatus.Novo);
    const rejected = find(DisplayStatus.Reprovado);
    const management = find(DisplayStatus.AprovacaoGestao);
    const client = find(DisplayStatus.AprovacaoCliente);
    const financial = find(DisplayStatus.RevisaoFinanceira);
    const approved = find(DisplayStatus.Aprovado);

    const totalAmount =
      noEntry.total_value +
      newEntry.total_value +
      rejected.total_value +
      management.total_value +
      client.total_value +
      financial.total_value +
      approved.total_value;

    return {
      totalAmount,
      noEntryCount: noEntry.count,
      noEntryAmount: noEntry.total_value,
      newCount: newEntry.count,
      newAmount: newEntry.total_value,
      rejectedCount: rejected.count,
      rejectedAmount: rejected.total_value,
      managementApprovalCount: management.count,
      managementApprovalAmount: management.total_value,
      clientApprovalCount: client.count,
      clientApprovalAmount: client.total_value,
      financialReviewCount: financial.count,
      financialReviewAmount: financial.total_value,
      approvedCount: approved.count,
      approvedAmount: approved.total_value,
      activeFilter: statusFilter,
      onFilterChange: setStatusFilter,
    };
  }, [statusSummary, statusFilter]);

  return {
    filterProps: {
      selectedYear,
      onYearChange: setSelectedYear,
      selectedMonth,
      onMonthChange: setSelectedMonth,
    },

    searchProps: {
      searchTerm,
      onSearchChange: setSearchTerm,
    },

    summaryProps,

    accordionProps: {
      clients,
      selectedYear: selectedYear!,
      selectedMonth: selectedMonth!,
      statusFilter,
      expandedClients,
      setExpandedClients,
      selectedItemsByClient,
      setSelectedItemsByClient,
      onRefetch: refetch,
      mutations: {
        createItem,
        updateItem,
        deleteItem,
        replicateItems,
        changeStatus,
        batchStatus,
      },
    },

    paginationProps: {
      pagination,
      page,
      onPageChange: setPage,
    },

    isLoading,
    isError,
  };
}
