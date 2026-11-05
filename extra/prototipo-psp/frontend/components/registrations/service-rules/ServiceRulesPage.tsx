"use client";

import { ArrowLeft, Building2, ChevronsUpDown, Loader2 } from "lucide-react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useServiceRuleManager } from "@/hooks/registrations/useServiceRuleManager";
import { useDebounce } from "@/hooks/use-debounce";
import { useUserRole } from "@/hooks/use-user-role";
import type { ClientSummary } from "@/lib/registrations/clients";
import {
  useClientsSearch,
  useClientsSummary,
} from "@/lib/registrations/clients";
import ModalServiceRules from "./ModalServiceRules";
import ServiceRulesTable from "./ServiceRulesTable";

export function ServiceRulesPage() {
  const [selectedClient, setSelectedClient] = useState<ClientSummary | null>(
    null,
  );
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  const summaryQuery = useClientsSummary();
  const searchQuery = useClientsSearch(debouncedSearch);

  const isSearching = debouncedSearch.trim().length > 0;
  const source = isSearching ? searchQuery : summaryQuery;
  const clients = source.data;
  const isDebouncePending = search.trim() !== debouncedSearch.trim();
  const listLoading = source.isLoading || isDebouncePending;

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) setSearch("");
  };

  const handleClientSelect = (uuid: string) => {
    const client = clients.find((c) => c.uuid === uuid) ?? null;
    setSelectedClient(client);
    setOpen(false);
    setSearch("");
  };

  const { hasNextPage, isFetchingNextPage, fetchNextPage } = source;

  const handleListScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget;
      if (!hasNextPage || isFetchingNextPage) return;

      const threshold = 80;
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold) {
        fetchNextPage();
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage],
  );

  return (
    <Card>
      <CardHeader className="pb-4">
        {selectedClient ? (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={() => setSelectedClient(null)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
            <div>
              <CardTitle className="text-base">
                {selectedClient.client_code} - {selectedClient.name}
              </CardTitle>
              <CardDescription className="text-xs">
                Serviços e regras do cliente selecionado
              </CardDescription>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 shrink-0 text-muted-foreground" />
              <div>
                <CardTitle className="text-base">Selecione o Cliente</CardTitle>
                <CardDescription className="text-xs">
                  Selecione um cliente para visualizar e gerenciar seus serviços
                  e regras
                </CardDescription>
              </div>
            </div>
            <Popover open={open} onOpenChange={handleOpenChange}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  aria-expanded={open}
                  className="w-full sm:w-80 justify-between cursor-pointer font-normal"
                  disabled={summaryQuery.isLoading}
                >
                  {summaryQuery.isLoading
                    ? "Carregando..."
                    : "Pesquisar cliente..."}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder="Buscar por nome ou código..."
                    value={search}
                    onValueChange={setSearch}
                  />
                  <CommandList onScroll={handleListScroll}>
                    {listLoading ? (
                      <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Buscando clientes...
                      </div>
                    ) : (
                      <>
                        <CommandEmpty>Nenhum cliente encontrado.</CommandEmpty>
                        <CommandGroup>
                          {clients.map((client) => (
                            <CommandItem
                              key={client.uuid}
                              value={client.uuid}
                              onSelect={() => handleClientSelect(client.uuid)}
                              className="cursor-pointer"
                            >
                              {client.client_code} - {client.name}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                        {isFetchingNextPage && (
                          <div className="flex items-center justify-center gap-2 py-2 text-xs text-muted-foreground">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Carregando mais...
                          </div>
                        )}
                      </>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {selectedClient ? (
          <ServiceRulesContent client={selectedClient} />
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <Building2 className="h-12 w-12 text-muted-foreground/30" />
            <div>
              <p className="font-medium text-muted-foreground">
                Nenhum cliente selecionado
              </p>
              <p className="text-sm text-muted-foreground/70">
                Selecione um cliente acima para visualizar seus serviços e
                regras
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ServiceRulesContent({ client }: { client: ClientSummary }) {
  const { tabProps, modalProps, deleteDialogProps } =
    useServiceRuleManager(client);
  const { canManageServiceRules } = useUserRole();

  return (
    <>
      <ServiceRulesTable {...tabProps} canManage={canManageServiceRules} />
      <ModalServiceRules {...modalProps} />
      <ConfirmDialog
        open={deleteDialogProps.open}
        onOpenChange={deleteDialogProps.onOpenChange}
        onConfirm={deleteDialogProps.onConfirm}
        loading={deleteDialogProps.loading}
        title="Confirmar Exclusão"
        description={
          deleteDialogProps.serviceName ? (
            <>
              Tem certeza que deseja excluir o serviço{" "}
              <strong>{deleteDialogProps.serviceName}</strong>? Esta ação não
              pode ser desfeita.
            </>
          ) : (
            ""
          )
        }
        confirmLabel="Excluir"
        loadingLabel="Excluindo..."
        variant="destructive"
      />
    </>
  );
}
