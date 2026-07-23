import { useState, useMemo } from 'react'
import { Search, ChevronDown } from 'lucide-react'

// ─── Types ──────────────────────────────────────────────────────────────────
// Matches the shape returned by POST /api/summarize and consumed by
// POST /api/tables_excel — one shared structure for viewing AND exporting.

interface SummaryRow {
  key?: string
  description?: string
  values: any[]
}

interface SummarySubcategory {
  name: string
  rows: SummaryRow[]
}

interface SummaryCategory {
  name: string
  rows?: SummaryRow[]
  subcategories?: SummarySubcategory[]
}

interface SummarySection {
  heading: string
  categories: SummaryCategory[]
}

export interface SummaryData {
  columns: string[]
  sections: SummarySection[]
}

interface TableEntry {
  id: string
  label: string
  rows: SummaryRow[]
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function flattenTables(summary: SummaryData | null): TableEntry[] {
  if (!summary) return []
  const out: TableEntry[] = []
  let idx = 0
  for (const section of summary.sections || []) {
    for (const cat of section.categories || []) {
      if (cat.subcategories && cat.subcategories.length) {
        for (const sub of cat.subcategories) {
          out.push({ id: `t${idx++}`, label: `${cat.name} - ${sub.name}`.replace(/ - $/, ''), rows: sub.rows || [] })
        }
      } else {
        out.push({ id: `t${idx++}`, label: cat.name || section.heading || `Table ${idx}`, rows: cat.rows || [] })
      }
    }
  }
  return out
}

function fmtCell(v: any): string {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'number') return v.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  return String(v)
}

// ─── Component ──────────────────────────────────────────────────────────────

interface ExtractedDataViewerProps {
  summary: SummaryData | null
  loading?: boolean
  emptyLabel?: string
}

export default function ExtractedDataViewer({ summary, loading, emptyLabel }: ExtractedDataViewerProps) {
  const tables = useMemo(() => flattenTables(summary), [summary])
  const [activeTableId, setActiveTableId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)

  const activeTable = tables.find(t => t.id === activeTableId) || tables[0] || null
  const columns = summary?.columns || []

  const filteredRows = useMemo(() => {
    if (!activeTable) return []
    const q = search.trim().toLowerCase()
    if (!q) return activeTable.rows
    return activeTable.rows.filter(r =>
      (r.description || r.key || '').toLowerCase().includes(q)
    )
  }, [activeTable, search])

  if (loading) {
    return <div className="text-xs text-tx3 py-6 text-center">Loading extracted data…</div>
  }
  if (!summary || tables.length === 0) {
    return <div className="text-xs text-tx3 py-6 text-center">{emptyLabel || 'No data extracted yet.'}</div>
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Sheet / table switcher + search */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <button
            onClick={() => setPickerOpen(o => !o)}
            className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border
              text-[11px] font-semibold text-tx hover:bg-sub transition-all min-w-[160px] justify-between"
          >
            <span className="truncate max-w-[220px]">{activeTable?.label || 'Select table'}</span>
            <ChevronDown size={13} className={pickerOpen ? 'rotate-180' : ''} />
          </button>
          {pickerOpen && (
            <div className="absolute z-20 mt-1 max-h-72 w-72 overflow-y-auto rounded-lg border border-border
              bg-surf shadow-soft py-1">
              {tables.map(t => (
                <button
                  key={t.id}
                  onClick={() => { setActiveTableId(t.id); setPickerOpen(false) }}
                  className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-sub transition-all truncate
                    ${t.id === activeTable?.id ? 'text-acc font-semibold' : 'text-tx2'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="relative flex-1 min-w-[160px] max-w-xs">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tx3" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search rows in this table…"
            className="w-full h-8 pl-7 pr-2 rounded-lg border border-border bg-bg text-[11px] text-tx
              placeholder:text-tx3 focus:outline-none focus:ring-1 focus:ring-acc"
          />
        </div>

        <span className="text-[10px] text-tx3 ml-auto">
          {columns.length} period{columns.length === 1 ? '' : 's'} · {filteredRows.length} row{filteredRows.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Full data grid — scrolls both directions, no truncation */}
      <div className="border border-border rounded-xl overflow-auto max-h-[70vh]">
        <table className="text-[11px] border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-sub/70">
              <th className="sticky left-0 z-20 bg-sub/90 px-3 py-2 text-left text-tx2 font-semibold
                whitespace-nowrap border-b border-r border-border min-w-[220px]">
                Field
              </th>
              {columns.map((c, i) => (
                <th key={i} className="px-3 py-2 text-right text-tx2 font-semibold whitespace-nowrap
                  border-b border-border min-w-[120px]">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRows.map((row, ri) => (
              <tr key={ri} className="hover:bg-sub/30">
                <td className="sticky left-0 z-10 bg-surf px-3 py-1.5 text-tx font-medium whitespace-nowrap
                  border-r border-border min-w-[220px]">
                  {row.description || row.key}
                </td>
                {columns.map((_, ci) => (
                  <td key={ci} className="px-3 py-1.5 text-right text-tx whitespace-nowrap tabular-nums">
                    {fmtCell(row.values?.[ci])}
                  </td>
                ))}
              </tr>
            ))}
            {filteredRows.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="px-3 py-6 text-center text-tx3">
                  No rows match "{search}".
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}