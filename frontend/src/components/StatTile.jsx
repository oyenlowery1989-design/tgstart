export default function StatTile({ label, value }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded px-4 py-3 flex-1">
      <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className="text-2xl font-semibold text-slate-100">{value}</div>
    </div>
  );
}
