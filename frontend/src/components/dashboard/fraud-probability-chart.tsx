"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface FraudProbBucket {
  bucket: string;
  count: number;
}

export function FraudProbabilityChart({ data }: { data: FraudProbBucket[] }) {
  if (!data.length || data.every((d) => d.count === 0)) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Fraud Probability Distribution</CardTitle></CardHeader>
        <CardContent className="h-64 flex items-center justify-center text-sm text-muted-foreground">
          No analyzed transactions yet — run risk analysis to populate this chart.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Fraud Probability Distribution</CardTitle></CardHeader>
      <CardContent className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="bucket" stroke="hsl(var(--muted-foreground))" fontSize={11} />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
            <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Transactions" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
