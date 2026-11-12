import { MONTHS_FULL } from "./constants";

export function formatPercentual(
  value: number | string | null | undefined,
): string {
  const num = Number(value);
  if (Number.isNaN(num)) return "0,00%";
  return `${num.toFixed(2).replace(".", ",")}%`;
}

export function formatCurrency(
  value: number | string | null | undefined,
): string {
  const num = Number(value);
  if (Number.isNaN(num)) return "R$ 0,00";
  return num.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function formatDateOnly(value: string): string {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

/** Arredonda para 2 casas decimais (centavos), mitigando representação binária. */
function roundCents(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function reconcileToTotal(total: number, parts: number[]): number[] {
  const roundedTotal = roundCents(total);
  const rounded = parts.map(roundCents);
  const residual = roundCents(
    roundedTotal - rounded.reduce((acc, value) => acc + value, 0),
  );
  if (residual === 0 || rounded.length === 0) return rounded;

  let largestIndex = 0;
  for (let i = 1; i < parts.length; i++) {
    if (parts[i] > parts[largestIndex]) largestIndex = i;
  }
  rounded[largestIndex] = roundCents(rounded[largestIndex] + residual);
  return rounded;
}

export function formatMonthYear(
  month: number | null | undefined,
  year: number | null | undefined,
): string {
  if (!month || !year) return "—";
  return `${String(month).padStart(2, "0")}/${year}`;
}

export function truncTo(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.trunc(Number(value) * factor) / factor;
}

/** Período por extenso, ex.: "Maio/2026". Usa o mesmo rótulo do MonthSelector. */
export function formatMonthNameYear(
  month: number | null | undefined,
  year: number | null | undefined,
): string {
  if (!month || !year) return "—";
  const label = MONTHS_FULL.find((m) => m.value === month)?.label;
  if (!label) return "—";
  return `${label}/${year}`;
}
