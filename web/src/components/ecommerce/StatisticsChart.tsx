import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import { useTranslation } from "react-i18next";

interface DailyEvaluationData {
  channel: string;
  dates: string[];   // ISO: 'YYYY-MM-DD'
  values: number[];
}

function buildPalette(n: number) {
  // Cores HSL igualmente espaçadas → não se repetem dentro do conjunto atual
  if (n <= 0) return ["hsl(220,70%,55%)"];
  return Array.from({ length: n }, (_, i) => {
    const hue = Math.round((360 / n) * i);
    return `hsl(${hue}, 70%, 50%)`;
  });
}

export default function StatisticsChart({ data }: { data: DailyEvaluationData[] }) {
  const { t } = useTranslation();

  const series = data.map((item) => ({
    name: item.channel,
    data: item.dates.map((dateStr, idx) => ({
      x: new Date(dateStr).getTime(),
      y: item.values[idx] ?? 0,
    })),
  }));

  const colors = buildPalette(series.length);

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
      // TIPOS COMPATÍVEIS: use "size" ao invés de width/height
      markers: { size: 10, strokeWidth: 0 },
    },
    colors,
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 310,
      type: "line",
      toolbar: { show: false },
      // Evita o warning de "easing"
      animations: { enabled: true, speed: 500 },
    },
    stroke: {
      curve: "straight",
      width: 2,
    },
    markers: {
      size: 0,
      strokeColors: "#fff",
      strokeWidth: 2,
      hover: { size: 5 },
    },
    fill: { type: "solid", opacity: 1 },
    grid: {
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
    },
    dataLabels: { enabled: false },
    tooltip: {
      enabled: true,
      x: { format: "dd MMM yyyy" },
    },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeFormatter: {
          year: "yyyy",
          month: "MMM yyyy",
          day: "dd MMM",
          hour: "HH:mm",
        },
      },
      axisBorder: { show: false },
      axisTicks: { show: false },
      tooltip: { enabled: false },
    },
    yaxis: {
      labels: { style: { fontSize: "12px", colors: ["#6B7280"] } },
      title: { text: "", style: { fontSize: "0px" } },
      min: 0,
      forceNiceScale: true,
    },
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-5 pb-5 pt-5 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6 sm:pt-6">
      <div className="flex flex-col gap-5 mb-6 sm:flex-row sm:justify-between">
        <div className="w-full">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            {t("dashboard.statistics.title")}
          </h3>
          <p className="mt-1 text-gray-500 text-theme-sm dark:text-gray-400">
            {t("dashboard.statistics.subtitle")}
          </p>
        </div>
      </div>

      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <div className="min-w-[1000px] xl:min-w-full">
          <Chart options={options} series={series} type="line" height={310} />
        </div>
      </div>
    </div>
  );
}
