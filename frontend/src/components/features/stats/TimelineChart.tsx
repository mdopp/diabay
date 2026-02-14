import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { HourlyCount } from '@/types/stats'

interface TimelineChartProps {
  data: HourlyCount[]
}

/**
 * Timeline chart showing hourly processing counts for the last 48 hours
 */
export function TimelineChart({ data }: TimelineChartProps) {
  // Show only every 4th hour label to avoid crowding
  const tickFormatter = (value: string, index: number) => {
    return index % 4 === 0 ? value : ''
  }

  // Calculate max value for Y-axis
  const maxCount = Math.max(...data.map((d) => d.count), 1)
  const yAxisMax = Math.ceil(maxCount * 1.2) // Add 20% padding

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Timeline</CardTitle>
        <CardDescription>Images processed per hour (last 48 hours)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="hour"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                tickFormatter={tickFormatter}
                stroke="hsl(var(--border))"
              />
              <YAxis
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                stroke="hsl(var(--border))"
                domain={[0, yAxisMax]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
                cursor={{ fill: 'hsl(var(--accent) / 0.1)' }}
              />
              <Bar
                dataKey="count"
                fill="hsl(var(--accent))"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {data.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Total (48h)</p>
              <p className="font-semibold text-lg">{data.reduce((sum, d) => sum + d.count, 0)}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Peak Hour</p>
              <p className="font-semibold text-lg">
                {Math.max(...data.map((d) => d.count))} images
              </p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Average/Hour</p>
              <p className="font-semibold text-lg">
                {(data.reduce((sum, d) => sum + d.count, 0) / 48).toFixed(1)}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
