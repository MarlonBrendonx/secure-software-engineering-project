import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Table } from "@/components/ui/table";
import type { PspMutations } from "../Accordion";
import DetailModalRelease from "../DetailModalRelease";
import EditModalRelease from "../EditModalRelease";
import type { ServiceRow } from "../types";
import Body from "./Body";
import Header from "./Header";
import MobileCards from "./MobileCards";

interface ProgramGroup {
  key: string;
  label: string;
  itemCount: number;
  rows: ServiceRow[];
}

function groupRowsByProgram(rows: ServiceRow[]): ProgramGroup[] {
  const multiProgramRows: ServiceRow[] = [];
  const singleProgramMap = new Map<
    string,
    { name: string; rows: ServiceRow[] }
  >();

  for (const row of rows) {
    const programs = row.programs ?? [];
    if (programs.length > 1) {
      multiProgramRows.push(row);
    } else {
      const progId = programs[0]?.uuid ?? row.programId ?? "_none";
      const progName = programs[0]?.name ?? row.programName ?? "";
      if (!singleProgramMap.has(progId)) {
        singleProgramMap.set(progId, { name: progName, rows: [] });
      }
      singleProgramMap.get(progId)?.rows.push(row);
    }
  }

  const groups: ProgramGroup[] = [];

  if (multiProgramRows.length > 0) {
    groups.push({
      key: "_general",
      label: "Geral (múltiplos programas)",
      itemCount: multiProgramRows.filter((r) => r.itemId !== null).length,
      rows: multiProgramRows,
    });
  }

  for (const [progId, { name, rows: progRows }] of singleProgramMap) {
    groups.push({
      key: progId,
      label: name || "Sem programa",
      itemCount: progRows.filter((r) => r.itemId !== null).length,
      rows: progRows,
    });
  }

  return groups;
}

interface ReleaseTableProps {
  rows: ServiceRow[];
  clientId: string;
  clientName: string;
  statusFilter: string;
  selectedYear: number;
  selectedMonth: number;
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onUpdate: () => void;
  mediaMap: Map<string, number>;
  mutations?: PspMutations;
}

const TableRelease = ({
  rows,
  clientId,
  clientName,
  statusFilter,
  selectedYear,
  selectedMonth,
  selectedIds,
  onSelectionChange,
  onUpdate,
  mediaMap,
  mutations,
}: ReleaseTableProps) => {
  const [editRow, setEditRow] = useState<ServiceRow | null>(null);
  const [detailRow, setDetailRow] = useState<ServiceRow | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const isOverview = statusFilter === "todos";
  const isEditable = true;
  const canDelete = true;

  const groups = useMemo(() => groupRowsByProgram(rows), [rows]);

  const handleSelectItem = (itemId: string, checked: boolean) => {
    onSelectionChange(
      checked
        ? [...selectedIds, itemId]
        : selectedIds.filter((id) => id !== itemId),
    );
  };

  const handleDeleteContent = async (row: ServiceRow) => {
    if (!row.itemId) return;
    setActionLoading(row.itemId);
    try {
      await mutations?.deleteItem.mutateAsync(row.itemId);
      toast.success("Conteúdo do lançamento excluído.");
    } catch {
      // Error toast handled globally by MutationCache
    } finally {
      setActionLoading(null);
    }
  };

  const makeSharedProps = (groupRows: ServiceRow[]) => ({
    rows: groupRows,
    mediaMap,
    selectedIds,
    actionLoading,
    clientId,
    isEditable,
    isOverview,
    canDelete,
    handleSelectItem,
    handleDeleteContent,
    setEditRow,
    setDetailRow,
  });

  return (
    <>
      {/* Desktop */}
      <div className="hidden sm:block space-y-4">
        {groups.map((group) => {
          const groupItemRows = group.rows.filter((r) => r.itemId !== null);
          const groupAllSelected =
            groupItemRows.length > 0 &&
            groupItemRows.every((r) =>
              selectedIds.includes(r.itemId as string),
            );
          const groupSomeSelected =
            groupItemRows.some((r) =>
              selectedIds.includes(r.itemId as string),
            ) && !groupAllSelected;

          const handleGroupSelectAll = (checked: boolean) => {
            const groupItemIds = groupItemRows.map((r) => r.itemId as string);
            if (checked) {
              const merged = new Set([...selectedIds, ...groupItemIds]);
              onSelectionChange(Array.from(merged));
            } else {
              onSelectionChange(
                selectedIds.filter((id) => !groupItemIds.includes(id)),
              );
            }
          };

          return (
            <div key={group.key}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-muted-foreground">
                  {group.label !== "Geral (múltiplos programas)" ? (
                    <Badge variant="outline" className="text-[10px] h-7">
                      {group.label}
                    </Badge>
                  ) : (
                    group.label
                  )}
                </span>
              </div>
              <Table className="table-fixed w-full">
                <Header
                  itemRows={groupItemRows}
                  isEditable={isEditable}
                  allSelected={groupAllSelected}
                  someSelected={groupSomeSelected}
                  handleSelectAll={handleGroupSelectAll}
                />
                <Body {...makeSharedProps(group.rows)} />
              </Table>
            </div>
          );
        })}
      </div>

      {/* Mobile */}
      <div className="sm:hidden space-y-4">
        {groups.map((group) => (
          <div key={group.key}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-muted-foreground">
                {group.label}
              </span>
              <Badge variant="secondary" className="text-[10px]">
                {group.itemCount} lançamento
                {group.itemCount !== 1 ? "s" : ""}
              </Badge>
            </div>
            <MobileCards {...makeSharedProps(group.rows)} />
          </div>
        ))}
      </div>

      {editRow && (
        <EditModalRelease
          open={!!editRow}
          onOpenChange={(open: boolean) => {
            if (!open) {
              setEditRow(null);
            }
          }}
          row={editRow}
          clientId={clientId}
          clientName={clientName}
          selectedYear={selectedYear}
          selectedMonth={selectedMonth}
          onSuccess={onUpdate}
          mutations={mutations}
        />
      )}

      {detailRow && (
        <DetailModalRelease
          open={!!detailRow}
          onOpenChange={(open: boolean) => !open && setDetailRow(null)}
          row={detailRow}
          clientName={clientName}
        />
      )}
    </>
  );
};

export default TableRelease;
