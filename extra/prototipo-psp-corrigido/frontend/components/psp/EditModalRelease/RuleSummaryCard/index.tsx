import { Badge } from "@/components/ui/badge";
import TruncatedText from "@/components/ui/truncated-text";
import { formatNumber, getRuleTypeLabel, type ServiceRow } from "../../types";

interface RuleSummaryCardProps {
  clientName: string;
  row: ServiceRow;
}

function getRuleBaseDescription(row: ServiceRow): string | null {
  switch (row.ruleType) {
    case "multiplicacao":
      return `Valor base: R$ ${formatNumber(row.ruleBaseValue ?? 0)} × Quantidade`;
    case "percentual":
      return `${formatNumber(row.rulePercentage ?? 0)}% sobre o Valor Base`;
    case "range":
      return null; // handled separately as a table
    default:
      return null;
  }
}

const RuleSummaryCard = ({ clientName, row }: RuleSummaryCardProps) => {
  return (
    <div className="grid grid-cols-2 gap-4 p-3 bg-muted/50 rounded-lg relative">
      <div>
        <p className="text-xs text-muted-foreground">Cliente</p>
        <p className="font-medium text-sm">{clientName}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Programa</p>
        {(() => {
          const programs = row.programs ?? [];
          if (programs.length === 0)
            return (
              <p className="font-medium text-sm">{row.programName || ""}</p>
            );
          if (programs.length === 1)
            return <p className="font-medium text-sm">{programs[0].name}</p>;
          const display = `${programs[0].name}, ...`;
          const full = programs.map((p) => p.name).join(", ");
          return (
            <TruncatedText
              as="p"
              className="font-medium text-sm"
              content={full}
            >
              {display}
            </TruncatedText>
          );
        })()}
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Serviço</p>
        <p className="font-medium text-sm">{row.serviceName}</p>
      </div>
      <div>
        <p className="text-xs text-muted-foreground">Tipo Regra</p>
        <Badge variant="outline">{getRuleTypeLabel(row.ruleType)}</Badge>
      </div>
      {getRuleBaseDescription(row) && (
        <div className="col-span-2">
          <p className="text-xs text-muted-foreground">Base de Cálculo</p>
          <p className="font-medium text-sm">{getRuleBaseDescription(row)}</p>
        </div>
      )}
      {row.ruleType === "range" && row.ranges && row.ranges.length > 0 && (
        <div className="col-span-2">
          <p className="text-xs text-muted-foreground mb-1">
            Base de Cálculo (Faixas)
          </p>
          <div className="border rounded-md overflow-hidden text-xs">
            <table className="w-full">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-2 py-1 font-medium">De</th>
                  <th className="text-left px-2 py-1 font-medium">Até</th>
                  <th className="text-left px-2 py-1 font-medium">Tipo</th>
                  <th className="text-right px-2 py-1 font-medium">
                    Valor (R$)
                  </th>
                </tr>
              </thead>
              <tbody>
                {row.ranges.map((r) => (
                  <tr key={r.uuid} className="border-t">
                    <td className="px-2 py-1">{formatNumber(r.range_from)}</td>
                    <td className="px-2 py-1">
                      {r.last_range ? "∞" : formatNumber(r.range_to ?? 0)}
                    </td>
                    <td className="px-2 py-1">
                      {r.range_type === "fixed_value"
                        ? "Valor Fixo"
                        : "Por Unidade"}
                    </td>
                    <td className="px-2 py-1 text-right">
                      {formatNumber(r.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default RuleSummaryCard;
