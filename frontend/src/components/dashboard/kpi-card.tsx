import { cn, formatCurrency, riskBadgeClass } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

export function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  accent,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  accent?: string;
}) {
  return (
    <Card className="border-border/60 bg-card/80">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={cn("rounded-md p-2", accent || "bg-primary/10")}>
          <Icon className={cn("h-4 w-4", accent ? "text-current" : "text-primary")} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

export function RiskBadge({ level }: { level: string | null | undefined }) {
  return <span className={riskBadgeClass(level)}>{level || "UNKNOWN"}</span>;
}

export function RiskScoreRing({ score, level }: { score: number | null; level: string | null }) {
  const s = score ?? 0;
  const color =
    level === "CRITICAL" ? "#ef4444" : level === "HIGH" ? "#f97316" : level === "MEDIUM" ? "#eab308" : "#22c55e";

  return (
    <div className="relative flex h-32 w-32 items-center justify-center">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="hsl(var(--muted))" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${s * 2.64} 264`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute text-center">
        <p className="text-3xl font-bold">{Math.round(s)}</p>
        <p className="text-xs text-muted-foreground">/ 100</p>
      </div>
    </div>
  );
}

export { formatCurrency, riskBadgeClass };
