import type { ColumnKind } from "../types";
import { formatNumber, kindLabel } from "../format";

interface DataTableProps {
  columns: { name: string; kind?: ColumnKind }[];
  rows: Record<string, unknown>[];
  maxHeight?: number;
  dense?: boolean;
}

function cellText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  return text.length > 140 ? `${text.slice(0, 140)}…` : text;
}

export function DataTable({ columns, rows, maxHeight = 460, dense = false }: DataTableProps) {
  if (!columns.length) return null;
  return (
    <div className="table-shell" style={{ maxHeight }}>
      <table className={`data-table ${dense ? "dense" : ""}`}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.name}>
                <span className="th-inner">
                  {column.name}
                  {column.kind ? <span className={`kind-dot kind-${column.kind}`} title={kindLabel(column.kind)} /> : null}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => {
                const text = cellText(row[column.name]);
                return (
                  <td key={column.name} title={text}>
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length ? <div className="table-empty">没有可展示的数据</div> : null}
    </div>
  );
}

