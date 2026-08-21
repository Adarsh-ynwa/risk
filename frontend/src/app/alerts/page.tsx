"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Clock, ExternalLink, ShieldAlert } from "lucide-react";
import { api, type PaginatedTransactions } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskBadge } from "@/components/dashboard/kpi-card";
import { formatCurrency } from "@/lib/utils";

export default function AlertsPage() {
  const [data, setData] = useState<PaginatedTransactions | null>(null);
  const [level, setLevel] = useState("ALL");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    api.transactions({ page: 1, page_size: 100, minimum_risk: 60, risk_level: level === "ALL" ? undefined : level, sort_by: "risk_score", sort_order: "desc" })
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [level]);
  const pending = data?.items.filter((item) => !["APPROVED", "BLOCKED", "VERIFIED"].includes(item.status)).length ?? 0;
  return <div className="space-y-6">
    <div><h1 className="text-3xl font-bold">Analyst Alert Queue</h1><p className="text-muted-foreground">Prioritized suspicious payments awaiting verification or review.</p></div>
    <div className="grid gap-4 sm:grid-cols-3">
      <QueueCard title="Open alerts" value={pending} icon={AlertTriangle} />
      <QueueCard title="Critical" value={data?.items.filter((x) => x.risk_level === "CRITICAL").length ?? 0} icon={ShieldAlert} />
      <QueueCard title="Awaiting approval" value={data?.items.filter((x) => x.status === "PENDING_HUMAN_APPROVAL").length ?? 0} icon={Clock} />
    </div>
    <div className="flex gap-2">{["ALL", "HIGH", "CRITICAL"].map((item) => <Button key={item} size="sm" variant={level === item ? "default" : "outline"} onClick={() => setLevel(item)}>{item}</Button>)}</div>
    <Card><CardHeader><CardTitle>Priority cases</CardTitle></CardHeader><CardContent className="p-0">
      {loading ? <div className="p-8 text-muted-foreground">Loading alerts…</div> : !data?.items.length ? <div className="p-8 text-muted-foreground">No alerts match this filter.</div> :
        <div className="divide-y divide-border">{data.items.map((item, index) => <div key={item.transaction_id} className="grid items-center gap-3 p-4 md:grid-cols-[60px_1fr_120px_110px_180px_40px]">
          <span className="text-xs font-semibold text-muted-foreground">#{index + 1}</span><div><p className="font-mono text-sm font-semibold">{item.transaction_id}</p><p className="text-xs text-muted-foreground">{item.customer_id} · {item.merchant_category} · {item.country}</p></div>
          <p className="font-semibold">{formatCurrency(item.transaction_amount)}</p><div><RiskBadge level={item.risk_level} /><p className="mt-1 text-xs text-muted-foreground">Score {item.risk_score?.toFixed(1)}</p></div><span className="text-xs text-muted-foreground">{item.status.replace(/_/g, " ")}</span>
          <Link aria-label="Open case" href={`/transactions/${item.transaction_id}`} className="text-primary"><ExternalLink className="h-4 w-4" /></Link>
        </div>)}</div>}
    </CardContent></Card>
  </div>;
}

function QueueCard({ title, value, icon: Icon }: { title: string; value: number; icon: React.ElementType }) {
  return <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-sm text-muted-foreground">{title}</p><p className="text-2xl font-bold">{value}</p></div><Icon className="h-5 w-5 text-primary" /></CardContent></Card>;
}
