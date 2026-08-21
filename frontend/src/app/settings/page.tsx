import { Settings, Shield, Bot, Database, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";

export default async function SettingsPage() {
  let metrics: Record<string, unknown> = {};
  let health: { model_loaded: boolean; groq_configured: boolean } = { model_loaded: false, groq_configured: false };

  try {
    [metrics, health] = await Promise.all([api.modelMetrics(), api.health()]);
  } catch {
    /* use defaults */
  }

  const thresholds = [
    { level: "LOW", range: "0 – 29", color: "text-risk-low" },
    { level: "MEDIUM", range: "30 – 59", color: "text-risk-medium" },
    { level: "HIGH", range: "60 – 79", color: "text-risk-high" },
    { level: "CRITICAL", range: "80 – 100", color: "text-risk-critical" },
  ];

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Settings className="h-8 w-8 text-primary" />
          Settings
        </h1>
        <p className="text-muted-foreground">System configuration and demo information</p>
      </div>

      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
        <p className="text-sm text-amber-200/90">
          Demo environment — no real payments are processed. This is an experimental AI-powered payment risk management prototype inspired by modern payment infrastructure.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Shield className="h-5 w-5" /> Risk Thresholds</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {thresholds.map((t) => (
            <div key={t.level} className="flex justify-between items-center border-b border-border/50 pb-2">
              <span className={`font-semibold ${t.color}`}>{t.level}</span>
              <span className="text-sm text-muted-foreground">{t.range}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5" /> System Components</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Row label="ML Model" value={String(metrics.model_type || "XGBoost")} status={health.model_loaded ? "Loaded" : "Not loaded"} />
          <Row label="AI Agent" value="Groq · Llama 3.3 70B" status={health.groq_configured ? "Configured" : "Fallback mode"} />
          <Row label="Dataset" value="Synthetic Banking Fraud Dataset" status="Demo" />
          <Row label="Database" value="SQLite" status="Local" />
          {metrics.f1 != null && (
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground mb-2">Model Metrics (test set)</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <span>F1: {Number(metrics.f1).toFixed(3)}</span>
                <span>ROC-AUC: {Number(metrics.roc_auc).toFixed(3)}</span>
                <span>Precision: {Number(metrics.precision).toFixed(3)}</span>
                <span>Recall: {Number(metrics.recall).toFixed(3)}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Database className="h-5 w-5" /> Scoring Formula</CardTitle>
          <CardDescription>Hybrid ML + Rules risk engine</CardDescription>
        </CardHeader>
        <CardContent className="font-mono text-sm space-y-2 text-muted-foreground">
          <p>ml_score = fraud_probability × 100</p>
          <p>final_risk_score = 0.60 × ml_score + 0.40 × rule_score</p>
          <p className="text-xs pt-2">Rule score capped at 100. Agent investigates HIGH/CRITICAL cases only.</p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value, status }: { label: string; value: string; status: string }) {
  return (
    <div className="flex justify-between items-center">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{value}</p>
      </div>
      <span className="text-xs rounded-full bg-muted px-2.5 py-1">{status}</span>
    </div>
  );
}
