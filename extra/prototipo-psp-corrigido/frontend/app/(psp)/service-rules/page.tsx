"use client";

import { ClipboardCheck } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import { ServiceRulesPage } from "@/components/registrations/service-rules/ServiceRulesPage";

export default function ServiceRulesRoute() {
  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Serviços e Regras"
        description="Gerencie os serviços e regras de faturamento por cliente"
        icon={ClipboardCheck}
      />
      <ServiceRulesPage />
    </div>
  );
}
