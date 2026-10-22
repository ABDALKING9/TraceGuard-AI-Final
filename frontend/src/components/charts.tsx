import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ActivityBucket, PlatformSlice, RiskSlice } from "../api/types";
import { Empty } from "./ui";

export const RISK_COLORS: Record<string, string> = {
  Low: "#2f9e73",
  Moderate: "#e0a92e",
  Elevated: "#e07a3c",
  High: "#d3455a",
};

export const RISK_ORDER = ["Low", "Moderate", "Elevated", "High"];

const PLATFORM_COLORS: Record<string, string> = {
  Telegram: "#526ee8",
  WhatsApp: "#22a06b",
  Instagram: "#d65b91",
};

export function RiskDistributionChart({ data }: { data: RiskSlice[] }) {
  const hasData = data.some((slice) => slice.count > 0);
  if (!hasData) {
    return <Empty text="No analysed records yet. Load demo data to populate this chart." />;
  }
  const ordered = RISK_ORDER.map((category) => data.find((slice) => slice.category === category) ?? {
    category,
    count: 0,
  });
  return (
    <div className="chart-wrap" data-testid="risk-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={ordered}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7ebf1" />
          <XAxis dataKey="category" axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "#f5f7fb" }} />
          <Bar dataKey="count" name="Records" radius={[5, 5, 0, 0]}>
            {ordered.map((slice) => (
              <Cell key={slice.category} fill={RISK_COLORS[slice.category] ?? "#5577e8"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PlatformComparisonChart({
  records,
  accounts,
}: {
  records: PlatformSlice[];
  accounts: PlatformSlice[];
}) {
  const hasData = records.some((slice) => slice.count > 0);
  if (!hasData) return <Empty text="No records yet. Load demo data to populate this chart." />;
  const accountLookup = new Map(accounts.map((slice) => [slice.platform, slice.count]));
  const merged = records.map((slice) => ({
    platform: slice.platform,
    records: slice.count,
    accounts: accountLookup.get(slice.platform) ?? 0,
  }));
  return (
    <div className="chart-wrap" data-testid="platform-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={merged} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7ebf1" />
          <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="platform" width={78} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "#f5f7fb" }} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 10 }} />
          <Bar dataKey="records" name="Records" radius={[0, 5, 5, 0]}>
            {merged.map((slice) => (
              <Cell key={slice.platform} fill={PLATFORM_COLORS[slice.platform] ?? "#5577e8"} />
            ))}
          </Bar>
          <Bar dataKey="accounts" name="Accounts" fill="#c9d2e8" radius={[0, 5, 5, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActivityChart({
  buckets,
  interval,
}: {
  buckets: ActivityBucket[];
  interval: string;
}) {
  if (!buckets.length) {
    return <Empty text="No record activity in this window yet." />;
  }
  const label = (bucket: string) =>
    interval === "week" ? bucket : bucket.slice(5);
  return (
    <div className="chart-wrap chart-wrap-tall" data-testid="activity-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={buckets} margin={{ left: -18, right: 12, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5577e8" stopOpacity={0.42} />
              <stop offset="100%" stopColor="#5577e8" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7ebf1" />
          <XAxis
            dataKey="bucket"
            tickFormatter={label}
            interval="preserveStartEnd"
            minTickGap={18}
            axisLine={false}
            tickLine={false}
            fontSize={10}
          />
          <YAxis allowDecimals={false} axisLine={false} tickLine={false} fontSize={10} />
          <Tooltip
            labelFormatter={(value: string) => value}
            formatter={(value: number) => [`${value} records`, "Volume"]}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#5577e8"
            strokeWidth={2}
            fill="url(#activityFill)"
            name="Records"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
