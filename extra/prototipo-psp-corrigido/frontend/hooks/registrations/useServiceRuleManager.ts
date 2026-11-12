import { useCallback, useState } from "react";
import { toast } from "sonner";
import {
  initialServiceRuleFormData,
  type ServiceRule,
  type ServiceRuleFormData,
} from "@/components/registrations/service-rules/types";
import { useDebounce } from "@/hooks/use-debounce";
import type { ClientSummary } from "@/lib/registrations/clients";
import { usePrograms } from "@/lib/registrations/programs";
import {
  type CreateServiceRulePayload,
  useCreateServiceRule,
  useDeleteServiceRule,
  useServiceRules,
  useUpdateServiceRule,
} from "@/lib/registrations/service-rules";

export function useServiceRuleManager(selectedClient: ClientSummary) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingVersion, setEditingVersion] = useState<number | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [serviceToDelete, setServiceToDelete] = useState<ServiceRule | null>(
    null,
  );
  const [formData, setFormData] = useState<ServiceRuleFormData>(
    initialServiceRuleFormData,
  );
  const [editingHasBillingItems, setEditingHasBillingItems] = useState(false);
  const [programNameFilter, setProgramNameFilter] = useState("");
  const debouncedProgramNameFilter = useDebounce(programNameFilter, 800);
  const [serviceNameFilter, setServiceNameFilter] = useState("");
  const debouncedServiceNameFilter = useDebounce(serviceNameFilter, 800);
  const [page, setPage] = useState(1);

  const {
    data: serviceRules,
    pagination,
    isLoading,
    isError,
    refetch,
  } = useServiceRules(
    selectedClient.uuid,
    debouncedProgramNameFilter || undefined,
    debouncedServiceNameFilter || undefined,
    page,
  );

  const { data: programs } = usePrograms(selectedClient.uuid);

  const createServiceRule = useCreateServiceRule();
  const updateServiceRule = useUpdateServiceRule();
  const deleteServiceRule = useDeleteServiceRule();

  const buildPayload = useCallback((): CreateServiceRulePayload => {
    const isRange = formData.rule_type === "range";
    const isPercentual = formData.rule_type === "percentage";
    const isMultiplication = formData.rule_type === "multiplication";

    return {
      name: formData.name.trim().substring(0, 100),
      status: formData.status,
      rule_type: formData.rule_type,
      percentage: isPercentual
        ? Number.parseFloat(formData.percentage) || null
        : null,
      base_value: isMultiplication
        ? Number.parseFloat(formData.base_value) || null
        : null,
      requires_client_approval: formData.requires_client_approval,
      ranges: isRange
        ? formData.ranges.map((r) => ({
            range_from: Number.parseInt(r.range_from, 10) || 0,
            range_to: r.last_range
              ? null
              : Number.parseInt(r.range_to, 10) || 0,
            range_type: r.range_type || "fixed_value",
            value: Number.parseFloat(r.value) || null,
            last_range: r.last_range,
          }))
        : undefined,
      programs: formData.selected_programs.map((p) => ({
        program_uuid: p.program_uuid,
      })),
    };
  }, [formData]);

  const closeAndReset = useCallback(() => {
    setIsDialogOpen(false);
    setEditingId(null);
    setEditingVersion(null);
    setFormData(initialServiceRuleFormData);
    setEditingHasBillingItems(false);
  }, []);

  const handleSave = useCallback(() => {
    const payload = buildPayload();

    const onSuccess = () => {
      closeAndReset();
      toast.success(
        editingId
          ? "Serviço atualizado com sucesso."
          : "Serviço cadastrado com sucesso.",
      );
    };

    if (editingId) {
      updateServiceRule.mutate(
        {
          serviceRuleUuid: editingId,
          clientUuid: selectedClient.uuid,
          data: payload,
          version: editingVersion as number,
        },
        { onSuccess },
      );
    } else {
      createServiceRule.mutate(
        { clientUuid: selectedClient.uuid, data: payload },
        { onSuccess },
      );
    }
  }, [
    buildPayload,
    closeAndReset,
    createServiceRule,
    updateServiceRule,
    editingId,
    editingVersion,
    selectedClient,
  ]);

  const handleEdit = useCallback((service: ServiceRule) => {
    setEditingHasBillingItems(service.has_billing_items);
    setFormData({
      name: service.name,
      status: service.status,
      rule_type: service.rule_type,
      percentage: service.percentage?.toString() ?? "",
      base_value: service.base_value?.toString() ?? "",
      requires_client_approval: service.requires_client_approval,
      ranges: (service.ranges ?? []).map((r) => ({
        id: crypto.randomUUID(),
        range_from: r.range_from?.toString() ?? "",
        range_to: r.range_to?.toString() ?? "",
        range_type: r.range_type ?? "",
        value: r.value?.toString() ?? "",
        last_range: r.last_range ?? false,
      })),
      selected_programs: (service.programs ?? []).map((p) => ({
        program_uuid: p.program_uuid,
      })),
    });
    setEditingId(service.uuid);
    setEditingVersion(service.version);
    setIsDialogOpen(true);
  }, []);

  const handleDelete = useCallback((service: ServiceRule) => {
    setServiceToDelete(service);
    setDeleteDialogOpen(true);
  }, []);

  const handleConfirmDelete = () => {
    if (!serviceToDelete) return;
    deleteServiceRule.mutate(
      {
        serviceRuleUuid: serviceToDelete.uuid,
        clientUuid: selectedClient.uuid,
      },
      {
        onSuccess: () => {
          setDeleteDialogOpen(false);
          setServiceToDelete(null);
          toast.success("Serviço excluído com sucesso.");
        },
      },
    );
  };

  const openNewServiceRuleDialog = useCallback(() => {
    setFormData(initialServiceRuleFormData);
    setEditingId(null);
    setEditingVersion(null);
    setEditingHasBillingItems(false);
    setIsDialogOpen(true);
  }, []);

  return {
    tabProps: {
      serviceRules,
      isLoading,
      isError,
      onRetry: refetch,
      onNewServiceRule: openNewServiceRuleDialog,
      onEdit: handleEdit,
      onDelete: handleDelete,
      programNameFilter,
      onProgramNameFilterChange: setProgramNameFilter,
      serviceNameFilter,
      onServiceNameFilterChange: setServiceNameFilter,
      paginationProps: { pagination, page, onPageChange: setPage },
    },

    modalProps: {
      isDialogOpen,
      editingId,
      formData,
      programs,
      hasBillingItems: editingHasBillingItems,
      handleSave,
      setFormData,
      setEditingId,
      setIsDialogOpen,
      loadingSave: createServiceRule.isPending || updateServiceRule.isPending,
    },

    deleteDialogProps: {
      open: deleteDialogOpen,
      onOpenChange: setDeleteDialogOpen,
      serviceName: serviceToDelete?.name ?? "",
      onConfirm: handleConfirmDelete,
      loading: deleteServiceRule.isPending,
    },
  };
}
