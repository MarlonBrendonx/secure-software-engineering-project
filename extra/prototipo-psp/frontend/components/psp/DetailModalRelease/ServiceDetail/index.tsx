import { Badge } from "@/components/ui/badge";
import TruncatedText from "@/components/ui/truncated-text";
import { getStatusBadge } from "../../Common/StatusBadge";
import type { ServiceRow } from "../../types";
import { getRuleTypeLabel } from "../../types";

type ServiceDetailProps = {
  row: ServiceRow;
  clientName: string;
};

const ServiceDetail = ({ row, clientName }: ServiceDetailProps) => {
  const TooltipPrograms = () => {
    if (!row?.programs?.length) return row.programName || "";

    if (row?.programs?.length === 1) return row.programs[0].name;

    const display = `${row.programs[0].name}, ...`;
    const fullPrograms = row.programs.map((p) => p.name).join(", ");

    return <TruncatedText content={fullPrograms}>{display}</TruncatedText>;
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <p className="text-xs text-muted-foreground">Cliente</p>
        <p className="font-medium text-sm">{clientName}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Status</p>
        {getStatusBadge(row.status)}
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Programa</p>
        <TooltipPrograms />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Serviço</p>
        <p className="font-medium text-sm">{row.serviceName}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Tipo Regra</p>
        <Badge variant="outline">{getRuleTypeLabel(row.ruleType)}</Badge>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Código</p>
        <p className="font-medium text-sm">{row.serviceCode}</p>
      </div>
    </div>
  );
};

export default ServiceDetail;
