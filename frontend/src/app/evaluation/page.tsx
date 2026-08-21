import { AlertTriangle, CheckCircle, IndianRupee, Target } from "lucide-react";
import { api } from "@/lib/api";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

export default async function EvaluationPage() {
  let metrics;
  try {
    metrics = await api.modelMetrics();
  } catch {
    return <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-8">Model metrics are unavailable. Start the backend and train the model.</div>;
  }
  const hybrid = metrics.hybrid_test_metrics || {};
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Held-out Evaluation</h1>
        <p className="text-muted-foreground">Honest fraud performance and merchant-cost trade-offs on {metrics.test_size.toLocaleString()} untouched transactions.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Precision" value={pct(metrics.precision)} subtitle="Alerts that were actual fraud" icon={Target} />
        <KpiCard title="Recall" value={pct(metrics.recall)} subtitle="Total fraud successfully caught" icon={CheckCircle} />
        <KpiCard title="False Positives" value={metrics.false_positives.toLocaleString()} subtitle="Legitimate payments flagged" icon={AlertTriangle} accent="bg-amber-500/10 text-amber-400" />
        <KpiCard title="Estimated Cost" value={`₹${metrics.estimated_total_cost_inr.toLocaleString("en-IN")}`} subtitle="Illustrative scenario, not merchant financials" icon={IndianRupee} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Confusion Matrix</CardTitle><CardDescription>What the model got right and wrong at the selected {pct(metrics.threshold)} threshold.</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-center">
            <MatrixCell label="Legitimate allowed" value={metrics.true_negatives} tone="green" />
            <MatrixCell label="Legitimate flagged" value={metrics.false_positives} tone="amber" />
            <MatrixCell label="Fraud missed" value={metrics.false_negatives} tone="red" />
            <MatrixCell label="Fraud caught" value={metrics.true_positives} tone="green" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Model vs Deployed Hybrid</CardTitle><CardDescription>The rules reduce alert volume but currently sacrifice fraud coverage.</CardDescription></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm"><thead className="text-muted-foreground"><tr><th className="py-2 text-left">System</th><th>Precision</th><th>Recall</th><th>False alerts</th></tr></thead>
              <tbody><tr className="border-t"><td className="py-3">Cost-selected ML</td><td className="text-center">{pct(metrics.precision)}</td><td className="text-center">{pct(metrics.recall)}</td><td className="text-center">{metrics.false_positives.toLocaleString()}</td></tr>
              <tr className="border-t"><td className="py-3">ML + rules HIGH boundary</td><td className="text-center">{pct(hybrid.precision || 0)}</td><td className="text-center">{pct(hybrid.recall || 0)}</td><td className="text-center">{(hybrid.false_positives || 0).toLocaleString()}</td></tr></tbody>
            </table>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle>Validation Threshold Comparison</CardTitle><CardDescription>The threshold was chosen on validation data only. The test set above remained untouched.</CardDescription></CardHeader>
        <CardContent className="overflow-x-auto"><table className="w-full text-sm"><thead className="text-muted-foreground"><tr><th className="py-2 text-left">Threshold</th><th>Precision</th><th>Recall</th><th>Alert rate</th><th>FP</th><th>FN</th><th>Estimated cost</th></tr></thead>
          <tbody>{metrics.validation_threshold_comparison.map((row) => <tr className="border-t" key={row.threshold}><td className="py-3 font-medium">{pct(row.threshold)}</td><td className="text-center">{pct(row.precision)}</td><td className="text-center">{pct(row.recall)}</td><td className="text-center">{pct(row.alert_rate)}</td><td className="text-center">{row.false_positives.toLocaleString()}</td><td className="text-center">{row.false_negatives.toLocaleString()}</td><td className="text-right">₹{row.estimated_total_cost_inr.toLocaleString("en-IN")}</td></tr>)}</tbody>
        </table></CardContent>
      </Card>
      <p className="text-xs text-muted-foreground">Cost assumptions: ₹{metrics.cost_assumptions_inr.false_positive?.toLocaleString("en-IN")} per false positive and ₹{metrics.cost_assumptions_inr.false_negative?.toLocaleString("en-IN")} per missed fraud. Replace these illustrative values with merchant-specific economics.</p>
    </div>
  );
}

function MatrixCell({ label, value, tone }: { label: string; value: number; tone: "green" | "amber" | "red" }) {
  const colors = { green: "border-green-500/30 bg-green-500/10", amber: "border-amber-500/30 bg-amber-500/10", red: "border-red-500/30 bg-red-500/10" };
  return <div className={`rounded-lg border p-5 ${colors[tone]}`}><p className="text-2xl font-bold">{value.toLocaleString()}</p><p className="text-xs text-muted-foreground">{label}</p></div>;
}
