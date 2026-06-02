import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { storeApi } from "../../../api/store";
import "../../../components/HeatmapChart.css";

const COLORS = ["#1e2a4a", "#2c3f70", "#3d5599", "#4f7cff", "#6b93ff", "#8aacff"];

export default function StoreHeatmap() {
  const [data, setData] = useState<{ category: string; hours: { hour: number; value: number }[] }[]>([]);
  const [activeCategory, setActiveCategory] = useState(0);

  useEffect(() => {
    storeApi.getHeatmap().then((res) => {
      setData(res.heatmap as { category: string; hours: { hour: number; value: number }[] }[]);
    });
  }, []);

  const chartData = useMemo(() => {
    if (!data.length) return [];
    const cat = data[activeCategory];
    const maxVal = Math.max(...cat.hours.map((h) => h.value), 1);
    return cat.hours.map((h) => ({
      hour: `${h.hour}:00`,
      value: h.value,
      intensity: h.value / maxVal,
    }));
  }, [data, activeCategory]);

  const getColor = (intensity: number) => {
    const idx = Math.min(Math.floor(intensity * (COLORS.length - 1)), COLORS.length - 1);
    return COLORS[idx];
  };

  if (!data.length) {
    return <p className="heatmap-empty">Loading purchase patterns…</p>;
  }

  return (
    <motion.div className="heatmap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
      <div className="category-tabs">
        {data.map((cat, i) => (
          <button
            key={cat.category}
            type="button"
            className={`cat-tab ${i === activeCategory ? "active" : ""}`}
            onClick={() => setActiveCategory(i)}
          >
            {cat.category}
          </button>
        ))}
      </div>
      <div className="heatmap-chart">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#9aa3b8" }} interval={2} />
            <YAxis tick={{ fontSize: 10, fill: "#9aa3b8" }} />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              contentStyle={{
                background: "rgba(20, 26, 45, 0.92)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 10,
                fontSize: 12,
              }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={getColor(entry.intensity)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
