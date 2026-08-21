import { BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { FraudProbabilityChart } from "@/components/dashboard/fraud-probability-chart";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default async function AnalyticsPage() {
  let analytics: Awaited<ReturnType<typeof api.analytics>> | null = null;

  try {
    analytics = await api.analytics();
  } catch {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-8 text-center">
        <p className="text-destructive font-semibold">Backend unavailable</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Start the API: <code className="text-primary">uvicorn app.main:app --reload --port 8000</code>
        </p>
      </div>
    );
  }

  const { stats, risk_summary: summary, fraud_probability_distribution } = analytics;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <BarChart3 className="h-8 w-8 text-primary" />
          Analytics
        </h1>
        <p className="text-muted-foreground">Risk and fraud analytics from live backend data</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Total Transactions" value={stats.total_transactions.toLocaleString()} icon={BarChart3} />
        <KpiCard title="Fraud Rate" value={`${stats.fraud_detection_rate}%`} icon={BarChart3} accent="bg-red-500/10 text-red-400" />
        <KpiCard title="Amount at Risk" value={formatCurrency(stats.amount_at_risk)} icon={BarChart3} accent="bg-amber-500/10 text-amber-400" />
        <KpiCard title="Critical Cases" value={stats.critical_transactions} icon={BarChart3} accent="bg-orange-500/10 text-orange-400" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-base">International Fraud</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold">{analytics.international_fraud_count}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Night Transaction Fraud</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold">{analytics.night_transaction_fraud_count}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Failed Attempt Correlation</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold">{analytics.failed_attempt_fraud_count}</p></CardContent>
        </Card>
      </div>

      <FraudProbabilityChart data={fraud_probability_distribution} />

      <Card>
        <CardHeader><CardTitle className="text-base">Top Fraud Merchant Categories</CardTitle></CardHeader>
        <CardContent>
          {summary.fraud_by_category.length ? (
            <ul className="space-y-2">
              {summary.fraud_by_category.slice(0, 8).map(({ category, count }) => (
                <li key={category} className="flex justify-between text-sm border-b border-border/40 pb-2">
                  <span>{category}</span>
                  <span className="font-semibold text-red-400">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No fraud data available yet.</p>
          )}
        </CardContent>
      </Card>

      <DashboardCharts summary={summary} />
    </div>
  );
}
