import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi, DayBookEntry, PnlReport } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import AnimatedStat from "../../components/motion/AnimatedStat";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./store-theme.css";
import "../../components/CsvUpload.css";

type Tab = "financial" | "import";

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>("financial");
  const [pnl, setPnl] = useState<PnlReport | null>(null);
  const [daybook, setDaybook] = useState<DayBookEntry[]>([]);
  const [daybookDate, setDaybookDate] = useState(new Date().toISOString().slice(0, 10));
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (tab === "financial") {
      storeApi.getPnl().then(setPnl);
      storeApi.getDayBook(daybookDate).then((r) => setDaybook(r.entries));
    }
  }, [tab, daybookDate]);

  const handleExport = async () => {
    const result = await storeApi.exportReport();
    setExportUrl(result.download_url);
  };

  const upload = async (file: File) => {
    setLoading(true);
    setImportStatus(null);
    try {
      const result = await storeApi.importCsv(file);
      setImportStatus(`Imported ${result.imported} transactions.`);
    } catch {
      setImportStatus("Import failed. Check CSV format.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell {...STORE_SHELL} title="Reports" subtitle="Financial summaries and data import/export">
      <div className="tab-bar">
        <button
          type="button"
          className={`tab-bar-item${tab === "financial" ? " active" : ""}`}
          onClick={() => setTab("financial")}
        >
          {tab === "financial" && (
            <motion.span layoutId="reports-tab" className="tab-indicator" transition={{ type: "spring", stiffness: 380, damping: 30 }} />
          )}
          Financial
        </button>
        <button
          type="button"
          className={`tab-bar-item${tab === "import" ? " active" : ""}`}
          onClick={() => setTab("import")}
        >
          {tab === "import" && (
            <motion.span layoutId="reports-tab" className="tab-indicator" transition={{ type: "spring", stiffness: 380, damping: 30 }} />
          )}
          Import / Export
        </button>
      </div>

      {tab === "financial" && (
        <>
          <StaggerGrid className="admin-grid-4">
            <StaggerItem>
              <div className="admin-stat-card">
                <div className="admin-stat-label">Revenue ({pnl?.from} – {pnl?.to})</div>
                <AnimatedStat value={pnl?.revenue ?? 0} prefix="₹" />
              </div>
            </StaggerItem>
            <StaggerItem>
              <div className="admin-stat-card">
                <div className="admin-stat-label">COGS</div>
                <AnimatedStat value={pnl?.cogs ?? 0} prefix="₹" />
              </div>
            </StaggerItem>
            <StaggerItem>
              <div className="admin-stat-card">
                <div className="admin-stat-label">Gross margin</div>
                <AnimatedStat value={pnl?.gross_margin ?? 0} prefix="₹" />
                <small style={{ color: "var(--text-muted)" }}>{pnl?.margin_pct ?? 0}%</small>
              </div>
            </StaggerItem>
            <StaggerItem>
              <div className="admin-stat-card">
                <div className="admin-stat-label">GST collected</div>
                <AnimatedStat value={pnl?.tax_collected ?? 0} prefix="₹" />
              </div>
            </StaggerItem>
          </StaggerGrid>
          <div style={{ marginBottom: "1rem" }} />

          <AnimatedPanel className="admin-card store-table-wrap">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <div className="admin-card-title" style={{ margin: 0 }}>Day book</div>
              <input
                type="date"
                className="admin-input"
                value={daybookDate}
                onChange={(e) => setDaybookDate(e.target.value)}
              />
            </div>
            <table className="admin-table admin-table-modern">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Debit</th>
                  <th>Credit</th>
                </tr>
              </thead>
              <AnimatedTableBody dataKey={`${daybookDate}-${daybook.length}`}>
                {daybook.map((e, i) => (
                  <AnimatedTableRow key={i} index={i}>
                    <td>{new Date(e.time).toLocaleTimeString()}</td>
                    <td>{e.type}</td>
                    <td>{e.description}</td>
                    <td className="gst-mono">{e.debit ? `₹${e.debit}` : "—"}</td>
                    <td className="gst-mono">{e.credit ? `₹${e.credit}` : "—"}</td>
                  </AnimatedTableRow>
                ))}
              </AnimatedTableBody>
            </table>
            {daybook.length === 0 && <div className="admin-empty-state">No entries for this date.</div>}
          </AnimatedPanel>
        </>
      )}

      {tab === "import" && (
        <StaggerGrid className="admin-grid-2">
          <StaggerItem>
          <AnimatedPanel>
            <div className="admin-card-title">Export forecast report</div>
            <p style={{ color: "var(--text-muted)", marginBottom: "0.75rem" }}>
              Download Prophet forecasts for all SKUs as CSV.
            </p>
            <button type="button" className="admin-btn admin-btn-primary" onClick={handleExport}>
              Generate export
            </button>
            {exportUrl && (
              <a href={exportUrl} target="_blank" rel="noreferrer" className="admin-btn admin-btn-ghost" style={{ marginLeft: 8 }}>
                Download CSV
              </a>
            )}
          </AnimatedPanel>
          </StaggerItem>
          <StaggerItem>
          <AnimatedPanel>
            <div className="admin-card-title">Import POS transactions</div>
            <div
              className="drop-zone"
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) upload(file);
              }}
            >
              <p>Drop CSV here or click to browse</p>
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) upload(file);
                }}
              />
            </div>
            {loading && <p>Importing…</p>}
            {importStatus && <p className="admin-job-msg">{importStatus}</p>}
          </AnimatedPanel>
          </StaggerItem>
        </StaggerGrid>
      )}
    </AppShell>
  );
}
