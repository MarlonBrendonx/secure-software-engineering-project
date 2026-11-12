import { formatMonthYear } from "@/utils/formatter";
import type { ServiceRow } from "../../types";

type AdditionalInformation = {
  row: ServiceRow;
};

const AdditionalInformation = ({ row }: AdditionalInformation) => {
  return (
    <div className="border-t pt-3">
      <h4 className="text-sm font-semibold mb-2">Informações Adicionais</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <p className="text-xs text-muted-foreground">Número da PO</p>
          <p className="text-sm">{row.poNumber || "—"}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Competência</p>
          <p className="text-sm">
            {formatMonthYear(row.competenceMonth, row.competenceYear)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">
            Período de Faturamento
          </p>
          <p className="text-sm">
            {formatMonthYear(row.billingMonth, row.billingYear)}
          </p>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs text-muted-foreground">Descrição da Nota</p>
          <p className="text-sm">{row.invoiceDescription || "—"}</p>
        </div>
        <div className="sm:col-span-2">
          <p className="text-xs text-muted-foreground">Observação</p>
          <p className="text-sm">{row.notes || "—"}</p>
        </div>
      </div>
    </div>
  );
};
export default AdditionalInformation;
