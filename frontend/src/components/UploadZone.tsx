import { FileSpreadsheet, Loader2, Sparkles, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

interface UploadZoneProps {
  onFile: (file: File) => void;
  onDemo: () => void;
  loading?: boolean;
  compact?: boolean;
}

export function UploadZone({ onFile, onDemo, loading = false, compact = false }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function accept(file: File | undefined) {
    if (file) onFile(file);
  }

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""} ${compact ? "compact" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        accept(event.dataTransfer.files?.[0]);
      }}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.tsv,.xlsx"
        hidden
        onChange={(event) => {
          accept(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <div className="upload-icon">
        {loading ? <Loader2 size={22} className="spin" /> : <UploadCloud size={22} />}
      </div>
      <div className="upload-copy">
        <strong>{loading ? "正在分析数据…" : "拖拽 CSV / Excel 到这里"}</strong>
        <span>或点击选择文件 · 支持 .csv / .tsv / .xlsx · 最大 100 MB</span>
      </div>
      <button
        type="button"
        className="btn btn-ghost upload-demo"
        disabled={loading}
        onClick={(event) => {
          event.stopPropagation();
          onDemo();
        }}
      >
        <Sparkles size={14} />
        加载示例数据
      </button>
      <div className="upload-foot">
        <span><FileSpreadsheet size={13} /> 自动识别编码、分隔符与字段类型</span>
        <span>数据只在本地处理</span>
      </div>
    </div>
  );
}

