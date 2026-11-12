import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./tooltip";

interface TruncatedTextProps {
  children: React.ReactNode;
  content?: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
  contentClassName?: string;
  as?: "span" | "p";
}

export default function TruncatedText({
  children,
  content,
  side = "bottom",
  className,
  contentClassName,
  as: Tag = "span",
}: TruncatedTextProps) {
  const tooltipContent = content ?? children;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Tag className={cn("truncate block cursor-default", className)}>
            {children}
          </Tag>
        </TooltipTrigger>
        <TooltipContent
          side={side}
          className={cn(
            "max-w-xs max-h-48 overflow-y-auto whitespace-pre-wrap break-words",
            contentClassName,
          )}
        >
          {tooltipContent}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
