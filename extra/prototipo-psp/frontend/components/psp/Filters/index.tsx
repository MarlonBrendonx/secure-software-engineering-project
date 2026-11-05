import MonthSelector from "@/components/ui/month-selector";
import YearSelector, { getPspYears } from "@/components/ui/year-selector";
import { MONTHS_FULL } from "@/utils/constants";

export interface FiltersProps {
  selectedYear: number | null;
  onYearChange: (year: number) => void;
  selectedMonth: number | null;
  onMonthChange: (month: number) => void;
}

const now = new Date();
const currentMonth = now.getMonth() + 1;
const currentYear = now.getFullYear();
const pspYears = getPspYears(now);

const Filters = ({
  selectedYear,
  onYearChange,
  selectedMonth,
  onMonthChange,
}: FiltersProps) => {
  return (
    <div className="space-y-3">
      <YearSelector
        selectedYear={selectedYear}
        currentYear={currentYear}
        availableYears={pspYears}
        onYearChange={onYearChange}
      />

      <MonthSelector
        months={MONTHS_FULL}
        currentMonth={currentMonth}
        currentYear={currentYear}
        selectedYear={selectedYear}
        selectedMonth={selectedMonth}
        onMonthChange={onMonthChange}
        blockFutureMonths={false}
      />
    </div>
  );
};

export default Filters;
