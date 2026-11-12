"use client";

import { ChevronsUpDown, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export type SearchableComboboxProps<T> = {
  value: string;
  onValueChange: (value: string) => void;
  items: T[];
  getKey: (item: T) => string;
  getLabel: (item: T) => string;
  label?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  isLoading?: boolean;
  disabled?: boolean;
};

export function SearchableCombobox<T>({
  value,
  onValueChange,
  items,
  getKey,
  getLabel,
  label,
  placeholder = "Selecionar...",
  searchPlaceholder = "Buscar...",
  emptyMessage = "Nenhum item encontrado.",
  isLoading = false,
  disabled = false,
}: SearchableComboboxProps<T>) {
  const [open, setOpen] = useState(false);

  const selectedItem = items.find((item) => getKey(item) === value);

  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}
      <div className="relative">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              aria-expanded={open}
              className="w-full justify-start cursor-pointer font-normal pr-14"
              disabled={isLoading || disabled}
            >
              <span className="truncate">
                {isLoading
                  ? "Carregando..."
                  : selectedItem
                    ? getLabel(selectedItem)
                    : placeholder}
              </span>
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
            <Command>
              <CommandInput placeholder={searchPlaceholder} />
              <CommandList>
                <CommandEmpty>{emptyMessage}</CommandEmpty>
                <CommandGroup>
                  {items.map((item) => {
                    const key = getKey(item);
                    return (
                      <CommandItem
                        key={key}
                        value={getLabel(item)}
                        onSelect={() => {
                          onValueChange(key);
                          setOpen(false);
                        }}
                        className="cursor-pointer"
                      >
                        {getLabel(item)}
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
        <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {value && (
            <button
              type="button"
              onClick={() => onValueChange("")}
              className="pointer-events-auto"
            >
              <X className="h-4 w-4 opacity-50 hover:opacity-100" />
            </button>
          )}
          <ChevronsUpDown className="h-4 w-4 opacity-50" />
        </div>
      </div>
    </div>
  );
}
