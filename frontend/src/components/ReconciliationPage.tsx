import { useState, useRef, useEffect } from 'react'
import { X, Download, AlertCircle,Upload,
  CheckCircle2, AlertTriangle, RefreshCw, ChevronDown,
  Calendar, Layers, GitCompare, FileSpreadsheet,
} from 'lucide-react'
import React from 'react'
import ExtractedDataViewer, { type SummaryData } from './ExtractedDataViewer'

// ─── Types ────────────────────────────────────────────────────────────────────

type ReconStatus = 'Match' | 'Mismatch' | 'Missing' | 'Info'
interface SummaryRow {
  section: string
  description: string
  gstr1: number
  gstr3b: number
  difference: number
  status: ReconStatus
}

interface PeriodResult {
  period: string
  gstin: string
  overall_status: 'Matched' | 'Mismatch'
  total_variance: number
  breakdown?: Record<string, any> 
  rows: SummaryRow[]
}

interface ReconResult {
  periods: PeriodResult[]
  report_type: 'monthly' | 'annual'
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ||
  (() => {
    if (typeof window === 'undefined') return ''
    const devPorts = new Set(['5173','5174','5175','5176','5177','3000'])
    return devPorts.has(window.location.port) ? 'http://127.0.0.1:8000' : window.location.origin
  })()

const numFmt = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
const fmt = (v: number) => numFmt.format(v)

function statusPill(status: string) {
  if (status === 'Match')
    return <span className="pill pill-lo flex items-center gap-1"><CheckCircle2 size={10} />Match</span>
  if (status === 'Missing')
    return <span className="pill pill-inf flex items-center gap-1"><AlertCircle size={10} />Missing</span>
  if (status === 'Info')
    return <span className="pill pill-inf flex items-center gap-1"><AlertCircle size={10} />Info</span>
  return <span className="pill pill-hi flex items-center gap-1"><AlertTriangle size={10} />Mismatch</span>
}

// ─── Period Result Card ───────────────────────────────────────────────────────

function PeriodCard({ result, defaultOpen }: { result: PeriodResult; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? true)
  const mismatches = result.rows.filter(r => r.status !== 'Match' && r.status !== 'Info').length
  const isClean = result.overall_status === 'Matched'

  return (
    <div className={`rounded-xl border bg-surf shadow-sm overflow-hidden transition-all
      ${isClean ? 'border-ok/30' : 'border-err/30'}`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-sub/40 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isClean ? 'bg-ok' : 'bg-err'}`} />
        <span className="font-semibold text-sm text-tx flex-1">{result.period}</span>
        {result.gstin && (
          <span className="text-[10px] font-mono text-tx3 hidden sm:block">{result.gstin}</span>
        )}
        {!isClean && (
          <span className="pill pill-hi text-[10px]">
            {mismatches} mismatch{mismatches !== 1 ? 'es' : ''}
          </span>
        )}
        {isClean && <span className="pill pill-lo text-[10px]">Clean</span>}
        <ChevronDown size={14} className={`text-tx3 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="overflow-x-auto border-t border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-sub/60">
                <th className="px-3 py-2 text-left font-semibold text-tx2 whitespace-nowrap w-16">Section</th>
                <th className="px-3 py-2 text-left font-semibold text-tx2">Description</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">GSTR-1 (₹)</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">GSTR-3B (₹)</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">Difference (₹)</th>
                <th className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {result.rows.map((row, i) => (
                <tr
                  key={i}
                  className={`transition-colors
                    ${row.status === 'Mismatch' ? 'bg-err/5 hover:bg-err/10' :
                      row.status === 'Missing'  ? 'bg-warn/5 hover:bg-warn/10' :
                      row.status === 'Info'     ? 'bg-sub/30' :
                      'hover:bg-sub/50'}`}
                >
                  <td className="px-3 py-2 font-mono text-[10px] text-tx3 whitespace-nowrap">{row.section}</td>
                  <td className="px-3 py-2 text-tx">{row.description}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(row.gstr1)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(row.gstr3b)}</td>
                  <td className={`px-3 py-2 text-right tabular-nums font-medium
                    ${row.difference !== 0 ? 'text-err' : 'text-tx3'}`}>
                    {row.difference !== 0 ? (row.difference > 0 ? '+' : '') + fmt(row.difference) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">{statusPill(row.status)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-sub font-semibold border-t-2 border-border">
                <td colSpan={2} className="px-3 py-2 text-xs text-tx">Total Variance</td>
                <td colSpan={2} />
                <td className={`px-3 py-2 text-right tabular-nums text-xs
                  ${result.total_variance > 1 ? 'text-err' : 'text-ok'}`}>
                  {result.total_variance > 1 ? fmt(result.total_variance) : '₹ 0'}
                </td>
                <td className="px-3 py-2 text-center">
                  {isClean
                    ? <span className="pill pill-lo">Matched</span>
                    : <span className="pill pill-hi">Mismatch</span>}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}
function AnnualSummary({ periods }: { periods: PeriodResult[] }) {
  if (!periods.length) return null

  const ALL_DESCS = [
    'Outward Taxable Value',
    'IGST',
    'CGST',
    'SGST',
    'Cess',
    'Exports / Zero Rated Value',
    'Exports IGST',
    'Nil / Exempt Supplies',
  ]
  return (
    <div className="rounded-xl border border-border bg-surf shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-sub/60 border-b border-border flex items-center gap-2">
        <Layers size={14} className="text-acc" />
        <span className="font-semibold text-sm text-tx">Annual Summary</span>
        <span className="text-xs text-tx3 ml-1">({periods.length} month{periods.length !== 1 ? 's' : ''})</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-sub/40">
              <th className="px-3 py-2 text-left font-semibold text-tx2 sticky left-0 bg-sub/40 whitespace-nowrap z-10">Period</th>
              {ALL_DESCS.map(desc => (
                <th key={desc} colSpan={3} className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap border-l border-border">
                  {desc}
                </th>
              ))}
              <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap border-l border-border">Total Variance</th>
              <th className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap">Status</th>
            </tr>
            <tr className="bg-sub/20 border-b border-border">
              <th className="px-3 py-1 sticky left-0 bg-sub/20 z-10" />
              {ALL_DESCS.map(desc => (
                <React.Fragment key={desc}>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] border-l border-border whitespace-nowrap">GSTR-1</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">GSTR-3B</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">Diff</th>
                </React.Fragment>
              ))}
              <th className="px-3 py-1 border-l border-border" />
              <th className="px-3 py-1" />
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {periods.map((p, i) => {
              const byDesc = (desc: string) => p.rows.find(r => r.description === desc)
              return (
                <tr key={i} className={`transition-colors ${p.overall_status === 'Matched' ? 'hover:bg-sub/40' : 'bg-err/5 hover:bg-err/10'}`}>
                  <td className="px-3 py-2 font-medium text-tx sticky left-0 bg-inherit whitespace-nowrap z-10">{p.period}</td>
                  {ALL_DESCS.map(desc => {
                    const row = byDesc(desc)
                    const diff = row?.difference ?? 0
                    const hasDiff = Math.abs(diff) > 1
                    return (
                      <React.Fragment key={desc}>
                        <td className="px-2 py-2 text-right tabular-nums text-tx border-l border-border whitespace-nowrap">{fmt(row?.gstr1 ?? 0)}</td>
                        <td className="px-2 py-2 text-right tabular-nums text-tx whitespace-nowrap">{fmt(row?.gstr3b ?? 0)}</td>
                        <td className={`px-2 py-2 text-right tabular-nums font-medium whitespace-nowrap ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                          {hasDiff ? (diff > 0 ? '+' : '') + fmt(diff) : '—'}
                        </td>
                      </React.Fragment>
                    )
                  })}
                  <td className={`px-3 py-2 text-right tabular-nums font-semibold border-l border-border whitespace-nowrap ${p.total_variance > 1 ? 'text-err' : 'text-tx3'}`}>
                    {p.total_variance > 1 ? fmt(p.total_variance) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {p.overall_status === 'Matched'
                      ? <span className="pill pill-lo">Clean</span>
                      : <span className="pill pill-hi">Mismatch</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>

          <tfoot>
            <tr className="bg-sub font-semibold border-t-2 border-border">
              <td className="px-3 py-2 text-xs text-tx sticky left-0 bg-sub z-10">Annual Total</td>
              {ALL_DESCS.map(desc => {
                const g1Total   = periods.reduce((s, p) => s + (p.rows.find(r => r.description === desc)?.gstr1      ?? 0), 0)
                const g3bTotal  = periods.reduce((s, p) => s + (p.rows.find(r => r.description === desc)?.gstr3b     ?? 0), 0)
                const diffTotal = periods.reduce((s, p) => s + (p.rows.find(r => r.description === desc)?.difference ?? 0), 0)
                const hasDiff   = Math.abs(diffTotal) > 1
                return (
                  <React.Fragment key={desc}>
                    <td className="px-2 py-2 text-right tabular-nums text-xs border-l border-border">{fmt(g1Total)}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-xs">{fmt(g3bTotal)}</td>
                    <td className={`px-2 py-2 text-right tabular-nums text-xs ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                      {hasDiff ? fmt(diffTotal) : '—'}
                    </td>
                  </React.Fragment>
                )
              })}
              <td className={`px-3 py-2 text-right tabular-nums text-xs font-bold border-l border-border
                ${periods.reduce((s, p) => s + p.total_variance, 0) > 1 ? 'text-err' : 'text-ok'}`}>
                {fmt(periods.reduce((s, p) => s + p.total_variance, 0))}
              </td>
              <td className="px-3 py-2 text-center">
                {periods.every(p => p.overall_status === 'Matched')
                  ? <span className="pill pill-lo">All Clean</span>
                  : <span className="pill pill-hi">{periods.filter(p => p.overall_status !== 'Matched').length} Issues</span>}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
function Gstr3bBooksPeriodCard({ period, defaultOpen }: { period: any; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? true)
  const mismatches = (period.rows ?? []).filter((r: any) => r.status !== 'Match').length
  const isClean = period.overall_status === 'Matched'

  return (
    <div className={`rounded-xl border bg-surf shadow-sm overflow-hidden transition-all
      ${isClean ? 'border-ok/30' : 'border-err/30'}`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-sub/40 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isClean ? 'bg-ok' : 'bg-err'}`} />
        <span className="font-semibold text-sm text-tx flex-1">{period.period}</span>
        {!isClean && (
          <span className="pill pill-hi text-[10px]">
            {mismatches} mismatch{mismatches !== 1 ? 'es' : ''}
          </span>
        )}
        {isClean && <span className="pill pill-lo text-[10px]">Clean</span>}
        <ChevronDown size={14} className={`text-tx3 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="overflow-x-auto border-t border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-sub/60">
                <th className="px-3 py-2 text-left font-semibold text-tx2">Description</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">Books (₹)</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">GSTR-3B (₹)</th>
                <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">Difference (₹)</th>
                <th className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(period.rows ?? []).map((row: any, i: number) => (
                <tr
                  key={i}
                  className={`transition-colors
                    ${row.status === 'Mismatch' ? 'bg-err/5 hover:bg-err/10' :
                      row.status === 'Difference' ? 'bg-warn/5 hover:bg-warn/10' :
                      'hover:bg-sub/50'}`}
                >
                  <td className="px-3 py-2 text-tx">{row.description}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(row.books ?? 0)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(row.gstr3b ?? 0)}</td>
                  <td className={`px-3 py-2 text-right tabular-nums font-medium
                    ${row.difference !== 0 ? 'text-err' : 'text-tx3'}`}>
                    {row.difference !== 0 ? (row.difference > 0 ? '+' : '') + fmt(row.difference) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {row.status === 'Match'
                      ? <span className="pill pill-lo">Match</span>
                      : row.status === 'Difference'
                      ? <span className="pill pill-inf">Difference</span>
                      : <span className="pill pill-hi">Mismatch</span>}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-sub font-semibold border-t-2 border-border">
                <td className="px-3 py-2 text-xs text-tx">Total Variance</td>
                <td colSpan={2} />
                <td className={`px-3 py-2 text-right tabular-nums text-xs
                  ${period.total_variance > 1 ? 'text-err' : 'text-ok'}`}>
                  {period.total_variance > 1 ? fmt(period.total_variance) : '₹ 0'}
                </td>
                <td className="px-3 py-2 text-center">
                  {isClean
                    ? <span className="pill pill-lo">Matched</span>
                    : <span className="pill pill-hi">{period.overall_status}</span>}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}
function Gstr2bBooksPeriodCard({ period, defaultOpen }: { period: any; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? true)
  const isClean = period.status === 'MATCH'
  const isMissing = period.status === 'MONTH_MISSING'
  const fields = [
    { label: 'IGST', books: period.books_igst, gstr2b: period.gstr2b_igst, diff: period.diff_igst },
    { label: 'CGST', books: period.books_cgst, gstr2b: period.gstr2b_cgst, diff: period.diff_cgst },
    { label: 'SGST', books: period.books_sgst, gstr2b: period.gstr2b_sgst, diff: period.diff_sgst },
  ]
  const statusPill = (status: string) => {
    if (status === 'MATCH') return <span className="pill pill-lo text-[10px]">Clean</span>
    if (status === 'WARNING') return <span className="pill pill-inf text-[10px]">Warning</span>
    if (status === 'MONTH_MISSING') return <span className="pill text-[10px]" style={{ background: 'var(--color-sub)', color: 'var(--color-tx3)' }}>Missing</span>
    return <span className="pill pill-hi text-[10px]">Mismatch</span>
  }

  return (
    <div className={`rounded-xl border bg-surf shadow-sm overflow-hidden transition-all
      ${isClean ? 'border-ok/30' : isMissing ? 'border-border' : 'border-err/30'}`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-sub/40 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isClean ? 'bg-ok' : isMissing ? 'bg-tx3' : 'bg-err'}`} />
        <span className="font-semibold text-sm text-tx flex-1">{period.period}</span>
        {statusPill(period.status)}
        <ChevronDown size={14} className={`text-tx3 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="overflow-x-auto border-t border-border">
          {isMissing ? (
            <p className="px-4 py-3 text-xs text-tx3">
              This month is present in only one of GSTR-2B or Books — no comparison possible.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-sub/60">
                  <th className="px-3 py-2 text-left font-semibold text-tx2">Tax Head</th>
                  <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">Books (₹)</th>
                  <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">GSTR-2B (₹)</th>
                  <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">Difference (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {fields.map((f, i) => (
                  <tr key={i} className={Math.abs(f.diff) > 1 ? 'bg-err/5 hover:bg-err/10' : 'hover:bg-sub/50'}>
                    <td className="px-3 py-2 text-tx">{f.label}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(f.books ?? 0)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(f.gstr2b ?? 0)}</td>
                    <td className={`px-3 py-2 text-right tabular-nums font-medium ${Math.abs(f.diff) > 1 ? 'text-err' : 'text-tx3'}`}>
                      {Math.abs(f.diff) > 1 ? (f.diff > 0 ? '+' : '') + fmt(f.diff) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-sub font-semibold border-t-2 border-border">
                  <td className="px-3 py-2 text-xs text-tx">Total Variance</td>
                  <td colSpan={2} />
                  <td className={`px-3 py-2 text-right tabular-nums text-xs ${period.total_variance > 1 ? 'text-err' : 'text-ok'}`}>
                    {period.total_variance > 1 ? fmt(period.total_variance) : '₹ 0'}
                  </td>
                </tr>
              </tfoot>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
function Gstr2bBooksAnnualSummary({ periods }: { periods: any[] }) {
  if (!periods.length) return null

  const FIELDS = [
    { label: 'IGST', books: 'books_igst', other: 'gstr2b_igst', diff: 'diff_igst' },
    { label: 'CGST', books: 'books_cgst', other: 'gstr2b_cgst', diff: 'diff_cgst' },
    { label: 'SGST', books: 'books_sgst', other: 'gstr2b_sgst', diff: 'diff_sgst' },
  ]

  return (
    <div className="rounded-xl border border-border bg-surf shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-sub/60 border-b border-border flex items-center gap-2">
        <Layers size={14} className="text-acc" />
        <span className="font-semibold text-sm text-tx">Annual Summary</span>
        <span className="text-xs text-tx3 ml-1">({periods.length} month{periods.length !== 1 ? 's' : ''})</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-sub/40">
              <th className="px-3 py-2 text-left font-semibold text-tx2 sticky left-0 bg-sub/40 whitespace-nowrap z-10">Period</th>
              {FIELDS.map(f => (
                <th key={f.label} colSpan={3} className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap border-l border-border">
                  {f.label}
                </th>
              ))}
              <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap border-l border-border">Total Variance</th>
              <th className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap">Status</th>
            </tr>
            <tr className="bg-sub/20 border-b border-border">
              <th className="px-3 py-1 sticky left-0 bg-sub/20 z-10" />
              {FIELDS.map(f => (
                <React.Fragment key={f.label}>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] border-l border-border whitespace-nowrap">Books</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">GSTR-2B</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">Diff</th>
                </React.Fragment>
              ))}
              <th className="px-3 py-1 border-l border-border" />
              <th className="px-3 py-1" />
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {periods.map((p, i) => (
              <tr key={i} className={`transition-colors ${p.status === 'MATCH' ? 'hover:bg-sub/40' : 'bg-err/5 hover:bg-err/10'}`}>
                <td className="px-3 py-2 font-medium text-tx sticky left-0 bg-inherit whitespace-nowrap z-10">{p.period}</td>
                {FIELDS.map(f => {
                  const diff = p[f.diff] ?? 0
                  const hasDiff = Math.abs(diff) > 1
                  return (
                    <React.Fragment key={f.label}>
                      <td className="px-2 py-2 text-right tabular-nums text-tx border-l border-border whitespace-nowrap">{fmt(p[f.books] ?? 0)}</td>
                      <td className="px-2 py-2 text-right tabular-nums text-tx whitespace-nowrap">{fmt(p[f.other] ?? 0)}</td>
                      <td className={`px-2 py-2 text-right tabular-nums font-medium whitespace-nowrap ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                        {hasDiff ? (diff > 0 ? '+' : '') + fmt(diff) : '—'}
                      </td>
                    </React.Fragment>
                  )
                })}
                <td className={`px-3 py-2 text-right tabular-nums font-semibold border-l border-border whitespace-nowrap ${p.total_variance > 1 ? 'text-err' : 'text-tx3'}`}>
                  {p.total_variance > 1 ? fmt(p.total_variance) : '—'}
                </td>
                <td className="px-3 py-2 text-center">
                  {p.status === 'MATCH'
                    ? <span className="pill pill-lo">Clean</span>
                    : p.status === 'MONTH_MISSING'
                    ? <span className="pill" style={{ background: 'var(--color-sub)', color: 'var(--color-tx3)' }}>Missing</span>
                    : <span className="pill pill-hi">Mismatch</span>}
                </td>
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr className="bg-sub font-semibold border-t-2 border-border">
              <td className="px-3 py-2 text-xs text-tx sticky left-0 bg-sub z-10">Annual Total</td>
              {FIELDS.map(f => {
                const booksTotal = periods.reduce((s, p) => s + (p[f.books] ?? 0), 0)
                const otherTotal = periods.reduce((s, p) => s + (p[f.other] ?? 0), 0)
                const diffTotal  = periods.reduce((s, p) => s + (p[f.diff]  ?? 0), 0)
                const hasDiff = Math.abs(diffTotal) > 1
                return (
                  <React.Fragment key={f.label}>
                    <td className="px-2 py-2 text-right tabular-nums text-xs border-l border-border">{fmt(booksTotal)}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-xs">{fmt(otherTotal)}</td>
                    <td className={`px-2 py-2 text-right tabular-nums text-xs ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                      {hasDiff ? fmt(diffTotal) : '—'}
                    </td>
                  </React.Fragment>
                )
              })}
              <td className={`px-3 py-2 text-right tabular-nums text-xs font-bold border-l border-border
                ${periods.reduce((s, p) => s + (p.total_variance ?? 0), 0) > 1 ? 'text-err' : 'text-ok'}`}>
                {fmt(periods.reduce((s, p) => s + (p.total_variance ?? 0), 0))}
              </td>
              <td className="px-3 py-2 text-center">
                {periods.every(p => p.status === 'MATCH')
                  ? <span className="pill pill-lo">All Clean</span>
                  : <span className="pill pill-hi">{periods.filter(p => p.status !== 'MATCH').length} Issues</span>}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
function Gstr3bBooksAnnualSummary({ periods }: { periods: any[] }) {
  if (!periods.length) return null


  const SECTIONS = [
    { label: 'Outward Supplies', descs: ['Taxable Value', 'Zero Rated Supplies', 'Nil Rated Supplies', 'IGST Output', 'CGST Output', 'SGST Output'] },
    { label: 'RCM Inward',       descs: ['RCM Taxable Value', 'RCM IGST', 'RCM CGST', 'RCM SGST'] },
    { label: 'ITC Available',    descs: ['ITC Available IGST', 'ITC Available CGST', 'ITC Available SGST'] },
    { label: 'ITC Reversed',     descs: ['ITC Reversed IGST', 'ITC Reversed CGST', 'ITC Reversed SGST'] },
    { label: 'Ineligible ITC',   descs: ['Ineligible ITC IGST', 'Ineligible ITC CGST', 'Ineligible ITC SGST'] },
    { label: 'Net ITC',          descs: ['Net ITC IGST', 'Net ITC CGST', 'Net ITC SGST'] },
    { label: 'ITC Utilised',     descs: ['ITC Utilised IGST', 'ITC Utilised CGST', 'ITC Utilised SGST'] },
    { label: 'Net Tax Payable',  descs: ['Net Tax Payable'] },
    { label: 'Cash Paid',        descs: ['Cash Paid IGST', 'Cash Paid CGST', 'Cash Paid SGST'] },
    { label: 'Interest',         descs: ['Interest IGST', 'Interest CGST', 'Interest SGST'] },
    { label: 'Late Fee',         descs: ['Late Fee CGST', 'Late Fee SGST'] },
  ]
  // Only include sections where at least one desc exists in the actual data
  const ALL_DESCS: string[] = []
  periods.forEach(p => {
    ;(p.rows ?? []).forEach((r: any) => {
      if (!ALL_DESCS.includes(r.description)) ALL_DESCS.push(r.description)
    })
  })
  const ACTIVE_SECTIONS = SECTIONS.map(s => ({
    ...s,
    descs: s.descs.filter(d => ALL_DESCS.includes(d))
  })).filter(s => s.descs.length > 0)
  const ORDERED_DESCS = ACTIVE_SECTIONS.flatMap(s => s.descs)

  return (
    <div className="rounded-xl border border-border bg-surf shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-sub/60 border-b border-border flex items-center gap-2">
        <Layers size={14} className="text-acc" />
        <span className="font-semibold text-sm text-tx">Annual Summary</span>
        <span className="text-xs text-tx3 ml-1">({periods.length} month{periods.length !== 1 ? 's' : ''})</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-sub/60 border-b border-border">
              <th className="px-3 py-1 sticky left-0 bg-sub/60 z-10" />
              {ACTIVE_SECTIONS.map(s => (
                <th key={s.label} colSpan={s.descs.length * 3}
                  className="px-3 py-1 text-center font-semibold text-tx text-[11px] border-l border-border whitespace-nowrap">
                  {s.label}
                </th>
              ))}
              <th className="px-3 py-1 border-l border-border" />
              <th className="px-3 py-1" />
            </tr>
            <tr className="bg-sub/40">
              <th className="px-3 py-2 text-left font-semibold text-tx2 sticky left-0 bg-sub/40 whitespace-nowrap z-10">Period</th>
              {ORDERED_DESCS.map(desc => (
                <th key={desc} colSpan={3} className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap border-l border-border">
                  {desc}
                </th>
              ))}
              <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap border-l border-border">Total Variance</th>
              <th className="px-3 py-2 text-center font-semibold text-tx2 whitespace-nowrap">Status</th>
            </tr>
            <tr className="bg-sub/20 border-b border-border">
              <th className="px-3 py-1 sticky left-0 bg-sub/20 z-10" />
              {ORDERED_DESCS.map(desc => (
                <React.Fragment key={desc}>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] border-l border-border whitespace-nowrap">Books</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">GSTR-3B</th>
                  <th className="px-2 py-1 text-right font-medium text-tx3 text-[10px] whitespace-nowrap">Diff</th>
                </React.Fragment>
              ))}
              <th className="px-3 py-1 border-l border-border" />
              <th className="px-3 py-1" />
            </tr>
          </thead>

          <tbody className="divide-y divide-border">
            {periods.map((p, i) => {
              const byDesc = (desc: string) => (p.rows ?? []).find((r: any) => r.description === desc)
              return (
                <tr key={i} className={`transition-colors ${p.overall_status === 'Matched' ? 'hover:bg-sub/40' : 'bg-err/5 hover:bg-err/10'}`}>
                  <td className="px-3 py-2 font-medium text-tx sticky left-0 bg-inherit whitespace-nowrap z-10">{p.period}</td>
                  {ORDERED_DESCS.map(desc => {
                    const row = byDesc(desc)
                    const diff = row?.difference ?? 0
                    const hasDiff = Math.abs(diff) > 1
                    return (
                      <React.Fragment key={desc}>
                        <td className="px-2 py-2 text-right tabular-nums text-tx border-l border-border whitespace-nowrap">{fmt(row?.books ?? 0)}</td>
                        <td className="px-2 py-2 text-right tabular-nums text-tx whitespace-nowrap">{fmt(row?.gstr3b ?? 0)}</td>
                        <td className={`px-2 py-2 text-right tabular-nums font-medium whitespace-nowrap ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                          {hasDiff ? (diff > 0 ? '+' : '') + fmt(diff) : '—'}
                        </td>
                      </React.Fragment>
                    )
                  })}
                  <td className={`px-3 py-2 text-right tabular-nums font-semibold border-l border-border whitespace-nowrap ${p.total_variance > 1 ? 'text-err' : 'text-tx3'}`}>
                    {p.total_variance > 1 ? fmt(p.total_variance) : '—'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {p.overall_status === 'Matched'
                      ? <span className="pill pill-lo">Clean</span>
                      : <span className="pill pill-hi">{p.overall_status}</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>

          <tfoot>
            <tr className="bg-sub font-semibold border-t-2 border-border">
              <td className="px-3 py-2 text-xs text-tx sticky left-0 bg-sub z-10">Annual Total</td>
              {ORDERED_DESCS.map(desc => {
                const booksTotal = periods.reduce((s, p) => s + ((p.rows ?? []).find((r: any) => r.description === desc)?.books ?? 0), 0)
                const g3bTotal   = periods.reduce((s, p) => s + ((p.rows ?? []).find((r: any) => r.description === desc)?.gstr3b ?? 0), 0)
                const diffTotal  = periods.reduce((s, p) => s + ((p.rows ?? []).find((r: any) => r.description === desc)?.difference ?? 0), 0)
                const hasDiff = Math.abs(diffTotal) > 1
                return (
                  <React.Fragment key={desc}>
                    <td className="px-2 py-2 text-right tabular-nums text-xs border-l border-border">{fmt(booksTotal)}</td>
                    <td className="px-2 py-2 text-right tabular-nums text-xs">{fmt(g3bTotal)}</td>
                    <td className={`px-2 py-2 text-right tabular-nums text-xs ${hasDiff ? 'text-err' : 'text-tx3'}`}>
                      {hasDiff ? fmt(diffTotal) : '—'}
                    </td>
                  </React.Fragment>
                )
              })}
              <td className={`px-3 py-2 text-right tabular-nums text-xs font-bold border-l border-border
                ${periods.reduce((s, p) => s + (p.total_variance ?? 0), 0) > 1 ? 'text-err' : 'text-ok'}`}>
                {fmt(periods.reduce((s, p) => s + (p.total_variance ?? 0), 0))}
              </td>
              <td className="px-3 py-2 text-center">
                {periods.every(p => p.overall_status === 'Matched')
                  ? <span className="pill pill-lo">All Clean</span>
                  : <span className="pill pill-hi">{periods.filter(p => p.overall_status !== 'Matched').length} Issues</span>}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
// ─── Props ────────────────────────────────────────────────────────────────────

interface ReconciliationPageProps {
  onGoToUpload?: () => void
}
// ─── Main Component ───────────────────────────────────────────────────────────

type ReconTab = 'gstr1-3b' | 'gstr2b-books' | 'gstr3b-books'

const TABS: { id: ReconTab; label: string; ready: boolean }[] = [
  { id: 'gstr1-3b',     label: 'GSTR-1 vs GSTR-3B', ready: true  },
 //{ id: 'gstr2b-books', label: 'GSTR-2B vs Books',   ready: true  },
 // { id: 'gstr3b-books', label: 'GSTR-3B vs Books',   ready: true },
]

export default function ReconciliationPage(_props: ReconciliationPageProps = {}) {

  const [activeTab,   setActiveTab]   = useState<ReconTab>('gstr1-3b')
  const [uploadStep, setUploadStep] = useState<string>('')
  // ── Reconciliation state ───────────────────────────────────────────────────
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState<string | null>(null)
  const [result,      setResult]      = useState<ReconResult | null>(null)
  const [downloading, setDownloading] = useState(false)

  // ── Toast notification ─────────────────────────────────────────────────────
  const [toast, setToast] = useState<string | null>(null)
  // ── PDF direct upload mode ─────────────────────────────────────────────────
const [gstr1Files,    setGstr1Files]    = useState<File[]>([])
const [gstr3bFiles,   setGstr3bFiles]   = useState<File[]>([])
const [gstin,         setGstin]         = useState('')
const [monthsFound,   setMonthsFound]   = useState<number>(0)
const [g1Extracted,   setG1Extracted]   = useState<Record<string,any>[]>([])
const [g3bExtracted,  setG3bExtracted]  = useState<Record<string,any>[]>([])
const [showExtracted, setShowExtracted] = useState<'gstr1'|'gstr3b'|null>(null)
const [g1Summary,  setG1Summary]  = useState<SummaryData | null>(null)
const [g3bSummary, setG3bSummary] = useState<SummaryData | null>(null)
const [summarizing, setSummarizing] = useState(false)
const [downloadingTables, setDownloadingTables] = useState(false)
const [downloadMenuOpen, setDownloadMenuOpen] = useState(false)
const downloadMenuRef = useRef<HTMLDivElement>(null)

useEffect(() => {
  if (!showExtracted) return
  const records = showExtracted === 'gstr1' ? g1Extracted : g3bExtracted
  if (!records.length) return
  const setSummary = showExtracted === 'gstr1' ? setG1Summary : setG3bSummary
  let cancelled = false
  setSummarizing(true)
  fetch(`${API_BASE}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ records, returnType: showExtracted === 'gstr1' ? 'GSTR-1' : 'GSTR-3B' }),
  })
    .then(res => res.json())
    .then(data => { if (!cancelled) setSummary(data) })
    .catch(() => { if (!cancelled) setSummary(null) })
    .finally(() => { if (!cancelled) setSummarizing(false) })
  return () => { cancelled = true }
}, [showExtracted, g1Extracted, g3bExtracted])
useEffect(() => {      
  if (!downloadMenuOpen) return
  const handler = (e: MouseEvent) => {
    if (!downloadMenuRef.current?.contains(e.target as Node)) setDownloadMenuOpen(false)
  }
  document.addEventListener('mousedown', handler)
  return () => document.removeEventListener('mousedown', handler)
}, [downloadMenuOpen])

const downloadTables = async (which: 'all' | 'gstr1' | 'gstr3b' = 'all') => {
  const datasets: { records: Record<string, any>[]; returnType: string }[] = []
  if (which !== 'gstr3b' && g1Extracted.length)  datasets.push({ records: g1Extracted,  returnType: 'GSTR-1' })
  if (which !== 'gstr1' && g3bExtracted.length) datasets.push({ records: g3bExtracted, returnType: 'GSTR-3B' })
  if (!datasets.length) return
  setDownloadingTables(true)
  setDownloadMenuOpen(false)
  try {
    const res = await fetch(`${API_BASE}/api/tables_excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ datasets }),
    })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const namePart = which === 'gstr1' ? 'GSTR1' : which === 'gstr3b' ? 'GSTR3B' : 'GSTR1_3B'
    a.download = `${namePart}_Tables_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    setError('Table export failed. Please try again.')
  } finally {
    setDownloadingTables(false)
  }
}
const gstr1Ref  = useRef<HTMLInputElement>(null)
const gstr3bRef = useRef<HTMLInputElement>(null)
// ── GSTR-3B vs Books state ─────────────────────────────────────────────────
const [g3bBooksFiles,       setG3bBooksFiles]       = useState<File[]>([])
const [booksFile,           setBooksFile]           = useState<File | null>(null)
const [g3bBooksResult,      setG3bBooksResult]      = useState<any>(null)
const [showG3bBooksExtracted, setShowG3bBooksExtracted] = useState(false)
const [g3bBooksSummary, setG3bBooksSummary] = useState<SummaryData | null>(null)
const [g3bBooksSummarizing, setG3bBooksSummarizing] = useState(false)
const [g3bBooksLoading,     setG3bBooksLoading]     = useState(false)
const [g3bBooksError,       setG3bBooksError]       = useState<string | null>(null)
const [g3bBooksStep,        setG3bBooksStep]        = useState('')
const [g3bBooksDownloading, setG3bBooksDownloading] = useState(false)
const g3bBooksRef = useRef<HTMLInputElement>(null)
const booksRef    = useRef<HTMLInputElement>(null)
const [downloadingG3bTables, setDownloadingG3bTables] = useState(false)
useEffect(() => {
  if (!showG3bBooksExtracted || !g3bBooksResult?.g3b_extracted?.length) return
  let cancelled = false
  setG3bBooksSummarizing(true)
  fetch(`${API_BASE}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ records: g3bBooksResult.g3b_extracted, returnType: 'GSTR-3B' }),
  })
    .then(res => res.json())
    .then(data => { if (!cancelled) setG3bBooksSummary(data) })
    .catch(() => { if (!cancelled) setG3bBooksSummary(null) })
    .finally(() => { if (!cancelled) setG3bBooksSummarizing(false) })
  return () => { cancelled = true }
}, [showG3bBooksExtracted, g3bBooksResult])

// ── GSTR-2B vs Books state ─────────────────────────────────────────────────
const [gstr2bFiles,         setGstr2bFiles]         = useState<File[]>([])
const [books2bFile,         setBooks2bFile]         = useState<File | null>(null)
const [gstr2bBooksResult,   setGstr2bBooksResult]   = useState<any>(null)
const [gstr2bBooksLoading,  setGstr2bBooksLoading]  = useState(false)
const [gstr2bBooksError,    setGstr2bBooksError]    = useState<string | null>(null)
const [gstr2bBooksStep,     setGstr2bBooksStep]     = useState('')
const [gstr2bBooksDownloading, setGstr2bBooksDownloading] = useState(false)
const [show2bExtracted, setShow2bExtracted] = useState<'gstr2b'|null>(null)
const gstr2bRef = useRef<HTMLInputElement>(null)
const books2bRef = useRef<HTMLInputElement>(null)
  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  // ── Download Excel ─────────────────────────────────────────────────────────
  const downloadExcel = async () => {
    if (!result) return
    setDownloading(true)
    try {
      const res = await fetch(`${API_BASE}/api/reconcile/gstr1-3b/excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ periods: result.periods, report_type: result.report_type }),
      })
      if (!res.ok) throw new Error('Download failed')
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `GSTR1_vs_3B_${result.report_type}_${new Date().toISOString().slice(0,10)}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setError('Excel download failed: ' + (e?.message ?? 'unknown error'))
    } finally {
      setDownloading(false)
    }
  }

  const runPdfReconciliation = async () => {
  if (!gstr1Files.length || !gstr3bFiles.length) {
    setError('Select at least one GSTR-1 PDF and one GSTR-3B PDF.')
    return
  }
  setLoading(true)
  setError(null)
  setResult(null)
  setGstin('')
  setMonthsFound(0)

  try {
    setUploadStep('Extracting PDFs...')
    const form = new FormData()
    gstr1Files.forEach(f  => form.append('gstr1_files',  f))
    gstr3bFiles.forEach(f => form.append('gstr3b_files', f))

    const res = await fetch(`${API_BASE}/api/reconcile/gstr1-3b/from-pdf`, {
      method: 'POST',
      body: form,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Server error' }))
      throw new Error(err.error ?? res.statusText)
    }

    setUploadStep('Building reconciliation...')
    const data = await res.json()

    setGstin(data.gstin ?? '')
    setMonthsFound(data.months_detected ?? 0)
    setG1Extracted(data.g1_extracted ?? [])
    setG3bExtracted(data.g3b_extracted ?? [])

    const periods: PeriodResult[] = (data.periods ?? []).map((p: any) => ({
      period:         p.period ?? '',
      gstin:          p.gstin  ?? '',
      overall_status: p.overall_status === 'Matched' ? 'Matched' : 'Mismatch',
      total_variance: p.total_variance ?? 0,
      breakdown:      p.breakdown ?? {},
      rows: (p.rows ?? []).map((r: any) => ({
        section:     r.section,
        description: r.description,
        gstr1:       r.gstr1      ?? 0,
        gstr3b:      r.gstr3b     ?? 0,
        difference:  r.difference ?? 0,
        status: (r.status === 'Match' ? 'Match' : r.status === 'Missing' ? 'Missing' : r.status === 'Info' ? 'Info' : 'Mismatch') as ReconStatus,      }))
    }))

    setResult({ periods, report_type: periods.length > 1 ? 'annual' : 'monthly' })
    setUploadStep('')
    showToast(`${data.months_detected} month(s) reconciled ✓`)
  } catch (e: any) {
    setError(e?.message ?? 'Reconciliation failed.')
    setUploadStep('')
  } finally {
    setLoading(false)
  }
}

const runGstr3bBooksReconciliation = async () => {
  if (!g3bBooksFiles.length || !booksFile) {
    setG3bBooksError('Select at least one GSTR-3B PDF and one Books Excel file.')
    return
  }
  setG3bBooksLoading(true)
  setG3bBooksError(null)
  setG3bBooksResult(null)

  try {
    setG3bBooksStep('Extracting & reconciling...')
    const form = new FormData()
    g3bBooksFiles.forEach(f => form.append('gstr3b_files', f))
    form.append('books_file', booksFile)

    const res = await fetch(`${API_BASE}/api/reconcile/gstr3b-books`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Server error' }))
      throw new Error(err.error ?? res.statusText)
    }

    const data = await res.json()
    setG3bBooksResult(data)
    setG3bBooksStep('')
    showToast(`${data.months_detected} month(s) reconciled ✓`)
  } catch (e: any) {
    setG3bBooksError(e?.message ?? 'Reconciliation failed.')
    setG3bBooksStep('')
  } finally {
    setG3bBooksLoading(false)
  }
}

const downloadG3bBooksExcel = async () => {
  if (!g3bBooksResult) return
  setG3bBooksDownloading(true)
  try {
    const res = await fetch(`${API_BASE}/api/reconcile/gstr3b-books/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        result:      g3bBooksResult,
        gstin_3b:    g3bBooksResult.gstin_3b    ?? '',
        gstin_books: g3bBooksResult.gstin_books ?? '',
      }),
    })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `GSTR3B_vs_Books_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    setG3bBooksError('Excel download failed: ' + (e?.message ?? ''))
  } finally {
    setG3bBooksDownloading(false)
  }
}

const runGstr2bBooksReconciliation = async () => {
  if (!gstr2bFiles.length || !books2bFile) {
    setGstr2bBooksError('Select at least one GSTR-2B Excel file and one Books Excel/CSV file.')
    return
  }
  setGstr2bBooksLoading(true)
  setGstr2bBooksError(null)
  setGstr2bBooksResult(null)

  try {
    setGstr2bBooksStep('Extracting & reconciling...')
    const form = new FormData()
    gstr2bFiles.forEach(f => form.append('gstr2b_files', f))
    form.append('books_file', books2bFile)

    const res = await fetch(`${API_BASE}/api/reconcile/gstr2b-books`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Server error' }))
      throw new Error(err.error ?? res.statusText)
    }

    const data = await res.json()
    setGstr2bBooksResult(data)
    setGstr2bBooksStep('')
    showToast(`${data.months_detected} month(s) reconciled ✓`)
  } catch (e: any) {
    setGstr2bBooksError(e?.message ?? 'Reconciliation failed.')
    setGstr2bBooksStep('')
  } finally {
    setGstr2bBooksLoading(false)
  }
}

const downloadGstr2bBooksExcel = async () => {
  if (!gstr2bBooksResult) return
  setGstr2bBooksDownloading(true)
  try {
    const res = await fetch(`${API_BASE}/api/reconcile/gstr2b-books/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        result:      gstr2bBooksResult,
        gstr2b_data: gstr2bBooksResult.gstr2b_data ?? {},
        books_data:  gstr2bBooksResult.books_data  ?? {},
        gstin_2b:    gstr2bBooksResult.gstin_2b    ?? '',
        gstin_books: gstr2bBooksResult.gstin_books ?? '',
      }),
    })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `GSTR2B_vs_Books_${new Date().toISOString().slice(0,10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    setGstr2bBooksError('Excel download failed: ' + (e?.message ?? ''))
  } finally {
    setGstr2bBooksDownloading(false)
  }
}

  // ── Period sort (Apr → Mar) ────────────────────────────────────────────────
  const MONTH_ORDER = ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar']
  const sortedPeriods = result
    ? [...result.periods].sort((a, b) => {
        const ai = MONTH_ORDER.findIndex(m => a.period.startsWith(m))
        const bi = MONTH_ORDER.findIndex(m => b.period.startsWith(m))
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
      })
    : []


  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5 py-1">

      {/* ── Toast ─────────────────────────────────────────────────────────── */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-[60]">
          <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-ok text-white shadow-lg text-sm font-medium">
            <CheckCircle2 size={15} />
            {toast}
          </div>
        </div>
      )}

      {/* ── Sub-navigation tabs ───────────────────────────────────────────── */}
      <div className="mx-6 flex justify-center">
      <div className="flex items-center gap-1 p-1 bg-sub rounded-xl w-fit">
          {TABS.map(tab => (
            <button
              key={tab.id}
              disabled={!tab.ready}
              onClick={() => { if (tab.ready) { setActiveTab(tab.id); setUploadStep(''); setG3bBooksStep('') } }}
              className={`relative px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
                ${activeTab === tab.id
                  ? 'bg-surf text-acc shadow-sm'
                  : tab.ready
                    ? 'text-tx2 hover:text-tx hover:bg-surf/50'
                    : 'text-tx3 cursor-not-allowed'}`}
            >
              {tab.label}
              {!tab.ready && (
                <span className="ml-1.5 text-[9px] font-mono bg-sub text-tx3 px-1 py-0.5 rounded">Soon</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'gstr1-3b' && (
  <div className="mx-6 space-y-5">
    <div className="bg-surf rounded-2xl border border-border shadow-soft p-5 space-y-5">

      {/* Header */}
      <div className="flex items-center gap-2">
        <GitCompare size={16} className="text-acc" />
        <h2 className="font-semibold text-sm text-tx">GSTR-1 vs GSTR-3B Reconciliation</h2>
      </div>

      {/* PDF Upload zones */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* GSTR-1 */}
        <div
          onClick={() => gstr1Ref.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${gstr1Files.length ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${gstr1Files.length ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">GSTR-1 PDF(s)</p>
          <p className="text-[11px] text-tx3 mt-1">
            {gstr1Files.length
              ? `${gstr1Files.length} file(s): ${gstr1Files.map(f => f.name).join(', ')}`
              : 'Click to select — 1 month or up to 12 months'}
          </p>
          <input
            ref={gstr1Ref}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={e => setGstr1Files(Array.from(e.target.files ?? []))}
          />
        </div>

        <div className="hidden sm:flex items-center justify-center px-2">
          <span className="text-[10px] font-mono text-tx3">vs</span>
        </div>
        
        {/* GSTR-3B */}
        <div
          onClick={() => gstr3bRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${gstr3bFiles.length ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${gstr3bFiles.length ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">GSTR-3B PDF(s)</p>
          <p className="text-[11px] text-tx3 mt-1">
            {gstr3bFiles.length
              ? `${gstr3bFiles.length} file(s): ${gstr3bFiles.map(f => f.name).join(', ')}`
              : 'Click to select — 1 month or up to 12 months'}
          </p>
          <input
            ref={gstr3bRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={e => setGstr3bFiles(Array.from(e.target.files ?? []))}
          />
        </div>
      </div>

      {/* Status badges — shown after successful extraction */}
      {(gstin || monthsFound > 0) && (
        <div className="flex flex-wrap gap-2">
          {gstin && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold bg-ok/10 text-ok border border-ok/20">
              <CheckCircle2 size={11} /> GSTIN {gstin} verified
            </span>
          )}
          {monthsFound > 0 && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold bg-acc/10 text-acc border border-acc/20">
              <Calendar size={11} /> {monthsFound} month(s) detected
            </span>
          )}
        </div>
      )}

      {uploadStep && (
        <p className="text-[11px] text-acc animate-pulse">{uploadStep}</p>
      )}

      {/* Action row */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={runPdfReconciliation}
          disabled={loading || !gstr1Files.length || !gstr3bFiles.length}
          className="inline-flex items-center gap-2 px-4 h-9 rounded-xl text-white text-sm font-semibold
            disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:opacity-90 shadow-sm"
          style={{ background: 'linear-gradient(to right, var(--color-acc), #e57373)' }}
        >
          {loading
            ? <><RefreshCw size={14} className="animate-spin" /> Processing…</>
            : <><GitCompare size={14} /> Run Reconciliation</>}
        </button>

        {result && (
          <button
            onClick={downloadExcel}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 h-9 rounded-xl border border-border bg-surf
              text-tx text-sm font-semibold hover:bg-sub transition-all disabled:opacity-50"
          >
            {downloading
              ? <><RefreshCw size={14} className="animate-spin" /> Preparing…</>
              : <><Download size={14} /> Download Excel</>}
          </button>
        )}

        {/* View extracted data buttons */}
        {g1Extracted.length > 0 && (
          <>
            <button
              onClick={() => setShowExtracted(showExtracted === 'gstr1' ? null : 'gstr1')}
              className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
                text-xs font-semibold text-tx hover:bg-sub transition-all"
            >
              {showExtracted === 'gstr1' ? '▲' : '▼'} View GSTR-1 Data
            </button>
            <button
              onClick={() => setShowExtracted(showExtracted === 'gstr3b' ? null : 'gstr3b')}
              className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
                text-xs font-semibold text-tx hover:bg-sub transition-all"
            >
              {showExtracted === 'gstr3b' ? '▲' : '▼'} View GSTR-3B Data
            </button>
            <div className="relative" ref={downloadMenuRef}>
            <button
            onClick={() => setDownloadMenuOpen(o => !o)}
                disabled={downloadingTables}
                className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
                  text-xs font-semibold text-tx hover:bg-sub transition-all disabled:opacity-50"
              >
                <Download size={13} /> {downloadingTables ? 'Preparing…' : 'Download Tables'}
                <ChevronDown size={13} className={downloadMenuOpen ? 'rotate-180' : ''} />
              </button>
              {downloadMenuOpen && (
                <div className="absolute z-20 mt-1 w-56 rounded-lg border border-border bg-surf shadow-soft py-1">
                  <button
                    onClick={() => downloadTables('all')}
                    disabled={!g1Extracted.length || !g3bExtracted.length}
                    className="w-full text-left px-3 py-2 text-[11px] text-tx hover:bg-sub transition-all
                      disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Both — Combined Workbook
                  </button>
                  <button
                    onClick={() => downloadTables('gstr1')}
                    disabled={!g1Extracted.length}
                    className="w-full text-left px-3 py-2 text-[11px] text-tx hover:bg-sub transition-all
                      disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    GSTR-1 Tables Only
                  </button>
                  <button
                    onClick={() => downloadTables('gstr3b')}
                    disabled={!g3bExtracted.length}
                    className="w-full text-left px-3 py-2 text-[11px] text-tx hover:bg-sub transition-all
                      disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    GSTR-3B Tables Only
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {(gstr1Files.length > 0 || gstr3bFiles.length > 0 || result) && (
          <button
            onClick={() => {
              setGstr1Files([]); setGstr3bFiles([])
              setResult(null); setError(null)
              setGstin(''); setMonthsFound(0)
              setG1Extracted([]); setG3bExtracted([])
              setShowExtracted(null)
              setG1Summary(null); setG3bSummary(null)
            }}
            className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl text-tx3
              hover:text-err hover:bg-err/5 text-xs transition-all ml-auto"
          >
            <X size={13} /> Clear
          </button>
        )}
      </div>
    </div>

    {/* Extracted data viewer — collapsible, full columns/rows, search, sheet switching */}
    {showExtracted && (g1Extracted.length > 0 || g3bExtracted.length > 0) && (
      <div className="bg-surf rounded-2xl border border-border shadow-soft p-4">
        <p className="text-xs font-semibold text-tx mb-3">
          {showExtracted === 'gstr1' ? 'GSTR-1 Extracted Data' : 'GSTR-3B Extracted Data'}
        </p>
        <ExtractedDataViewer
          summary={showExtracted === 'gstr1' ? g1Summary : g3bSummary}
          loading={summarizing}
        />
      </div>
    )}

    {/* Error */}
    {error && (
      <div className="flex items-start gap-2.5 rounded-xl border border-err/30 bg-err/5 px-4 py-3">
        <AlertCircle size={15} className="text-err flex-shrink-0 mt-0.5" />
        <p className="text-xs text-err">{error}</p>
      </div>
    )}

    {/* Results */}
    {result && sortedPeriods.length > 0 && (
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Periods',       value: sortedPeriods.length,                                              color: 'text-tx'  },
            { label: 'Clean',         value: sortedPeriods.filter(p => p.overall_status === 'Matched').length,  color: 'text-ok'  },
            { label: 'Mismatches',    value: sortedPeriods.filter(p => p.overall_status !== 'Matched').length,  color: 'text-err' },
          ].map(stat => (
            <div key={stat.label} className="bg-surf rounded-xl border border-border p-3 shadow-sm">
              <div className={`text-lg font-bold tabular-nums ${stat.color}`}>{stat.value}</div>
              <div className="text-[10px] text-tx3 font-medium uppercase tracking-wide mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
        {sortedPeriods.length > 1 && <AnnualSummary periods={sortedPeriods} />}
        <div className="space-y-3">
          {sortedPeriods.map((p, i) => (
            <PeriodCard
              key={p.period}
              result={p}
              defaultOpen={sortedPeriods.length === 1 || p.overall_status !== 'Matched' || i === 0}
            />
          ))}
        </div>
      </div>
    )}

    {!result && !loading && !error && (
      <div className="rounded-2xl border border-dashed border-border bg-surf/40 p-10 text-center">
        <GitCompare size={28} className="mx-auto text-tx3 mb-3" />
        <p className="text-sm font-medium text-tx2">Upload PDFs to begin</p>
        <p className="text-xs text-tx3 mt-1">Select GSTR-1 and GSTR-3B PDFs above — one month or up to 12 months at once</p>
      </div>
    )}
  </div>
)}

      {activeTab === 'gstr2b-books' && (
  <div className="mx-6 space-y-5">
    <div className="bg-surf rounded-2xl border border-border shadow-soft p-5 space-y-5">

      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <GitCompare size={16} className="text-acc" />
          <h2 className="font-semibold text-sm text-tx">GSTR-2B vs Books Reconciliation</h2>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`${API_BASE}/api/reconcile/gstr2b-books/template`}
            download
            className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border bg-surf text-xs font-semibold text-tx hover:bg-sub transition-all"
          >
            <Download size={13} /> Download Books Template
          </a>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        {/* GSTR-2B Excel(s) */}
        <div
          onClick={() => gstr2bRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${gstr2bFiles.length ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${gstr2bFiles.length ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">GSTR-2B Excel(s)</p>
          <p className="text-[11px] text-tx3 mt-1">
            {gstr2bFiles.length
              ? `${gstr2bFiles.length} file(s) selected`
              : '1 month or up to 12 months'}
          </p>
          <input ref={gstr2bRef} type="file" accept=".xlsx,.xls" multiple className="hidden"
            onChange={e => setGstr2bFiles(Array.from(e.target.files ?? []))} />
        </div>

        <div className="hidden sm:flex items-center justify-center px-2">
          <span className="text-[10px] font-mono text-tx3">vs</span>
        </div>

        {/* Books Excel */}
        <div
          onClick={() => books2bRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${books2bFile ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${books2bFile ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">Books Excel / CSV</p>
          <p className="text-[11px] text-tx3 mt-1">
            {books2bFile ? books2bFile.name : 'Click to select (.xlsx or .csv)'}
          </p>
          <input ref={books2bRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
            onChange={e => setBooks2bFile(e.target.files?.[0] ?? null)} />
        </div>
      </div>

      {gstr2bBooksStep && <p className="text-[11px] text-acc animate-pulse">{gstr2bBooksStep}</p>}

      {gstr2bBooksResult?.summary?.gstin_warning && (
        <div className="flex items-center gap-2 rounded-lg border border-warn/30 bg-warn/5 px-3 py-2">
          <AlertTriangle size={13} className="text-warn flex-shrink-0" />
          <p className="text-[11px] text-warn">{gstr2bBooksResult.summary.gstin_warning}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={runGstr2bBooksReconciliation}
          disabled={gstr2bBooksLoading || !gstr2bFiles.length || !books2bFile}
          className="inline-flex items-center gap-2 px-4 h-9 rounded-xl text-white text-sm font-semibold
            disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:opacity-90 shadow-sm"
          style={{ background: 'linear-gradient(to right, var(--color-acc), #e57373)' }}
        >
          {gstr2bBooksLoading
            ? <><RefreshCw size={14} className="animate-spin" /> Processing…</>
            : <><GitCompare size={14} /> Run Reconciliation</>}
        </button>
            
        {gstr2bBooksResult && (
  <>
    <button
      onClick={downloadGstr2bBooksExcel}
      disabled={gstr2bBooksDownloading}
      className="inline-flex items-center gap-2 px-4 h-9 rounded-xl border border-border bg-surf
        text-tx text-sm font-semibold hover:bg-sub transition-all disabled:opacity-50"
    >
      {gstr2bBooksDownloading
        ? <><RefreshCw size={14} className="animate-spin" /> Preparing…</>
        : <><Download size={14} /> Download Excel</>}
    </button>
    <button
      onClick={() => setShow2bExtracted(show2bExtracted === 'gstr2b' ? null : 'gstr2b')}
      className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
        text-xs font-semibold text-tx hover:bg-sub transition-all"
    >
      {show2bExtracted === 'gstr2b' ? '▲' : '▼'} View Extracted GSTR-2B
    </button>
  </>
)}

        {(gstr2bFiles.length > 0 || books2bFile || gstr2bBooksResult) && (
          <button
            onClick={() => {
              setGstr2bFiles([]); setBooks2bFile(null)
              setGstr2bBooksResult(null); setGstr2bBooksError(null)
              setShow2bExtracted(null)
            }}
            className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl text-tx3
              hover:text-err hover:bg-err/5 text-xs transition-all ml-auto"
          >
            <X size={13} /> Clear
          </button>
        )}
      </div>
    </div>

    {gstr2bBooksError && (
      <div className="flex items-start gap-2.5 rounded-xl border border-err/30 bg-err/5 px-4 py-3">
        <AlertCircle size={15} className="text-err flex-shrink-0 mt-0.5" />
        <p className="text-xs text-err">{gstr2bBooksError}</p>
      </div>
    )}

    {gstr2bBooksResult && show2bExtracted && (
  <div className="bg-surf rounded-2xl border border-border shadow-soft p-4 overflow-x-auto">
    <p className="text-xs font-semibold text-tx mb-3">Extracted GSTR-2B Data (all months)</p>
    <table className="w-full text-xs">
      <thead>
        <tr className="bg-sub/60">
          <th className="px-3 py-2 text-left font-semibold text-tx2">Period</th>
          <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">IGST (₹)</th>
          <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">CGST (₹)</th>
          <th className="px-3 py-2 text-right font-semibold text-tx2 whitespace-nowrap">SGST (₹)</th>
          <th className="px-3 py-2 text-left font-semibold text-tx2 whitespace-nowrap">Source</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {(gstr2bBooksResult.gstr2b_data?.monthly_data ?? []).map((m: any, i: number) => (
          <tr key={i} className="hover:bg-sub/30">
            <td className="px-3 py-2 text-tx font-medium">{m.period}</td>
            <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(m.itc_igst ?? 0)}</td>
            <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(m.itc_cgst ?? 0)}</td>
            <td className="px-3 py-2 text-right tabular-nums text-tx">{fmt(m.itc_sgst ?? 0)}</td>
            <td className="px-3 py-2 text-tx3 whitespace-nowrap">{m.source}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)}

    {gstr2bBooksResult && (
      <div className="space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Months',     value: gstr2bBooksResult.summary?.months ?? 0,     color: 'text-tx'  },
            { label: 'Matched',    value: gstr2bBooksResult.summary?.matched ?? 0,    color: 'text-ok'  },
            { label: 'Mismatches', value: gstr2bBooksResult.summary?.mismatches ?? 0, color: 'text-err' },
          ].map(stat => (
            <div key={stat.label} className="bg-surf rounded-xl border border-border p-3 shadow-sm">
              <div className={`text-lg font-bold tabular-nums ${stat.color}`}>{stat.value}</div>
              <div className="text-[10px] text-tx3 font-medium uppercase tracking-wide mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
        {(gstr2bBooksResult.monthly ?? []).length > 1 && (
        <Gstr2bBooksAnnualSummary periods={gstr2bBooksResult.monthly ?? []} />
        )}
        {/* Monthly breakdown */}
        <div className="space-y-3">
          {(gstr2bBooksResult.monthly ?? []).map((period: any, i: number) => (
            <Gstr2bBooksPeriodCard
              key={period.period}
              period={period}
              defaultOpen={(gstr2bBooksResult.monthly ?? []).length === 1 || period.status !== 'MATCH' || i === 0}
            />
          ))}
        </div>
      </div>
    )}

    {!gstr2bBooksResult && !gstr2bBooksLoading && !gstr2bBooksError && (
      <div className="rounded-2xl border border-dashed border-border bg-surf/40 p-10 text-center">
        <GitCompare size={28} className="mx-auto text-tx3 mb-3" />
        <p className="text-sm font-medium text-tx2">Upload files to begin</p>
        <p className="text-xs text-tx3 mt-1">Select GSTR-2B Excel file(s) and your Books Excel/CSV above</p>
      </div>
    )}
  </div>
)}

{activeTab === 'gstr3b-books' && (
  <div className="mx-6 space-y-5">
    <div className="bg-surf rounded-2xl border border-border shadow-soft p-5 space-y-5">

      <div className="flex items-center justify-between gap-2">
  <div className="flex items-center gap-2">
    <GitCompare size={16} className="text-acc" />
    <h2 className="font-semibold text-sm text-tx">GSTR-3B vs Books Reconciliation</h2>
  </div>
  <div className="flex items-center gap-2">
    <a
      href={`${API_BASE}/api/reconcile/gstr3b-books/template`}
      download
      className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border bg-surf text-xs font-semibold text-tx hover:bg-sub transition-all"
    >
      <Download size={13} /> Download Template
    </a>
    <a
      href={`${API_BASE}/api/reconcile/gstr3b-books/sample`}
      download
      className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border bg-surf text-xs font-semibold text-tx hover:bg-sub transition-all"
    >
      <FileSpreadsheet size={13} /> Download Sample
    </a>
  </div>
</div>

      <div className="flex flex-col sm:flex-row gap-3">
        {/* GSTR-3B PDFs */}
        <div
          onClick={() => g3bBooksRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${g3bBooksFiles.length ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${g3bBooksFiles.length ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">GSTR-3B PDF(s)</p>
          <p className="text-[11px] text-tx3 mt-1">
            {g3bBooksFiles.length
              ? `${g3bBooksFiles.length} file(s) selected`
              : '1 month or up to 12 months'}
          </p>
          <input ref={g3bBooksRef} type="file" accept=".pdf" multiple className="hidden"
            onChange={e => setG3bBooksFiles(Array.from(e.target.files ?? []))} />
        </div>

        <div className="hidden sm:flex items-center justify-center px-2">
          <span className="text-[10px] font-mono text-tx3">vs</span>
        </div>

        {/* Books Excel */}
        <div
          onClick={() => booksRef.current?.click()}
          className={`flex-1 rounded-xl border-2 border-dashed p-5 cursor-pointer transition-all text-center
            ${booksFile ? 'border-ok/50 bg-ok/5' : 'border-border hover:border-acc/50 bg-sub/30'}`}
        >
          <Upload size={18} className={`mx-auto mb-2 ${booksFile ? 'text-ok' : 'text-tx3'}`} />
          <p className="text-xs font-semibold text-tx">Books Excel / CSV</p>
          <p className="text-[11px] text-tx3 mt-1">
            {booksFile ? booksFile.name : 'Click to select (.xlsx or .csv)'}
          </p>
          <input ref={booksRef} type="file" accept=".xlsx,.xls,.csv" className="hidden"
            onChange={e => setBooksFile(e.target.files?.[0] ?? null)} />
        </div>
      </div>

      {g3bBooksStep && <p className="text-[11px] text-acc animate-pulse">{g3bBooksStep}</p>}

      {g3bBooksResult?.summary?.gstin_warning && (
        <div className="flex items-center gap-2 rounded-lg border border-warn/30 bg-warn/5 px-3 py-2">
          <AlertTriangle size={13} className="text-warn flex-shrink-0" />
          <p className="text-[11px] text-warn">{g3bBooksResult.summary.gstin_warning}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={runGstr3bBooksReconciliation}
          disabled={g3bBooksLoading || !g3bBooksFiles.length || !booksFile}
          className="inline-flex items-center gap-2 px-4 h-9 rounded-xl text-white text-sm font-semibold
            disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:opacity-90 shadow-sm"
          style={{ background: 'linear-gradient(to right, var(--color-acc), #e57373)' }}
        >
          {g3bBooksLoading
            ? <><RefreshCw size={14} className="animate-spin" /> Processing…</>
            : <><GitCompare size={14} /> Run Reconciliation</>}
        </button>

        {g3bBooksResult && (
          <button
            onClick={downloadG3bBooksExcel}
            disabled={g3bBooksDownloading}
            className="inline-flex items-center gap-2 px-4 h-9 rounded-xl border border-border bg-surf
              text-tx text-sm font-semibold hover:bg-sub transition-all disabled:opacity-50"
          >
            {g3bBooksDownloading
              ? <><RefreshCw size={14} className="animate-spin" /> Preparing…</>
              : <><Download size={14} /> Download Excel</>}
          </button>
        )}
        {g3bBooksResult?.g3b_extracted?.length > 0 && (
  <>
    <button
      onClick={() => setShowG3bBooksExtracted(v => !v)}
      className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
        text-xs font-semibold text-tx hover:bg-sub transition-all"
    >
      {showG3bBooksExtracted ? '▲' : '▼'} View GSTR-3B Data
    </button>
    <button
      onClick={async () => {
        setDownloadingG3bTables(true)
        try {
          const res = await fetch(`${API_BASE}/api/tables_excel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              datasets: [{ records: g3bBooksResult.g3b_extracted, returnType: 'GSTR-3B' }]
            }),
          })
          if (!res.ok) throw new Error('Download failed')
          const blob = await res.blob()
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `GSTR3B_Tables_${new Date().toISOString().slice(0,10)}.xlsx`
          a.click()
          URL.revokeObjectURL(url)
        } catch {
          setG3bBooksError('Table download failed. Please try again.')
        } finally {
          setDownloadingG3bTables(false)
        }
      }}
      disabled={downloadingG3bTables}
      className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl border border-border
        text-xs font-semibold text-tx hover:bg-sub transition-all disabled:opacity-50"
    >
      <Download size={13} /> {downloadingG3bTables ? 'Preparing…' : 'Download Tables'}
    </button>
  </>
)}
        {(g3bBooksFiles.length > 0 || booksFile || g3bBooksResult) && (
  <button
    onClick={() => {
      setG3bBooksFiles([]); setBooksFile(null); setG3bBooksResult(null); setG3bBooksError(null)
      setShowG3bBooksExtracted(false); setG3bBooksSummary(null)
    }}
    className="inline-flex items-center gap-1.5 px-3 h-9 rounded-xl text-tx3
      hover:text-err hover:bg-err/5 text-xs transition-all ml-auto"
  >
    <X size={13} /> Clear
  </button>
)}
      </div>
    </div>

    {g3bBooksError && (
      <div className="flex items-start gap-2.5 rounded-xl border border-err/30 bg-err/5 px-4 py-3">
        <AlertCircle size={15} className="text-err flex-shrink-0 mt-0.5" />
        <p className="text-xs text-err">{g3bBooksError}</p>
      </div>
    )}
    
    {g3bBooksResult && (
      <div className="space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Months',          value: g3bBooksResult.summary?.months ?? 0,      color: 'text-tx'  },
            { label: 'Matched',         value: g3bBooksResult.summary?.matched ?? 0,     color: 'text-ok'  },
            { label: 'Mismatches',      value: g3bBooksResult.summary?.mismatches ?? 0,  color: 'text-err' },
          ].map(stat => (
            <div key={stat.label} className="bg-surf rounded-xl border border-border p-3 shadow-sm">
              <div className={`text-lg font-bold tabular-nums ${stat.color}`}>{stat.value}</div>
              <div className="text-[10px] text-tx3 font-medium uppercase tracking-wide mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
        {(g3bBooksResult.monthly ?? []).length > 1 && (
        <Gstr3bBooksAnnualSummary periods={g3bBooksResult.monthly ?? []} />
        )}
        {/* Monthly breakdown — separated per-month cards, matching GSTR-1 vs 3B style */}
        <div className="space-y-3">
          {(g3bBooksResult.monthly ?? []).map((period: any, i: number) => (
            <Gstr3bBooksPeriodCard
              key={period.period}
              period={period}
              defaultOpen={(g3bBooksResult.monthly ?? []).length === 1 || period.overall_status !== 'Matched' || i === 0}
            />
          ))}
        </div>
      </div>
    )}
    {showG3bBooksExtracted && g3bBooksResult?.g3b_extracted?.length > 0 && (
  <div className="bg-surf rounded-2xl border border-border shadow-soft p-4">
    <p className="text-xs font-semibold text-tx mb-3">GSTR-3B Extracted Data</p>
    <ExtractedDataViewer summary={g3bBooksSummary} loading={g3bBooksSummarizing} />
  </div>
)}
    {!g3bBooksResult && !g3bBooksLoading && !g3bBooksError && (
      <div className="rounded-2xl border border-dashed border-border bg-surf/40 p-10 text-center">
        <GitCompare size={28} className="mx-auto text-tx3 mb-3" />
        <p className="text-sm font-medium text-tx2">Upload files to begin</p>
        <p className="text-xs text-tx3 mt-1">Select GSTR-3B PDFs and your Books Excel file above</p>
      </div>
    )}
  </div>
)}

    </div>
  )
}