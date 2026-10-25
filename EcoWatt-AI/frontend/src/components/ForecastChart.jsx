import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatUkAxisTick, formatUkTooltip } from "../lib/time.js";

export function ChartTooltip({ active, payload, source }) {
  if (!active || !payload?.length) {
    return null;
  }
  const point = payload[0].payload;
  const stamp = formatUkTooltip(point.time, point.end);
  return (
    <div className="chart-tooltip" role="tooltip">
      <strong>{stamp.date}</strong>
      <div>{stamp.start} – {stamp.end}</div>
      <div>{stamp.zone}</div>
      <div>{point.intensity} gCO2/kWh</div>
      <div className="fine">{source}</div>
    </div>
  );
}

export default function ForecastChart({ points, source }) {
  const lowest = points.find((point) => point.isLowest);

  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 16, right: 12, left: 0, bottom: 8 }}>
          <defs>
            <linearGradient id="intensityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#007AFF" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#16A085" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(23,25,29,0.06)" vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={formatUkAxisTick}
            minTickGap={56}
            tick={{ fill: "#667085", fontSize: 12 }}
            interval="preserveStartEnd"
          />
          <YAxis
            unit=" g"
            tick={{ fill: "#667085", fontSize: 12 }}
            width={56}
          />
          <Tooltip content={<ChartTooltip source={source} />} />
          <Area
            type="monotone"
            dataKey="intensity"
            stroke="#007AFF"
            fill="url(#intensityFill)"
            strokeWidth={3}
            name="Carbon intensity"
          />
          {lowest && (
            <ReferenceDot
              x={lowest.time}
              y={lowest.intensity}
              r={5}
              fill="#16a085"
              stroke="#fff"
              strokeWidth={2}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
