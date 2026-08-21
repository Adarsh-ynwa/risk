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
  History,
  TrendingDown,
  TrendingUp,
  KeyRound,
  Ban,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RiskBadge, RiskScoreRing, formatCurrency } from "@/components/dashboard/kpi-card";
import { showToast } from "@/components/ui/toaster";
import { api, type CustomerBehavior, type InvestigationReport, type TimelineEvent, type TransactionDetail, type UnblockRequest, type Verification } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function TransactionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string>("");
  const [txn, setTxn] = useState<TransactionDetail | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [investigating, setInvestigating] = useState(false);
  const [behavior, setBehavior] = useState<CustomerBehavior | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [verificationBusy, setVerificationBusy] = useState(false);
  const [showBlockApproval, setShowBlockApproval] = useState(false);
  const [blockDecisionBusy, setBlockDecisionBusy] = useState(false);
  const [unblockRequest, setUnblockRequest] = useState<UnblockRequest | null>(null);
  const [unblockReason, setUnblockReason] = useState("");
  const [unblockBusy, setUnblockBusy] = useState(false);
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
      const [behaviorResult, timelineResult, verificationResults, unblockResults] = await Promise.all([
        api.behavior(id).catch(() => null),
        api.timeline(id).catch(() => []),
        api.verifications(id).catch(() => []),
        api.unblockRequests(id).catch(() => []),
      ]);
      setBehavior(behaviorResult);
      setTimeline(timelineResult);
      setVerification(verificationResults.find((item) => item.status === "PENDING") ?? verificationResults[0] ?? null);
      setUnblockRequest(unblockResults.find((item) => item.status === "PENDING") ?? unblockResults[0] ?? null);
      try {
        const inv = await api.getInvestigation(id);
        setInvestigation(inv.investigation);
      } catch {
        setInvestigation(null);
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
      showToast({
        title: result.requires_human_approval ? "Human approval required" : "Agent decision applied",
        description: result.requires_human_approval
          ? "The agent recommends BLOCK. A human analyst must approve the final block."
          : `Agent applied ${result.action_applied?.replace(/_/g, " ") || "a decision"}.`,
      });
      await load();
      if (txn?.risk_level === "CRITICAL" || result.requires_human_approval) {
        setShowBlockApproval(true);
      }
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
      setConfirmAction(null);
      await load();
    } catch (e) {
      showToast({ title: "Action failed", description: String(e), variant: "destructive" });
    }
  };

  const decideCriticalCase = async (action: "BLOCK" | "HOLD") => {
    setBlockDecisionBusy(true);
    try {
      await executeAction(action);
      setShowBlockApproval(false);
    } finally {
      setBlockDecisionBusy(false);
    }
  };

  const submitUnblockRequest = async () => {
    if (unblockReason.trim().length < 10) {
      showToast({ title: "Reason required", description: "Enter at least 10 characters explaining why this block should be reviewed.", variant: "destructive" });
      return;
    }
    setUnblockBusy(true);
    try {
      const result = await api.requestUnblock(id, unblockReason.trim());
      setUnblockRequest(result);
      setUnblockReason("");
      showToast({ title: "Unblock review requested", description: "A senior analyst must approve or reject the request." });
      await load();
    } catch (e) { showToast({ title: "Request failed", description: String(e), variant: "destructive" }); }
    finally { setUnblockBusy(false); }
  };

  const decideUnblock = async (decision: "APPROVE" | "REJECT") => {
    if (!unblockRequest) return;
    setUnblockBusy(true);
    try {
      const result = await api.reviewUnblock(unblockRequest.id, decision);
      setUnblockRequest(result);
      showToast({ title: `Unblock ${decision === "APPROVE" ? "approved" : "rejected"}`, description: decision === "APPROVE" ? "The case moved to manual review; it was not automatically approved." : "The transaction remains blocked." });
      await load();
    } catch (e) { showToast({ title: "Review failed", description: String(e), variant: "destructive" }); }
    finally { setUnblockBusy(false); }
  };

  const requestVerification = async (method: string) => {
    setVerificationBusy(true);
    try {
      const result = await api.requestVerification(id, method);
      setVerification(result);
      showToast({ title: "Verification requested", description: `${method.replace(/_/g, " ")} is now pending.` });
      await load();
    } catch (e) {
      showToast({ title: "Verification failed", description: String(e), variant: "destructive" });
    } finally { setVerificationBusy(false); }
  };

  const resolveVerification = async (status: string) => {
    if (!verification) return;
    setVerificationBusy(true);
    try {
      const result = await api.resolveVerification(verification.id, status);
      setVerification(result);
      showToast({ title: `Verification ${status.toLowerCase()}`, description: `Transaction status updated after analyst review.` });
      await load();
    } catch (e) {
      showToast({ title: "Could not resolve verification", description: String(e), variant: "destructive" });
    } finally { setVerificationBusy(false); }
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

      {txn.risk_level === "CRITICAL" && !["BLOCKED", "UNBLOCK_PENDING"].includes(txn.status) && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-500/40 bg-red-500/10 p-4">
          <div className="flex gap-3">
            <Ban className="h-5 w-5 shrink-0 text-red-400" />
            <div><p className="font-semibold text-red-300">Critical case requires a human block decision</p><p className="text-sm text-muted-foreground">Review the AI findings and explicitly block the transaction or keep it on temporary hold.</p></div>
          </div>
          <Button variant="destructive" onClick={() => setShowBlockApproval(true)}>Review block decision</Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
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
              <CardTitle className="text-lg flex items-center gap-2"><History className="h-5 w-5 text-primary" /> Customer Behavioral Evidence</CardTitle>
              <CardDescription>Current payment compared only with this customer&apos;s earlier transactions.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {behavior ? <>
                <p className="text-xs text-muted-foreground">Baseline built from {behavior.history_count} earlier transaction{behavior.history_count === 1 ? "" : "s"}.</p>
                {behavior.signals.map((signal) => {
                  const increases = signal.impact === "INCREASES_RISK";
                  const Icon = increases ? TrendingUp : TrendingDown;
                  return <div key={signal.label} className={cn("rounded-lg border p-4", increases ? "border-red-500/25 bg-red-500/5" : "border-green-500/25 bg-green-500/5")}>
                    <div className="flex items-start gap-3"><Icon className={cn("mt-0.5 h-5 w-5 shrink-0", increases ? "text-red-400" : "text-green-400")} /><div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{signal.label}</p><span className={cn("text-xs", increases ? "text-red-400" : "text-green-400")}>{increases ? "Increases risk" : "Reduces risk"}</span></div>
                      <p className="mt-1 text-sm">{signal.current_value} <span className="text-muted-foreground">vs {signal.baseline_value}</span></p><p className="mt-1 text-xs text-muted-foreground">{signal.explanation}</p>
                    </div></div>
                  </div>;
                })}
              </> : <p className="text-sm text-muted-foreground">Behavioral evidence is unavailable.</p>}
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

          <Card className="order-5">
            <CardHeader><CardTitle className="text-lg flex items-center gap-2"><KeyRound className="h-5 w-5 text-primary" /> Verification & Human Approval</CardTitle><CardDescription>Customer confirmation and analyst-controlled resolution after the AI investigation.</CardDescription></CardHeader>
            <CardContent className="space-y-4">
              {txn.status === "BLOCKED" ? <div className="space-y-4 rounded-lg border border-red-500/30 bg-red-500/5 p-4">
                <div className="flex items-start gap-3"><Ban className="mt-0.5 h-5 w-5 shrink-0 text-red-400" /><div><p className="font-semibold text-red-300">Transaction blocked by human approval</p><p className="mt-1 text-sm text-muted-foreground">OTP cannot reverse the block. Request a separately audited senior review if the decision may be wrong.</p></div></div>
                <textarea value={unblockReason} onChange={(event) => setUnblockReason(event.target.value)} placeholder="Reason for requesting unblock review (minimum 10 characters)" className="min-h-24 w-full rounded-md border border-input bg-background p-3 text-sm" />
                <Button variant="outline" disabled={unblockBusy} onClick={submitUnblockRequest}>Request unblock review</Button>
              </div> : txn.status === "UNBLOCK_PENDING" ? <div className="space-y-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                <div><p className="font-semibold text-amber-300">Senior unblock review pending</p><p className="mt-1 text-sm text-muted-foreground">Requested by {unblockRequest?.requested_by || "Demo Analyst"}: {unblockRequest?.reason || "Reason recorded in the audit log."}</p></div>
                <div className="flex flex-wrap gap-2"><Button disabled={unblockBusy} onClick={() => decideUnblock("APPROVE")}>Approve to manual review</Button><Button variant="destructive" disabled={unblockBusy} onClick={() => decideUnblock("REJECT")}>Reject and retain block</Button></div>
              </div> : !verification || verification.status !== "PENDING" ? <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" disabled={verificationBusy} onClick={() => requestVerification("OTP")}>Request OTP</Button>
                <Button size="sm" variant="outline" disabled={verificationBusy} onClick={() => requestVerification("REGISTERED_DEVICE")}>Confirm device</Button>
                <Button size="sm" variant="outline" disabled={verificationBusy} onClick={() => requestVerification("CALLBACK")}>Request callback</Button>
              </div> : <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                <p className="font-semibold text-amber-300">{verification.method.replace(/_/g, " ")} pending</p><p className="mt-1 text-xs text-muted-foreground">An analyst records the simulated customer result.</p>
                <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" disabled={verificationBusy} onClick={() => resolveVerification("PASSED")}>Mark passed</Button><Button size="sm" variant="destructive" disabled={verificationBusy} onClick={() => resolveVerification("FAILED")}>Mark failed</Button><Button size="sm" variant="outline" disabled={verificationBusy} onClick={() => resolveVerification("EXPIRED")}>Mark expired</Button></div>
              </div>}
              <div className="space-y-0">
                {timeline.map((event, index) => <div key={`${event.timestamp}-${index}`} className="relative flex gap-3 pb-5 last:pb-0">
                  {index < timeline.length - 1 && <span className="absolute left-[7px] top-4 h-full w-px bg-border" />}<span className="relative mt-1 h-4 w-4 shrink-0 rounded-full border-2 border-primary bg-background" />
                  <div><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-semibold">{event.title}</p>{event.status && <span className="rounded bg-muted px-2 py-0.5 text-[10px]">{event.status.replace(/_/g, " ")}</span>}</div><p className="text-xs text-muted-foreground">{event.description}</p><p className="mt-1 text-[10px] text-muted-foreground">{event.actor} · {new Date(event.timestamp).toLocaleString()}</p></div>
                </div>)}
              </div>
            </CardContent>
          </Card>

          <Card className="order-4">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5 text-primary" />
                  AI Risk Investigator
                </CardTitle>
                <CardDescription>AI-driven evidence analysis completed before customer verification or analyst action</CardDescription>
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

      {showBlockApproval && txn.risk_level === "CRITICAL" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" role="dialog" aria-modal="true" aria-labelledby="block-approval-title">
          <div className="w-full max-w-lg rounded-xl border border-red-500/40 bg-card p-6 shadow-2xl">
            <div className="flex items-start gap-3"><div className="rounded-full bg-red-500/10 p-2"><Ban className="h-6 w-6 text-red-400" /></div><div><h3 id="block-approval-title" className="text-xl font-bold">Human approval required</h3><p className="mt-1 text-sm text-muted-foreground">The AI cannot permanently block this transaction on its own.</p></div></div>
            <div className="mt-5 space-y-3 rounded-lg border border-border bg-muted/20 p-4 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Transaction</span><span className="font-mono">{txn.transaction_id}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Amount</span><span className="font-semibold">{formatCurrency(txn.transaction_amount)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Risk score</span><span className="font-semibold text-red-400">{txn.risk_score?.toFixed(1)} · CRITICAL</span></div>
              {investigation && <div className="border-t border-border pt-3"><p className="text-xs text-muted-foreground">AI recommendation</p><p className="mt-1 font-semibold">{investigation.recommended_action.replace(/_/g, " ")}</p><p className="mt-1 text-xs text-muted-foreground">{investigation.recommended_action_reason}</p></div>}
            </div>
            <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200/90">Demo environment only. No real payment or customer account will be blocked.</div>
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="outline" disabled={blockDecisionBusy} onClick={() => setShowBlockApproval(false)}>Cancel</Button>
              <Button variant="outline" disabled={blockDecisionBusy} onClick={() => decideCriticalCase("HOLD")}>Keep on temporary hold</Button>
              <Button variant="destructive" disabled={blockDecisionBusy} onClick={() => decideCriticalCase("BLOCK")}>{blockDecisionBusy ? "Applying decision…" : "Approve block"}</Button>
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
