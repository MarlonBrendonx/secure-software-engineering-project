import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const PSP_START_YEAR = 2026;
const DASHBOARD_START_YEAR = 2024;

/**
 * Anos disponíveis para o PSP.
 * Começa em 2026; a partir de novembro, inclui o próximo ano.
 */
export function getPspYears(now: Date = new Date()): number[] {
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  const maxYear = currentMonth >= 11 ? currentYear + 1 : currentYear;
  const years: number[] = [];
  for (let y = PSP_START_YEAR; y <= maxYear; y++) {
    years.push(y);
  }
  return years;
}

/**
 * Anos disponíveis para o Dashboard.
 * Começa em 2024; inclui até o ano atual (aparece quando janeiro chega).
 */
export function getDashboardYears(now: Date = new Date()): number[] {
  const currentYear = now.getFullYear();
  const years: number[] = [];
  for (let y = DASHBOARD_START_YEAR; y <= currentYear; y++) {
    years.push(y);
  }
  return years;
}

interface YearSelectorProps {
  selectedYear: number | null;
  currentYear: number;
  availableYears: number[];
  onYearChange: (year: number) => void;
}

const YearSelector = ({
  selectedYear,
  currentYear,
  availableYears,
  onYearChange,
}: YearSelectorProps) => {
  return (
    <div className="flex items-center gap-4">
      <Label className="text-sm font-medium text-foreground">Ano:</Label>
      <div className="block md:hidden">
        <Select
          value={selectedYear != null ? String(selectedYear) : ""}
          onValueChange={(value) => onYearChange(Number(value))}
        >
          <SelectTrigger className="w-full cursor-pointer">
            <SelectValue placeholder="Ano" />
          </SelectTrigger>
          <SelectContent>
            {availableYears.map((year) => (
              <SelectItem key={year} value={String(year)}>
                {year}
                {year === currentYear && " (Atual)"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="hidden gap-2 md:flex">
        {availableYears.map((year) => (
          <Button
            key={year}
            variant={selectedYear === year ? "default" : "outline"}
            size="sm"
            onClick={() => onYearChange(year)}
            className={cn(
              "min-w-16 cursor-pointer text-xs",
              year === currentYear &&
                selectedYear !== year &&
                "ring-2 ring-ep-azul ring-offset-2",
            )}
          >
            {year}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default YearSelector;
