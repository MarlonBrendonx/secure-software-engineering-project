import { describe, expect, it } from "vitest";
import {
  formatCurrency,
  formatDateOnly,
  formatMonthNameYear,
  formatMonthYear,
  formatPercentual,
  reconcileToTotal,
  truncTo,
} from "@/utils/formatter";

describe("reconcileToTotal", () => {
  it("mantém as partes quando não há resíduo", () => {
    expect(reconcileToTotal(9.99, [3.33, 3.33, 3.33])).toEqual([
      3.33, 3.33, 3.33,
    ]);
  });

  it("joga o resíduo positivo na maior parte", () => {
    const result = reconcileToTotal(10, [3.334, 3.333, 3.333]);
    expect(result).toEqual([3.34, 3.33, 3.33]);
    expect(result.reduce((a, b) => a + b, 0)).toBeCloseTo(10, 10);
  });

  it("subtrai o resíduo negativo da maior parte", () => {
    const result = reconcileToTotal(9.98, [3.334, 3.333, 3.333]);
    expect(result).toEqual([3.32, 3.33, 3.33]);
    expect(result.reduce((a, b) => a + b, 0)).toBeCloseTo(9.98, 10);
  });

  it("retorna lista vazia para partes vazias", () => {
    expect(reconcileToTotal(10, [])).toEqual([]);
  });

  it("garante que a soma das partes bate com o total arredondado", () => {
    const total = 100;
    const parts = [33.333, 33.333, 33.334];
    const result = reconcileToTotal(total, parts);
    expect(result.reduce((a, b) => a + b, 0)).toBeCloseTo(total, 10);
  });
});

describe("truncTo", () => {
  it("trunca (não arredonda) para o número de casas", () => {
    expect(truncTo(3.149, 2)).toBe(3.14);
    expect(truncTo(2.999, 2)).toBe(2.99);
    expect(truncTo(10.559, 2)).toBe(10.55);
  });

  it("trunca em direção a zero para negativos", () => {
    expect(truncTo(-3.149, 2)).toBe(-3.14);
  });
});

describe("formatCurrency", () => {
  it("formata número como BRL", () => {
    expect(formatCurrency(1234.5)).toContain("1.234,50");
    expect(formatCurrency(1234.5).startsWith("R$")).toBe(true);
  });

  it("retorna o literal 'R$ 0,00' para entradas realmente NaN", () => {
    expect(formatCurrency("abc")).toBe("R$ 0,00");
    expect(formatCurrency(Number.NaN)).toBe("R$ 0,00");
  });

  it("formata null como zero (Number(null) === 0, passa pelo toLocaleString)", () => {
    expect(formatCurrency(null)).toContain("0,00");
  });
});

describe("formatPercentual", () => {
  it("formata com vírgula decimal e sufixo %", () => {
    expect(formatPercentual(12.5)).toBe("12,50%");
  });

  it("retorna 0,00% para entradas inválidas", () => {
    expect(formatPercentual(null)).toBe("0,00%");
    expect(formatPercentual("abc")).toBe("0,00%");
  });
});

describe("formatDateOnly", () => {
  it("converte YYYY-MM-DD para DD/MM/YYYY sem passar por Date (fuso-safe)", () => {
    expect(formatDateOnly("2026-07-24")).toBe("24/07/2026");
  });

  it("retorna a entrada quando o formato é incompleto", () => {
    expect(formatDateOnly("2026-07")).toBe("2026-07");
    expect(formatDateOnly("invalido")).toBe("invalido");
  });
});

describe("formatMonthYear", () => {
  it("formata MM/YYYY com padding", () => {
    expect(formatMonthYear(7, 2026)).toBe("07/2026");
  });

  it("retorna — quando month ou year são ausentes/zero", () => {
    expect(formatMonthYear(null, 2026)).toBe("—");
    expect(formatMonthYear(7, null)).toBe("—");
    expect(formatMonthYear(0, 2026)).toBe("—");
  });
});

describe("formatMonthNameYear", () => {
  it("formata o mês por extenso com o ano", () => {
    expect(formatMonthNameYear(5, 2026)).toBe("Maio/2026");
    expect(formatMonthNameYear(12, 2026)).toBe("Dezembro/2026");
  });

  it("retorna — quando month ou year são ausentes/zero", () => {
    expect(formatMonthNameYear(null, 2026)).toBe("—");
    expect(formatMonthNameYear(5, null)).toBe("—");
    expect(formatMonthNameYear(0, 2026)).toBe("—");
  });

  it("retorna — quando o mês está fora do intervalo", () => {
    expect(formatMonthNameYear(13, 2026)).toBe("—");
  });
});
