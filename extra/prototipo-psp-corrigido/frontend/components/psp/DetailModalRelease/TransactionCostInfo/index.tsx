import { formatCurrency } from "@/utils/formatter";
import type { ServiceRow } from "../../types";

type TransactionCostInfoProps = {
  row: ServiceRow;
};

const TransactionCostInfo = ({ row }: TransactionCostInfoProps) => {
  if (!row.itemId) return null;

  return (
    <div className="border-t pt-3">
      <h4 className="text-sm font-semibold mb-2">Valores</h4>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-xs text-muted-foreground">Quantidade</p>
          <p className="font-medium text-sm">{row.quantity || "—"}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Valor Unitário</p>
          <p className="font-medium text-sm">
            {row.unitValue ? formatCurrency(row.unitValue) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Valor Total</p>
          <p className="font-bold text-sm text-primary">
            {row.totalValue ? formatCurrency(row.totalValue) : "—"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default TransactionCostInfo;
