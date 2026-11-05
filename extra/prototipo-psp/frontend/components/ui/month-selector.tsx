import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MonthSelectorProps {
  months: { value: number; label: string }[];
  currentMonth: number;
  currentYear: number;
  selectedYear: number | null;
  selectedMonth: number | null;
  onMonthChange: (month: number) => void;
  blockFutureMonths?: boolean;
}

const MonthSelector = ({
  months,
  currentMonth,
  currentYear,
  selectedYear,
  selectedMonth,
  onMonthChange,
  blockFutureMonths = true,
}: MonthSelectorProps) => {
  return (
    <div className="flex flex-wrap gap-2">
      {months.map((month) => {
        const isCurrent =
          month.value === currentMonth && selectedYear === currentYear;
        const isSelected = month.value === selectedMonth;
        const isFuture =
          blockFutureMonths &&
          selectedYear !== null &&
          (selectedYear > currentYear ||
            (selectedYear === currentYear && month.value > currentMonth));

        return (
          <Button
            key={month.value}
            variant={isSelected ? "default" : "outline"}
            size="sm"
            disabled={isFuture}
            onClick={() => onMonthChange(month.value)}
            className={cn(
              "min-w-20 cursor-pointer text-xs",
              isFuture && "pointer-events-none opacity-50",
              isCurrent &&
                !isSelected &&
                !isFuture &&
                "ring-2 ring-ep-verde ring-offset-2 bg-ep-verde/10",
              isCurrent &&
                isSelected &&
                "bg-ep-verde text-ep-chumbo hover:bg-ep-verde/90",
            )}
          >
            {month.label.slice(0, 3)}
            {isCurrent && !isFuture && <span className="ml-1 text-xs">●</span>}
          </Button>
        );
      })}
    </div>
  );
};

export default MonthSelector;
