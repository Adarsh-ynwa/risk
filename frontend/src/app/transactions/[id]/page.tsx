"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Bot,
  CheckCircle,
  Clock,
  Globe,
  MapPin,
  Shield,
  Smartphone,
  CreditCard,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RiskBadge, RiskScoreRing, formatCurrency } from "@/components/dashboard/kpi-card";
import { ToolCallsPanel } from "@/components/investigations/tool-calls-panel";
import { showToast } from "@/components/ui/toaster";
import { api, type InvestigationReport, type TransactionDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function TransactionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string>("");
  const [txn, setTxn] = useState<TransactionDetail | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [investigationFallback, setInvestigationFallback] = useState(false);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  // Kept as inactive dialog state for backwards-compatible action API handling;
  // the UI no longer exposes manual demo-action controls.
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      let detail = await api.transaction(id);
      if (detail.risk_score == null) {
        await api.analyzeRisk(id);
        detail = await api.transaction(id);
      }
      setTxn(detail);
      try {
        const inv = await api.getInvestigation(id);
        setInvestigation(inv.investigation);
        setInvestigationFallback(inv.is_fallback);
      } catch {
        setInvestigation(null);
        setInvestigationFallback(false);
      }
    } catch {
      setTxn(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const runInvestigation = async () => {
    if (!id) return;
    setInvestigating(true);
    try {
      const result = await api.investigate(id);
      setInvestigation(result.investigation);
      setInvestigationFallback(result.is_fallback);
      showToast({
        title: result.requires_human_approval ? "Human approval required" : "Agent decision applied",
        description: result.requires_human_approval
          ? "The agent recommends BLOCK. A human analyst must approve the final block."
          : `Agent applied ${result.action_applied?.replace(/_/g, " ") || "a decision"}.`,
      });
      await load();
    } catch (e) {
      showToast({ title: "Investigation failed", description: String(e), variant: "destructive" });
    } finally {
      setInvestigating(false);
    }
  };

  const executeAction = async (action: string) => {
    if (!id) return;
    try {
      const result = await api.action(id, action);
      showToast({ title: "Action applied", description: `Transaction ${result.new_status}. Demo action — no real payment processed.` });
      load();
    } catch (e) {
      showToast({ title: "Action failed", description: String(e), variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );
  }

  if (!txn) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <p className="text-lg font-semibold">Transaction not found</p>
        <Link href="/transactions" className="text-primary text-sm mt-2 inline-block">← Back to transactions</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/transactions" className="text-sm text-muted-foreground hover:text-primary">← Transactions</Link>
          <h1 className="text-2xl font-bold font-mono mt-1">{txn.transaction_id}</h1>
          <p className="text-muted-foreground">{txn.transaction_date} {txn.transaction_time}</p>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge level={txn.risk_level} />
          <span className="text-sm text-muted-foreground">{txn.status}</span>
        </div>
      </div>

      {txn.status === "PENDING_HUMAN_APPROVAL" && (
        <div className="flex gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold text-amber-300">Human approval required</p>
            <p className="text-sm text-muted-foreground">This critical transaction was escalated automatically. Blocking or releasing it requires an analyst decision.</p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Transaction Information</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <InfoRow icon={CreditCard} label="Amount" value={formatCurrency(txn.transaction_amount)} highlight />
              <InfoRow icon={CreditCard} label="Payment Method" value={txn.payment_method} />
              <InfoRow icon={Shield} label="Merchant Category" value={txn.merchant_category} />
              <InfoRow icon={Globe} label="Country" value={txn.country} />
              <InfoRow icon={MapPin} label="City" value={txn.city} />
              <InfoRow icon={Smartphone} label="Device" value={txn.device_type} />
              <InfoRow icon={Clock} label="Hour" value={`${txn.hour_of_day}:00`} />
              <InfoRow icon={Globe} label="International" value={txn.is_international ? "Yes" : "No"} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Risk Factors</CardTitle>
              <CardDescription>Deterministic rules triggered for this transaction</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {txn.triggered_rules.length ? txn.triggered_rules.map((rule) => (
                <div key={rule.rule_id} className="flex gap-3 rounded-lg border border-border/60 bg-muted/20 p-4">
                  <AlertTriangle className={cn("h-5 w-5 shrink-0 mt-0.5",
                    rule.severity === "HIGH" ? "text-red-400" : "text-amber-400"
                  )} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{rule.name}</span>
                      <span className="text-xs rounded bg-muted px-2 py-0.5">{rule.severity}</span>
                      <span className="text-xs text-muted-foreground">+{rule.points} pts</span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{rule.explanation}</p>
                  </div>
                </div>
              )) : (
                <p className="text-sm text-muted-foreground">No rules triggered.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5 text-primary" />
                  AI Risk Investigator
                </CardTitle>
                <CardDescription>Agentic AI investigation with tool-based evidence gathering</CardDescription>
              </div>
              <Button onClick={runInvestigation} disabled={investigating} className="gap-2">
                {investigating ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Agent is investigating...</>
                ) : (
                  "Run AI Investigation"
                )}
              </Button>
            </CardHeader>
            <CardContent>
              {investigating && (
                <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 p-4 mb-4">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <p className="text-sm">Agent is investigating transaction context...</p>
                </div>
              )}
              {investigation ? (
                <div className="space-y-4">
                  <div className="rounded-lg border border-border p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <RiskBadge level={investigation.risk_level} />
                      <span className="text-xs text-muted-foreground">Confidence: {(investigation.confidence * 100).toFixed(0)}%</span>
                      {investigation.requires_human_review && (
                        <span className="text-xs rounded-full bg-amber-500/10 text-amber-400 px-2 py-0.5">Human Review Required</span>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed">{investigation.summary}</p>
                  </div>
                  <Section title="Primary Risk Factors" items={investigation.primary_risk_factors} />
                  <Section title="Investigation Findings" items={investigation.investigation_findings} />
                  <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                    <p className="text-sm font-semibold text-primary">Recommended: {investigation.recommended_action}</p>
                    <p className="text-sm text-muted-foreground mt-1">{investigation.recommended_action_reason}</p>
                  </div>
                  <ToolCallsPanel toolCalls={investigation.tool_calls} isFallback={investigationFallback} />
                  <Link href={`/investigations/${id}`} className="text-sm text-primary hover:underline">
                    View full investigation report →
                  </Link>
                </div>
              ) : !investigating ? (
                <p className="text-sm text-muted-foreground">
                  Run an AI investigation to get agent-powered analysis with customer history, similar transactions, and risk context.
                </p>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="text-lg">Risk Panel</CardTitle></CardHeader>
            <CardContent className="flex flex-col items-center gap-4">
              <RiskScoreRing score={txn.risk_score} level={txn.risk_level} />
              <RiskBadge level={txn.risk_level} />
              <div className="w-full space-y-2 text-sm">
                <ScoreRow label="Fraud Probability" value={txn.fraud_probability != null ? `${(txn.fraud_probability * 100).toFixed(1)}%` : "—"} />
                <ScoreRow label="ML Score" value={txn.ml_score != null ? txn.ml_score.toFixed(1) : "—"} />
                <ScoreRow label="Rule Score" value={txn.rule_score != null ? txn.rule_score.toFixed(1) : "—"} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Agent Decision</CardTitle>
              <CardDescription>Demo action — no real payment is processed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {txn.action ? (
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                  <p className="text-sm font-semibold text-primary">{txn.action.replace(/_/g, " ")}</p>
                  <p className="mt-1 text-sm text-muted-foreground">Final status: {txn.status}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No decision has been applied yet. Run the AI investigation to categorize this transaction.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl">
            <h3 className="text-lg font-semibold">Confirm Action</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Are you sure you want to <strong>{confirmAction.toLowerCase().replace(/_/g, " ")}</strong> this transaction?
            </p>
            <p className="mt-1 text-xs text-amber-400">Demo action — no real payment is processed.</p>
            <div className="mt-6 flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setConfirmAction(null)}>Cancel</Button>
              <Button variant="destructive" onClick={() => executeAction(confirmAction)}>Confirm</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, highlight }: { icon: React.ElementType; label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="h-4 w-4 text-muted-foreground mt-0.5" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={cn("text-sm font-medium", highlight && "text-lg font-bold")}>{value}</p>
      </div>
    </div>
  );
}

function ScoreRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border/50 pb-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-sm font-semibold mb-2">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
            <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
