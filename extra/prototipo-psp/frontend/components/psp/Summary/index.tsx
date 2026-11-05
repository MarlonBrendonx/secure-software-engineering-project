import {
  Building2,
  CheckCircle2,
  Clock,
  DollarSign,
  Eye,
  FileX,
  UserCheck,
  XCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAnimatedNumber } from "@/hooks/use-animated-number";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/utils/formatter";

import { DisplayStatus } from "@/utils/psp/statusMap";

export type StatusFilter = "todos" | DisplayStatus;

interface SummaryProps {
  totalAmount: number;
  noEntryCount: number;
  noEntryAmount: number;
  newCount: number;
  newAmount: number;
  rejectedCount: number;
  rejectedAmount: number;
  managementApprovalCount: number;
  managementApprovalAmount: number;
  clientApprovalCount: number;
  clientApprovalAmount: number;
  financialReviewCount: number;
  financialReviewAmount: number;
  approvedCount: number;
  approvedAmount: number;
  activeFilter: StatusFilter;
  onFilterChange: (filter: StatusFilter) => void;
}

const Summary = ({
  totalAmount,
  noEntryCount,
  noEntryAmount,
  newCount,
  newAmount,
  rejectedCount,
  rejectedAmount,
  managementApprovalCount,
  managementApprovalAmount,
  clientApprovalCount,
  clientApprovalAmount,
  financialReviewCount,
  financialReviewAmount,
  approvedCount,
  approvedAmount,
  activeFilter,
  onFilterChange,
}: SummaryProps) => {
  const summaryItems: {
    label: string;
    rawAmount: number;
    count: number;
    icon: typeof DollarSign;
    color: string;
    bgColor: string;
    filterKey: StatusFilter;
    isTotal?: boolean;
  }[] = [
    {
      label: "Valor Total",
      rawAmount: totalAmount,
      count:
        noEntryCount +
        newCount +
        rejectedCount +
        managementApprovalCount +
        clientApprovalCount +
        financialReviewCount +
        approvedCount,
      icon: DollarSign,
      color: "text-primary",
      bgColor: "bg-primary/10",
      filterKey: "todos",
      isTotal: true,
    },
    {
      label: "Sem Lançamento",
      rawAmount: noEntryAmount,
      count: noEntryCount,
      icon: FileX,
      color: "text-badge-arq-fg",
      bgColor: "bg-badge-arq",
      filterKey: DisplayStatus.SemLancamento,
    },
    {
      label: "Reprovados",
      rawAmount: rejectedAmount,
      count: rejectedCount,
      icon: XCircle,
      color: "text-badge-pend-fg",
      bgColor: "bg-badge-pend",
      filterKey: DisplayStatus.Reprovado,
    },
    {
      label: "Novos",
      rawAmount: newAmount,
      count: newCount,
      icon: Clock,
      color: "text-badge-fin-fg",
      bgColor: "bg-badge-fin",
      filterKey: DisplayStatus.Novo,
    },
    {
      label: "Aprovação Gestão",
      rawAmount: managementApprovalAmount,
      count: managementApprovalCount,
      icon: Eye,
      color: "text-badge-rasc-fg",
      bgColor: "bg-badge-rasc",
      filterKey: DisplayStatus.AprovacaoGestao,
    },
    {
      label: "Aprovação Cliente",
      rawAmount: clientApprovalAmount,
      count: clientApprovalCount,
      icon: UserCheck,
      color: "text-badge-cliente-fg",
      bgColor: "bg-badge-cliente",
      filterKey: DisplayStatus.AprovacaoCliente,
    },
    {
      label: "Rev. Financeira",
      rawAmount: financialReviewAmount,
      count: financialReviewCount,
      icon: Building2,
      color: "text-badge-ativo-fg",
      bgColor: "bg-badge-ativo",
      filterKey: DisplayStatus.RevisaoFinanceira,
    },
    {
      label: "Aprovados",
      rawAmount: approvedAmount,
      count: approvedCount,
      icon: CheckCircle2,
      color: "text-badge-pub-fg",
      bgColor: "bg-badge-pub",
      filterKey: DisplayStatus.Aprovado,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8 gap-2 sm:gap-3">
      {summaryItems.map((item) => (
        <SummaryCard
          key={item.label}
          item={item}
          isActive={activeFilter === item.filterKey}
          onClick={() => onFilterChange(item.filterKey)}
        />
      ))}
    </div>
  );
};

function SummaryCard({
  item,
  isActive,
  onClick,
}: {
  item: {
    label: string;
    rawAmount: number;
    count: number;
    icon: typeof DollarSign;
    color: string;
    bgColor: string;
  };
  isActive: boolean;
  onClick: () => void;
}) {
  const animatedAmount = useAnimatedNumber(item.rawAmount);
  const formattedAmount = formatCurrency(animatedAmount);

  return (
    <Card
      className={cn(
        "border shadow-sm cursor-pointer transition-all hover:shadow-md",
        isActive && "ring-2 ring-primary ring-offset-1",
      )}
      onClick={onClick}
    >
      <CardContent className="p-2 sm:p-3">
        <div className="flex flex-col gap-1.5 sm:gap-2">
          <div className="flex items-center justify-between">
            <div
              className={`h-7 w-7 sm:h-8 sm:w-8 rounded-lg ${item.bgColor} flex items-center justify-center shrink-0`}
            >
              <item.icon
                className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${item.color}`}
              />
            </div>
            <span className="text-[10px] sm:text-xs text-muted-foreground">
              {item.count} reg.
            </span>
          </div>
          <div className="min-w-0">
            <p
              className="text-[10px] sm:text-xs text-muted-foreground truncate"
              title={item.label}
            >
              {item.label}
            </p>
            <p
              className={`text-xs sm:text-sm font-bold ${item.color} truncate tabular-nums`}
              title={formattedAmount}
            >
              {formattedAmount}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default Summary;
