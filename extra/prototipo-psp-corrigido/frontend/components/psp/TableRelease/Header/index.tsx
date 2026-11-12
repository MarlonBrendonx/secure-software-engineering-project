import { Checkbox } from "@/components/ui/checkbox";
import { TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ServiceRow } from "../../types";

type HeaderProps = {
  itemRows: ServiceRow[];
  isEditable: boolean;
  allSelected: boolean;
  someSelected: boolean;
  handleSelectAll: (value: boolean) => void;
};

const Header = ({
  itemRows,
  isEditable,
  allSelected,
  someSelected,
  handleSelectAll,
}: HeaderProps) => {
  return (
    <TableHeader>
      <TableRow className="hover:bg-transparent">
        {isEditable && (
          <TableHead className="w-[40px]">
            <Checkbox
              checked={allSelected}
              onCheckedChange={handleSelectAll}
              aria-label="Selecionar todos"
              className={
                someSelected ? "data-[state=checked]:bg-primary/50" : ""
              }
              disabled={itemRows.length === 0}
            />
          </TableHead>
        )}
        <TableHead className="w-[13%]">Programa</TableHead>
        <TableHead className="w-[13%]">Serviço</TableHead>
        <TableHead className="w-[10%] text-right">Total</TableHead>
        <TableHead className="w-[12%] text-right">Média 3m</TableHead>
        <TableHead className="w-[10%]">Nº PO</TableHead>
        <TableHead className="w-[17%]">Descrição Nota</TableHead>
        <TableHead className="w-[auto]">Status</TableHead>
        <TableHead className="w-[auto]">Ações</TableHead>
      </TableRow>
    </TableHeader>
  );
};

export default Header;
