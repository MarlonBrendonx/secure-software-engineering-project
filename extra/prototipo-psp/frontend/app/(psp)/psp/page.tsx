"use client";
import { Search } from "lucide-react";
import ClientAccordion from "@/components/psp/Accordion";
import Filters from "@/components/psp/Filters";
import Summary from "@/components/psp/Summary";
import { Card, CardContent } from "@/components/ui/card";
import EmptyState from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { usePspManager } from "@/hooks/psp/usePspManager";

export default function Psp() {
  const {
    filterProps,
    searchProps,
    summaryProps,
    accordionProps,
    paginationProps,
    isLoading,
  } = usePspManager();

  return (
    <div className="space-y-6 animate-fade-in ">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Faturamento PSP</h1>
        <p className="text-muted-foreground">
          Gerencie os lançamentos de faturamento dos clientes PSP
        </p>
      </div>

      <Card className="">
        <CardContent className="p-3 pt-6 space-y-4 sm:p-6">
          <Card>
            <CardContent className="pt-6">
              <Filters {...filterProps} />
            </CardContent>
          </Card>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por cliente..."
              value={searchProps.searchTerm}
              onChange={(e) => searchProps.onSearchChange(e.target.value)}
              className="pl-9"
            />
          </div>

          <Summary {...summaryProps} />

          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton placeholders
                <Skeleton key={`skeleton-${i}`} className="h-12 w-full" />
              ))}
            </div>
          )}

          {!isLoading && filterProps.selectedMonth === null && (
            <EmptyState
              title="Selecione um período"
              description="Escolha o ano e o mês para visualizar os lançamentos."
            />
          )}

          {!isLoading && filterProps.selectedMonth !== null && (
            <ClientAccordion {...accordionProps} />
          )}

          {!isLoading && filterProps.selectedMonth !== null && (
            <Pagination {...paginationProps} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
