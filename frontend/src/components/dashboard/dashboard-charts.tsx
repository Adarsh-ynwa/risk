"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RiskSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

const RISK_COLORS: Record<string, string> = {
  LOW: "#22c55e",
  MEDIUM: "#eab308",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};

export function DashboardCharts({ summary }: { summary: RiskSummary }) {
  const riskData = Object.entries(summary.risk_distribution).map(([name, value]) => ({ name, value }));
  const fraudData = [
    { name: "Fraud", value: summary.fraud_vs_legitimate.fraud || 0 },
    { name: "Legitimate", value: summary.fraud_vs_legitimate.legitimate || 0 },
  ];
  const amountData = Object.entries(summary.amount_at_risk_by_level).map(([name, value]) => ({
    name,
    amount: value,
  }));

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      <Card className="md:col-span-1">
        <CardHeader><CardTitle className="text-base">Risk Distribution</CardTitle></CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {riskData.map((e) => (
                  <Cell key={e.name} fill={RISK_COLORS[e.name] || "#64748b"} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="md:col-span-1">
        <CardHeader><CardTitle className="text-base">Fraud vs Legitimate</CardTitle></CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={fraudData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Bar dataKey="value" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="md:col-span-1">
        <CardHeader><CardTitle className="text-base">Amount at Risk by Level</CardTitle></CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={amountData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                {amountData.map((e) => (
                  <Cell key={e.name} fill={RISK_COLORS[e.name] || "#64748b"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader><CardTitle className="text-base">Risk Trend Over Time</CardTitle></CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={summary.risk_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={10} tickFormatter={(d) => d.slice(5)} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Line type="monotone" dataKey="avg_risk_score" stroke="#3b82f6" strokeWidth={2} dot={false} name="Avg Risk Score" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="md:col-span-1">
        <CardHeader><CardTitle className="text-base">Fraud by Merchant Category</CardTitle></CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summary.fraud_by_category.slice(0, 6)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis type="category" dataKey="category" stroke="hsl(var(--muted-foreground))" fontSize={10} width={90} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
              <Bar dataKey="count" fill="#f97316" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
