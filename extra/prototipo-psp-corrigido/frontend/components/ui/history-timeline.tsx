"use client";

import { Clock, History as HistoryIcon, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface HistoryTimelineEntry {
  uuid: string;
  action: string;
  username: string | null;
  created_at: string;
  status?: string | null;
  completed_at?: string | null;
}

export interface HistoryActionConfig {
  label: string;
  icon: React.ElementType;
  color: string;
  bg: string;
  line: string;
}

export interface HistoryStatusConfig {
  label: string;
  variant: "default" | "secondary" | "destructive";
  icon: React.ElementType;
  animate?: boolean;
  className?: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(startIso: string, endIso: string): string {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  if (ms < 1000) return "< 1s";
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return remaining > 0 ? `${minutes}m ${remaining}s` : `${minutes}m`;
}

interface HistoryTimelineProps<T extends HistoryTimelineEntry> {
  entries: T[];
  actionConfig: Record<string, HistoryActionConfig>;
  statusConfig?: Record<string, HistoryStatusConfig>;
  renderDetails?: (entry: T) => React.ReactNode;
  title?: string;
  fallbackAction?: HistoryActionConfig;
  headerActions?: React.ReactNode;
}

export function HistoryTimeline<T extends HistoryTimelineEntry>({
  entries,
  actionConfig,
  statusConfig,
  renderDetails,
  title = "Histórico",
  fallbackAction,
  headerActions,
}: HistoryTimelineProps<T>) {
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <HistoryIcon className="h-4 w-4" />
          {title}
          <Badge variant="secondary" className="ml-1 text-[10px] h-5">
            {entries.length}
          </Badge>
          {headerActions}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-[420px] overflow-y-auto pr-1">
          {entries.map((entry, i) => {
            const config =
              actionConfig[entry.action] ??
              fallbackAction ??
              Object.values(actionConfig)[0];
            const Icon = config.icon;
            const sConfig = entry.status ? statusConfig?.[entry.status] : null;
            const StatusIcon = sConfig?.icon;
            const isLast = i === entries.length - 1;

            return (
              <div key={entry.uuid} className="relative flex gap-3">
                {!isLast && (
                  <div
                    className={cn(
                      "absolute left-[15px] top-9 bottom-0 w-0.5",
                      config.line,
                    )}
                  />
                )}

                <div
                  className={cn(
                    "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                    config.bg,
                  )}
                >
                  <Icon className={cn("h-4 w-4", config.color)} />
                </div>

                <div className="flex-1 min-w-0 pb-5">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-medium text-sm">{config.label}</span>
                    {sConfig && StatusIcon && (
                      <Badge
                        variant={sConfig.variant}
                        className={cn(
                          "gap-1 text-[10px] h-5",
                          sConfig.className,
                        )}
                      >
                        <StatusIcon
                          className={cn(
                            "h-3 w-3",
                            sConfig.animate && "animate-spin",
                          )}
                        />
                        {sConfig.label}
                      </Badge>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {entry.username || "—"}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(entry.created_at)} às{" "}
                      {formatTime(entry.created_at)}
                    </span>
                    {entry.completed_at && (
                      <span className="text-muted-foreground/70">
                        (processado em{" "}
                        {formatDuration(entry.created_at, entry.completed_at)})
                      </span>
                    )}
                  </div>

                  {renderDetails?.(entry)}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
