import { CheckCircle, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { DisplayStatus } from "@/utils/psp/statusMap";
import type { ServiceRow } from "../types";
import { FinancialApprovalModal } from "./FinancialApprovalModal";
import { ManagementApprovalModal } from "./ManagementApprovalModal";
import { MixedApprovalModal } from "./MixedApprovalModal";
import { RejectionModal } from "./RejectionModal";
import { ResendApprovalModal } from "./ResendApprovalModal";
import { SendToManagementModal } from "./SendToManagementModal";

interface StatusButtonsProps {
  currentStatus: string;
  selectedItemIds: string[];
  selectedRows: ServiceRow[];
  canSendToApproval: boolean;
  canApproveOrReject: boolean;
  onChangeStatus: (
    newStatus: string,
    statusLabel: string,
    motivo?: string,
    filterItemIds?: string[],
  ) => Promise<void>;
}

export function StatusButtons({
  currentStatus,
  selectedItemIds,
  selectedRows,
  canSendToApproval,
  canApproveOrReject,
  onChangeStatus,
}: StatusButtonsProps) {
  const [updatingAction, setUpdatingAction] = useState<string | null>(null);
  const [mixedApprovalOpen, setMixedApprovalOpen] = useState(false);

  const updating = updatingAction !== null;
  const hasSelection = selectedItemIds.length > 0;
  const selectedCount = selectedItemIds.length;

  const selectedServiceRows = useMemo(
    () =>
      selectedRows.filter(
        (r) => r.itemId && selectedItemIds.includes(r.itemId),
      ),
    [selectedRows, selectedItemIds],
  );

  const { withClientApproval, withoutClientApproval } = useMemo(() => {
    const withCA: ServiceRow[] = [];
    const withoutCA: ServiceRow[] = [];
    for (const row of selectedServiceRows) {
      if (row.requiresClientApproval) {
        withCA.push(row);
        continue;
      }
      withoutCA.push(row);
    }
    return { withClientApproval: withCA, withoutClientApproval: withoutCA };
  }, [selectedServiceRows]);

  const isMixedApproval =
    withClientApproval.length > 0 && withoutClientApproval.length > 0;

  const handleChangeStatus = async (
    action: string,
    newStatus: string,
    statusLabel: string,
    motivo?: string,
  ) => {
    setUpdatingAction(action);
    try {
      await onChangeStatus(newStatus, statusLabel, motivo);
    } finally {
      setUpdatingAction(null);
    }
  };

  const handleApprove = async () => {
    if (isMixedApproval) {
      setMixedApprovalOpen(true);
      return;
    }

    if (withClientApproval.length > 0) {
      await handleChangeStatus(
        "approve",
        DisplayStatus.AprovacaoCliente,
        "Aprovação do Cliente",
      );
    } else {
      await handleChangeStatus(
        "approve",
        DisplayStatus.RevisaoFinanceira,
        "Revisão Financeira",
      );
    }
  };

  const handleMixedApproveConfirm = async () => {
    setUpdatingAction("approve");
    try {
      const clientApprovalIds = withClientApproval
        .map((r) => r.itemId)
        .filter(Boolean) as string[];
      const financialReviewIds = withoutClientApproval
        .map((r) => r.itemId)
        .filter(Boolean) as string[];

      if (clientApprovalIds.length > 0) {
        await onChangeStatus(
          DisplayStatus.AprovacaoCliente,
          "Aprovação do Cliente",
          undefined,
          clientApprovalIds,
        );
      }
      if (financialReviewIds.length > 0) {
        await onChangeStatus(
          DisplayStatus.RevisaoFinanceira,
          "Revisão Financeira",
          undefined,
          financialReviewIds,
        );
      }
    } finally {
      setUpdatingAction(null);
      setMixedApprovalOpen(false);
    }
  };

  const sharedProps = { updating, updatingAction, hasSelection, selectedCount };

  const renderButtons = () => {
    // Novo → ManagementApproval (admin, analyst)
    if (currentStatus === DisplayStatus.Novo && canSendToApproval) {
      return (
        <SendToManagementModal
          {...sharedProps}
          onConfirm={() =>
            handleChangeStatus(
              "send",
              DisplayStatus.AprovacaoGestao,
              "Aprovação da Gestão",
            )
          }
        />
      );
    }

    // ManagementApproval → approve/reject (admin, manager)
    if (currentStatus === DisplayStatus.AprovacaoGestao && canApproveOrReject) {
      return (
        <>
          <RejectionModal
            {...sharedProps}
            onReject={(motivo) =>
              handleChangeStatus(
                "reject",
                DisplayStatus.Reprovado,
                DisplayStatus.Reprovado,
                motivo,
              )
            }
          />
          {isMixedApproval ? (
            <>
              <MixedApprovalModal
                open={mixedApprovalOpen}
                onOpenChange={setMixedApprovalOpen}
                updating={updating}
                updatingAction={updatingAction}
                withClientApproval={withClientApproval}
                withoutClientApproval={withoutClientApproval}
                onConfirm={handleMixedApproveConfirm}
              />
              <Button
                variant="default"
                className="gap-2"
                disabled={updating || !hasSelection}
                onClick={() => setMixedApprovalOpen(true)}
              >
                {updatingAction === "approve" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Aprovar lançamento
              </Button>
            </>
          ) : (
            <ManagementApprovalModal
              {...sharedProps}
              isMixedApproval={false}
              hasClientApprovalItems={withClientApproval.length > 0}
              onConfirm={handleApprove}
            />
          )}
        </>
      );
    }
    if (
      currentStatus === DisplayStatus.RevisaoFinanceira &&
      canApproveOrReject
    ) {
      return (
        <FinancialApprovalModal
          {...sharedProps}
          onConfirm={() =>
            handleChangeStatus(
              "approve",
              DisplayStatus.Aprovado,
              DisplayStatus.Aprovado,
            )
          }
        />
      );
    }

    // Rejected → ManagementApproval (admin, analyst)
    if (currentStatus === DisplayStatus.Reprovado && canSendToApproval) {
      return (
        <ResendApprovalModal
          {...sharedProps}
          onConfirm={() =>
            handleChangeStatus(
              "resend",
              DisplayStatus.AprovacaoGestao,
              "Aprovação da Gestão",
            )
          }
        />
      );
    }

    return null;
  };

  const buttons = renderButtons();
  if (!buttons) return null;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-4 border-t">
      <span className="text-xs sm:text-sm text-muted-foreground">
        {hasSelection
          ? `${selectedCount} selecionado(s)`
          : "Selecione lançamentos para enviar"}
      </span>
      <div className="hidden sm:block flex-1" />
      <div className="flex flex-wrap items-center gap-2">{buttons}</div>
    </div>
  );
}
