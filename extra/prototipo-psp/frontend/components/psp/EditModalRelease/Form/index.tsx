import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MonthYearPicker } from "@/components/ui/month-year-picker";
import { Textarea } from "@/components/ui/textarea";
import { formatCurrency } from "@/utils/formatter";
import { formatNumber } from "../../types";

interface FormProps {
  service: {
    ruleType: string;
    baseValue?: number;
    percentage?: number;
  } | null;
  quantity: string;
  setQuantity: (value: string) => void;
  inputValue: string;
  setInputValue: (value: string) => void;
  baseValue: string;
  setBaseValue: (value: string) => void;
  totalValue: number;
  poNumber: string;
  setPoNumber: (value: string) => void;
  referencePeriod: string;
  competencePeriod: string;
  setCompetencePeriod: (value: string) => void;
  billingPeriod: string;
  setBillingPeriod: (value: string) => void;
  invoiceDescription: string;
  setInvoiceDescription: (value: string) => void;
  notes: string;
  setNotes: (value: string) => void;
}

const Form = ({
  service,
  quantity,
  setQuantity,
  inputValue,
  setInputValue,
  baseValue,
  setBaseValue,
  totalValue,
  poNumber,
  setPoNumber,
  referencePeriod,
  competencePeriod,
  setCompetencePeriod,
  billingPeriod,
  setBillingPeriod,
  invoiceDescription,
  setInvoiceDescription,
  notes,
  setNotes,
}: FormProps) => {
  return (
    <div className="space-y-4">
      {service && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(service.ruleType === "multiplicacao" ||
            service.ruleType === "range") && (
            <div className="space-y-2">
              <Label>Quantidade</Label>
              <Input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
          )}
          {(service.ruleType === "valor_fixo" ||
            service.ruleType === "valor_variavel") && (
            <div className="space-y-2">
              <Label>Valor</Label>
              <Input
                type="number"
                step="any"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
              />
            </div>
          )}
          {service.ruleType === "percentual" && (
            <div className="space-y-2">
              <Label>
                Valor Base ({formatNumber(service.percentage || 0)}%)
              </Label>
              <Input
                type="number"
                value={baseValue}
                onChange={(e) => setBaseValue(e.target.value)}
              />
            </div>
          )}
          <div className="space-y-2">
            <Label>Valor Total</Label>
            <div
              className={`h-10 flex items-center px-3 border rounded-md ${totalValue < 0 ? "bg-destructive/10 border-destructive/20" : "bg-primary/10 border-primary/20"}`}
            >
              <span
                className={`font-bold ${totalValue < 0 ? "text-destructive" : "text-primary"}`}
              >
                {formatCurrency(totalValue)}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>Mês do Lançamento</Label>
          <Input value={referencePeriod} readOnly className="bg-muted/50" />
        </div>
        <div className="space-y-2">
          <Label>Competência</Label>
          <MonthYearPicker
            value={competencePeriod}
            onChange={setCompetencePeriod}
          />
        </div>
        <div className="space-y-2">
          <Label>Período de Faturamento</Label>
          <MonthYearPicker value={billingPeriod} onChange={setBillingPeriod} />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Número da PO</Label>
        <Input
          value={poNumber}
          onChange={(e) => setPoNumber(e.target.value)}
          placeholder="Ex: PO-12345"
        />
      </div>

      <div className="space-y-2">
        <Label>Descrição da Nota</Label>
        <Input
          value={invoiceDescription}
          onChange={(e) => setInvoiceDescription(e.target.value.slice(0, 100))}
          maxLength={100}
          placeholder="Descrição da nota fiscal"
        />
        <p className="text-xs text-muted-foreground text-right">
          {invoiceDescription.length}/100
        </p>
      </div>

      <div className="space-y-2">
        <Label>Observação</Label>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Observações internas sobre este lançamento..."
          className="resize-none"
        />
      </div>
    </div>
  );
};

export default Form;
