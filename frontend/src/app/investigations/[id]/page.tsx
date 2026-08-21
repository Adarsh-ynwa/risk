"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bot, CheckCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskBadge } from "@/components/dashboard/kpi-card";
import { api, type InvestigationReport } from "@/lib/api";

export default function InvestigationPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState("");
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    api.getInvestigation(id)
      .then((r) => {
        setInvestigation(r.investigation);
      })
      .catch(() => setInvestigation(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="h-64 animate-pulse rounded-lg bg-muted" />;
  }

  if (!investigation) {
    return (
      <div className="text-center py-16 space-y-4">
        <Bot className="h-12 w-12 text-muted-foreground mx-auto" />
        <p className="text-lg font-semibold">No investigation found</p>
        <Link href={`/transactions/${id}`} className="text-primary text-sm">Run investigation from transaction detail →</Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link href={`/transactions/${id}`} className="text-sm text-muted-foreground hover:text-primary">← Transaction</Link>
        <h1 className="text-2xl font-bold mt-2 flex items-center gap-2">
          <Bot className="h-6 w-6 text-primary" />
          AI Investigation Report
        </h1>
        <p className="font-mono text-sm text-muted-foreground">{id}</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <RiskBadge level={investigation.risk_level} />
            <span className="text-sm text-muted-foreground">Confidence: {(investigation.confidence * 100).toFixed(0)}%</span>
          </div>
          <CardTitle className="text-base mt-2">Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{investigation.summary}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Primary Risk Factors</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {investigation.primary_risk_factors.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm"><CheckCircle className="h-4 w-4 text-primary shrink-0" />{f}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Investigation Findings</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {investigation.investigation_findings.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground"><CheckCircle className="h-4 w-4 text-muted-foreground shrink-0" />{f}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="border-primary/30 bg-primary/5">
        <CardHeader><CardTitle className="text-base text-primary">Recommendation: {investigation.recommended_action}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm">{investigation.recommended_action_reason}</p>
          {investigation.requires_human_review && (
            <p className="text-xs text-amber-400 mt-3 flex items-center gap-1">
              <Loader2 className="h-3 w-3" /> Human review required before final action
            </p>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
