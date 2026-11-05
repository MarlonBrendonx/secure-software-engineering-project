"use client";

import { Pencil, Plus, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import EmptyState from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Pagination, type PaginationProps } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getRuleTypeLabel, type ServiceRule } from "../types";

type ServiceRulesTableProps = {
  serviceRules: ServiceRule[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  // Só o admin cadastra regras; os demais perfis consultam (a API também recusa a escrita).
  canManage: boolean;
  onNewServiceRule: () => void;
  onEdit: (service: ServiceRule) => void;
  onDelete: (service: ServiceRule) => void;
  programNameFilter: string;
  onProgramNameFilterChange: (value: string) => void;
  serviceNameFilter: string;
  onServiceNameFilterChange: (value: string) => void;
  paginationProps: PaginationProps;
};

function ProgramColumnHeader({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleOpen = () => {
    setIsOpen(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleClose = () => {
    setIsOpen(false);
    onChange("");
  };

  if (!isOpen) {
    return (
      <div className="flex items-center gap-1">
        <span>Programas</span>
        <button
          type="button"
          onClick={handleOpen}
          className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <Search className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <div className="relative flex-1">
        <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={inputRef}
          placeholder="Filtrar programa..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-7 pl-7 pr-7 text-xs font-normal rounded-none border-x-0 border-t-0 border-b shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-b-0 bg-transparent"
        />
        <button
          type="button"
          onClick={handleClose}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

const ServiceRulesTable = ({
  serviceRules,
  isLoading,
  isError,
  onRetry,
  canManage,
  onNewServiceRule,
  onEdit,
  onDelete,
  programNameFilter,
  onProgramNameFilterChange,
  serviceNameFilter,
  onServiceNameFilterChange,
  paginationProps,
}: ServiceRulesTableProps) => {
  return (
    <div className="space-y-6">
      {canManage ? (
        <div className="flex justify-end">
          <Button className="gap-2 cursor-pointer" onClick={onNewServiceRule}>
            <Plus className="h-4 w-4" />
            Novo Serviço
          </Button>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Somente administradores podem cadastrar, editar ou excluir serviços e
          regras.
        </p>
      )}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar por serviço..."
          aria-label="Buscar serviços"
          value={serviceNameFilter}
          onChange={(e) => onServiceNameFilterChange(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton placeholders
            <Skeleton key={`skeleton-${i}`} className="h-12 w-full" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
          <span className="text-muted-foreground">
            Erro ao carregar serviços e regras.
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Nome do Serviço</TableHead>
                <TableHead>Tipo de Regra</TableHead>
                <TableHead>
                  <ProgramColumnHeader
                    value={programNameFilter}
                    onChange={onProgramNameFilterChange}
                  />
                </TableHead>
                <TableHead>Status</TableHead>
                {canManage && (
                  <TableHead className="text-right">Ações</TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {serviceRules.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={canManage ? 6 : 5}>
                    <EmptyState
                      title="Nenhum serviço cadastrado"
                      description={
                        canManage
                          ? 'Clique em "Novo Serviço" para cadastrar o primeiro serviço.'
                          : "Este cliente ainda não tem serviços cadastrados."
                      }
                      actionLabel={canManage ? "Novo Serviço" : undefined}
                      onAction={canManage ? onNewServiceRule : undefined}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                serviceRules.map((service) => (
                  <TableRow
                    key={service.uuid}
                    className="table-row-interactive"
                  >
                    <TableCell className="font-medium">
                      {service.code}
                    </TableCell>
                    <TableCell>{service.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {getRuleTypeLabel(service.rule_type)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {service.programs.length === 0 ? (
                        <span className="text-muted-foreground">—</span>
                      ) : service.programs.length === 1 ? (
                        <span>{service.programs[0].program_name}</span>
                      ) : (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="cursor-default truncate max-w-[200px] inline-block align-bottom">
                                {service.programs[0].program_name}...
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="bottom">
                              <div className="flex flex-col gap-1">
                                {service.programs.map((p) => (
                                  <span key={p.program_uuid}>
                                    {p.program_name}
                                  </span>
                                ))}
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          service.status === "Ativo" ? "default" : "secondary"
                        }
                        className={
                          service.status === "Ativo"
                            ? "bg-badge-ativo text-badge-ativo-fg border-current/30"
                            : "bg-badge-arq text-badge-arq-fg border-current/30"
                        }
                      >
                        {service.status}
                      </Badge>
                    </TableCell>
                    {canManage && (
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="cursor-pointer"
                            onClick={() => onEdit(service)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          {service.has_billing_items ? (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      disabled
                                      className="text-muted-foreground"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="top">
                                  Este serviço já possui lançamentos e não pode
                                  ser excluído.
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => onDelete(service)}
                              className="cursor-pointer text-destructive hover:text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <Pagination {...paginationProps} />
    </div>
  );
};

export default ServiceRulesTable;
