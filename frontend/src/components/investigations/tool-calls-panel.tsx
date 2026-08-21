import { Wrench } from "lucide-react";
import type { ToolCallRecord } from "@/lib/api";

export function ToolCallsPanel({ toolCalls, isFallback }: { toolCalls?: ToolCallRecord[]; isFallback?: boolean }) {
  if (!toolCalls?.length) return null;

  return (
    <div className="rounded-lg border border-border/60 bg-muted/10 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Wrench className="h-4 w-4 text-primary" />
        <p className="text-sm font-semibold">Agent Tool Calls</p>
        {isFallback && (
          <span className="text-xs rounded-full bg-muted px-2 py-0.5 text-muted-foreground">Fallback mode</span>
        )}
      </div>
      <ul className="space-y-2">
        {toolCalls.map((call, i) => (
          <li key={`${call.tool}-${i}`} className="rounded-md border border-border/40 bg-background/50 p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-primary">{call.tool}</code>
              <span className="text-xs text-muted-foreground">{call.result_summary}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{call.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
