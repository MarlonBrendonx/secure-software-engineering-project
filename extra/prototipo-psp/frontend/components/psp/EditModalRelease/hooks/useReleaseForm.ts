import { useEffect, useMemo, useState } from "react";
import { MONTHS_SHORT } from "@/utils/constants";
import type { ApiRange, ServiceRow } from "../../types";

interface UseReleaseFormParams {
  open: boolean;
  row: ServiceRow;
  selectedYear: number;
  selectedMonth: number;
}

function formatPeriod(year: number, month: number) {
  return `${year}/${String(month).padStart(2, "0")}`;
}

function nextMonth(year: number, month: number) {
  return month === 12
    ? { year: year + 1, month: 1 }
    : { year, month: month + 1 };
}

function parsePeriod(
  value: string,
  fallbackYear: number,
  fallbackMonth: number,
) {
  const parts = value.split("/");
  if (parts.length === 2) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!Number.isNaN(y) && !Number.isNaN(m) && m >= 1 && m <= 12) {
      return { year: y, month: m };
    }
  }
  return { year: fallbackYear, month: fallbackMonth };
}

export function useReleaseForm({
  open,
  row,
  selectedYear,
  selectedMonth,
}: UseReleaseFormParams) {
  const [quantity, setQuantity] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [baseValue, setBaseValue] = useState("");
  const [poNumber, setPoNumber] = useState("");
  const [invoiceDescription, setInvoiceDescription] = useState("");
  const [notes, setNotes] = useState("");

  const defaultBilling = nextMonth(selectedYear, selectedMonth);
  const [billingPeriod, setBillingPeriod] = useState(
    formatPeriod(defaultBilling.year, defaultBilling.month),
  );

  const [competencePeriod, setCompetencePeriod] = useState(() => {
    const now = new Date();
    return formatPeriod(now.getFullYear(), now.getMonth() + 1);
  });

  const service = useMemo(
    () => ({
      ruleType: row.ruleType,
      baseValue: row.itemBaseValue ?? row.ruleBaseValue ?? undefined,
      percentage: row.rulePercentage ?? undefined,
    }),
    [row.ruleType, row.itemBaseValue, row.ruleBaseValue, row.rulePercentage],
  );

  const ranges: ApiRange[] = row.ranges ?? [];

  const referencePeriod = `${MONTHS_SHORT[selectedMonth - 1]?.label}/${selectedYear}`;

  const parsedPeriod = useMemo(
    () => parsePeriod(billingPeriod, selectedYear, selectedMonth),
    [billingPeriod, selectedYear, selectedMonth],
  );

  const parsedCompetence = useMemo(
    () =>
      parsePeriod(
        competencePeriod,
        new Date().getFullYear(),
        new Date().getMonth() + 1,
      ),
    [competencePeriod],
  );

  const totalValue = useMemo(() => {
    switch (service.ruleType) {
      case "valor_fixo":
      case "valor_variavel":
        return parseFloat(inputValue) || 0;
      case "multiplicacao":
        return (parseFloat(quantity) || 0) * (service.baseValue || 0);
      case "range": {
        const qtd = parseFloat(quantity) || 0;
        let total = 0;
        for (const range of ranges) {
          const rangeTo = range.range_to ?? Number.MAX_SAFE_INTEGER;
          if (qtd >= range.range_from && qtd <= rangeTo) {
            if (range.range_type === "per_unit_value") {
              total = qtd * range.value;
            } else if (range.range_type === "fixed_value") {
              total = range.value;
            }
            break;
          }
        }
        return total;
      }
      case "percentual":
        return ((parseFloat(baseValue) || 0) * (service.percentage || 0)) / 100;
      default:
        return 0;
    }
  }, [service, quantity, inputValue, baseValue, ranges]);

  const competenceLabel = useMemo(
    () =>
      `${String(parsedCompetence.month).padStart(2, "0")}/${parsedCompetence.year}`,
    [parsedCompetence],
  );

  const suggestedDescription = useMemo(() => {
    const parts: string[] = [];
    if (poNumber.trim()) parts.push(`PO: ${poNumber.trim()}`);
    if (row.programName) parts.push(row.programName);
    parts.push(row.serviceName);
    parts.push(competenceLabel);
    return parts.join(" - ");
  }, [poNumber, row.programName, row.serviceName, competenceLabel]);

  useEffect(() => {
    if (suggestedDescription && !row.itemId) {
      setInvoiceDescription(suggestedDescription);
    }
  }, [suggestedDescription, row.itemId]);

  useEffect(() => {
    if (open && row) {
      setPoNumber(row.poNumber || "");
      setInvoiceDescription(row.invoiceDescription || "");
      setNotes(row.notes || "");

      const isEditing = !!row.itemId;

      if (isEditing && row.billingYear && row.billingMonth) {
        setBillingPeriod(formatPeriod(row.billingYear, row.billingMonth));
      } else {
        const def = nextMonth(selectedYear, selectedMonth);
        setBillingPeriod(formatPeriod(def.year, def.month));
      }

      if (isEditing && row.competenceYear && row.competenceMonth) {
        setCompetencePeriod(
          formatPeriod(row.competenceYear, row.competenceMonth),
        );
      } else {
        const now = new Date();
        setCompetencePeriod(
          formatPeriod(now.getFullYear(), now.getMonth() + 1),
        );
      }

      if (row.itemId) {
        setQuantity(row.quantity?.toString() || "");
        if (
          row.ruleType === "valor_fixo" ||
          row.ruleType === "valor_variavel"
        ) {
          setInputValue(row.totalValue?.toString() || "");
        }
        if (row.ruleType === "percentual") {
          if (row.itemBaseValue != null) {
            setBaseValue(row.itemBaseValue.toString());
          } else if (service.percentage) {
            const base = row.totalValue
              ? (row.totalValue * 100) / service.percentage
              : 0;
            setBaseValue(base.toString());
          }
        }
      } else {
        setQuantity("");
        setInputValue("");
        setBaseValue("");
      }
    }
  }, [open, row, service, selectedMonth, selectedYear]);

  return {
    // State + setters
    quantity,
    setQuantity,
    inputValue,
    setInputValue,
    baseValue,
    setBaseValue,
    poNumber,
    setPoNumber,
    invoiceDescription,
    setInvoiceDescription,
    notes,
    setNotes,
    billingPeriod,
    setBillingPeriod,
    competencePeriod,
    setCompetencePeriod,
    // Derived
    service,
    referencePeriod,
    parsedPeriod,
    parsedCompetence,
    totalValue,
  };
}
