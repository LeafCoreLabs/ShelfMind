/** Renders structured report / query data in chat messages. */

interface Props {
  data: Record<string, unknown>;
}

function formatCell(value: unknown): string {
  if (typeof value === "number") {
    return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }
  return String(value ?? "");
}

export default function ChatDataBlock({ data }: Props) {
  const title = typeof data.title === "string" ? data.title : undefined;
  const summary = typeof data.summary === "string" ? data.summary : undefined;
  const arrayKey =
    Array.isArray(data.items) && data.items.length > 0
      ? "items"
      : Object.keys(data).find(
          (k) => Array.isArray(data[k]) && (data[k] as unknown[]).length > 0
        );
  if (!arrayKey) {
    if (summary) return <p className="chat-report-summary">{summary}</p>;
    return null;
  }

  const items = (data[arrayKey] as Record<string, unknown>[]).slice(0, 12);
  const cols = Object.keys(items[0]).filter((k) => typeof items[0][k] !== "object");
  if (cols.length === 0) return null;

  return (
    <div className="chat-report-block">
      {title && <div className="chat-report-title">{title}</div>}
      {summary && <p className="chat-report-summary">{summary}</p>}
      <table className="chat-data-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c.replace(/_/g, " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{formatCell(item[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
