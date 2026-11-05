import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

const MONTHS = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

interface MonthYearPickerProps {
  value: string; // "AAAA/MM"
  onChange: (value: string) => void;
}

export function MonthYearPicker({ value, onChange }: MonthYearPickerProps) {
  const [open, setOpen] = useState(false);

  const parts = value.split("/");
  const selectedYear =
    Number.parseInt(parts[0], 10) || new Date().getFullYear();
  const selectedMonth = Number.parseInt(parts[1], 10) || 1;

  const [viewYear, setViewYear] = useState(selectedYear);

  const handleSelect = (month: number) => {
    const formatted = `${viewYear}/${String(month).padStart(2, "0")}`;
    onChange(formatted);
    setOpen(false);
  };

  const displayLabel = `${MONTHS[selectedMonth - 1]} / ${selectedYear}`;

  return (
    <Popover
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setViewYear(selectedYear);
      }}
    >
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-start gap-2 font-normal cursor-pointer"
        >
          <Calendar className="h-4 w-4 text-muted-foreground" />
          {displayLabel}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-3" align="start">
        <div className="flex items-center justify-between mb-3">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 cursor-pointer"
            onClick={() => setViewYear((y) => y - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-semibold">{viewYear}</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 cursor-pointer"
            onClick={() => setViewYear((y) => y + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {MONTHS.map((label, idx) => {
            const month = idx + 1;
            const isSelected =
              month === selectedMonth && viewYear === selectedYear;
            return (
              <Button
                key={label}
                variant={isSelected ? "default" : "ghost"}
                size="sm"
                className={cn(
                  "text-xs cursor-pointer",
                  isSelected && "pointer-events-none",
                )}
                onClick={() => handleSelect(month)}
              >
                {label}
              </Button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
