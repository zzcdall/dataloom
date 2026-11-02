import * as echarts from "echarts/core";
import { BarChart, BoxplotChart, LineChart, ScatterChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";
import { formatNumber } from "../format";

echarts.use([
  BarChart,
  BoxplotChart,
  LineChart,
  ScatterChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
]);

type ChartInstance = ReturnType<typeof echarts.init>;

interface ChartProps {
  option: Record<string, unknown> | null;
  height?: number;
  className?: string;
}

export function Chart({ option, height = 260, className = "" }: ChartProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ChartInstance | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    if (option) {
      const prepared = JSON.parse(JSON.stringify(option)) as Record<string, any>;
      if (Array.isArray(prepared.series)) {
        for (const series of prepared.series) {
          if (series?.label?.formatter === "{c}") {
            series.label.formatter = (params: { value: unknown }) => formatNumber(params.value);
          }
        }
      }
      for (const axis of [prepared.xAxis, prepared.yAxis]) {
        if (axis?.type === "value" && axis.axisLabel) {
          axis.axisLabel.formatter = (value: number) => formatNumber(value);
        }
      }
      chartRef.current.setOption(prepared, { notMerge: true });
    } else {
      chartRef.current.clear();
    }
  }, [option]);

  return <div ref={ref} className={`chart-canvas ${className}`} style={{ height }} />;
}

