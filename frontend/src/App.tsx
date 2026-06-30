import { useState, useRef, useEffect } from 'react'
import Footer from './components/Footer'
import AppHeader from './components/Header'
import ReconciliationPage from './components/ReconciliationPage'
import AppSidebar from './components/Sidebar'
import { Download, CheckCircle, ChevronDown, BarChart3, Filter, X, Check, ArrowUpDown, ChevronsDown, ChevronsUp, Upload } from 'lucide-react'
type ParseResult = Record<string, any> & { filename?: string, __error__?: string }

// Environment-based API base URL: prefers VITE_API_BASE, otherwise infer dev vs prod
const inferDefaultApiBase = () => {
  if (typeof window === 'undefined') return ''
  const port = window.location.port
  const devPorts = new Set(['5173','5174','5175','5176','5177','3000'])
  return devPorts.has(port) ? 'http://127.0.0.1:8000' : window.location.origin
}
const API_BASE: string = (import.meta.env.VITE_API_BASE as string) || inferDefaultApiBase()

// UploadCard — no dropdowns; return type and file format are auto-detected in onProcess
function UploadCard({ onProcess, onFilesSelected, progressDone = 0, progressTotal = 0 }: {
  onProcess: (files: File[]) => void,
  onFilesSelected?: (files: File[]) => void,
  progressDone?: number,
  progressTotal?: number
}) {
  const [files, setFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement|null>(null)
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      const f = Array.from(e.dataTransfer.files)
      setFiles(f)
      onFilesSelected?.(f)
    }
  }

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  const f = e.target.files ? Array.from(e.target.files) : []
  setFiles(f)
  onFilesSelected?.(f)
  e.target.value = ''   // reset so re-selecting the same file still fires onChange next time
}

  // Progress bar: show only while in-flight (done < total), hide when complete
  const safeDone = Math.min(progressDone, progressTotal)
  const pct = progressTotal ? Math.min(100, Math.round((safeDone / progressTotal) * 100)) : 0
  const showProgress = progressTotal > 0 && progressDone < progressTotal
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`mx-6 border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center transition-all min-h-[18rem] ${isDragging ? 'border-acc/60 bg-acc/5 dark:border-acc/60 dark:bg-acc/10' : 'border-border bg-surf'} hover:border-acc/50 cursor-pointer`}
    >
      <div className="mx-auto mb-4 w-16 h-16 rounded-2xl bg-gradient-to-br from-acc/15 to-acc/5 flex items-center justify-center">
        <Upload className="w-8 h-8 text-acc" />
      </div>
      <p className="text-tx3 mb-1 text-sm font-medium">Drag and drop files here or select manually</p>
      <p className="text-tx3 mb-4 text-xs">Return type and format are detected automatically</p>
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-2 sm:gap-3 w-full">
        <button
          className="inline-flex items-center justify-center gap-2 w-full sm:w-44 h-11 px-4 rounded-xl border border-border bg-surf text-tx hover:bg-sub shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-4 h-4" /> <span className="font-semibold">Choose Files</span>
        </button>
        <button
          className="inline-flex items-center justify-center gap-2 w-full sm:w-44 h-11 px-4 rounded-xl text-white hover:opacity-90 shadow-lg shadow-acc/15 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer hover:shadow-xl"
          style={{ background: 'linear-gradient(to right, var(--color-acc) 0%, #e57373 100%)' }}
          onClick={() => onProcess(files)}
        >
          <BarChart3 className="w-4 h-4" /> <span className="font-semibold">Extract</span>
        </button>
      </div>
      {/* Accept both PDF and JSON — type is detected at extraction time */}
      <input ref={fileInputRef} className="hidden" type="file" multiple accept=".pdf,.json" onChange={handleSelect} />
      {files.length > 0 && (
        <p className="mt-3 text-sm text-tx3">{files.length} file(s) selected</p>
      )}

      {/* Progress bar — only shown while extraction is in flight */}
      {showProgress && (
        <div className="mt-6">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-3 rounded-full overflow-hidden bg-sub">
              <div className="h-3 bg-[#0ea5a3] rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <div className="text-sm text-tx2 whitespace-nowrap">{safeDone}/{progressTotal}</div>
          </div>
        </div>
      )}
    </div>
  )
}

function ResultsTabs({ results, includeFailedInExcel = true, returnType, selectedCategories, loading, refreshNonce = 0, prefOpen = false }: { results: ParseResult[], includeFailedInExcel?: boolean, returnType: 'GSTR-1'|'GSTR-3B', selectedCategories: string[], loading: boolean, refreshNonce?: number, prefOpen?: boolean }) {
  // Dropdown filter for tables shown (from preferences), persisted per return type
  const [filterOpen, setFilterOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement|null>(null)
  const tablesDropdownRef = useRef<HTMLDivElement|null>(null)
  const [displayedTables, setDisplayedTables] = useState<string[]>([...selectedCategories])
  // Persist collapsed per table label across filter changes
  const [collapsedMap, setCollapsedMap] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(`pref_collapsed_map_${returnType}`)
      if (raw) {
        const obj = JSON.parse(raw)
        if (obj && typeof obj === 'object') return obj
      }
    } catch {}
    return {}
  })
  // Toggle to control whether Excel uses only filtered tables or all from preferences
  const [, setExportOnlyFiltered] = useState<boolean>(() => {
    try {
      const key = `pref_export_only_filtered_${returnType}`
      const raw = localStorage.getItem(key)
      if (raw === 'true' || raw === 'false') return raw === 'true'
    } catch {}
    return true
  })
  const [, setSummaryLoading] = useState(false)
  const [summaryData, setSummaryData] = useState<null | {
    returnType: 'GSTR-1'|'GSTR-3B'
    columns: string[]
    sections: Array<{ heading: string, categories: Array<{ name: string, rows?: Array<{ description: string, key: string, column_index?: number|null, values: any[] }>, subcategories?: Array<{ name: string, rows: Array<{ description: string, key: string, column_index?: number|null, values: any[] }> }> }> }>
  }>(null)
  const lastSummarizedLenRef = useRef(0)

  // Close dropdown when clicking outside or pressing Escape
  useEffect(() => {
    if (!filterOpen) return
    const onClick = (e: Event) => {
      const el = filterRef.current
      if (el && !el.contains(e.target as Node)) setFilterOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setFilterOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('touchstart', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('touchstart', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [filterOpen])


  // Persist filter selection only when results exist; clear when none
  useEffect(() => {
    const key = `pref_displayed_tables_${returnType}`
    try {
      if (results.length) {
        localStorage.setItem(key, JSON.stringify(displayedTables))
      } else {
        localStorage.removeItem(key)
      }
    } catch {}
  }, [displayedTables, returnType, results.length])

  // Persist collapsed map for tables per return type
  useEffect(() => {
    try { localStorage.setItem(`pref_collapsed_map_${returnType}`, JSON.stringify(collapsedMap)) } catch {}
  }, [collapsedMap, returnType])

  // Reload collapsed map on return type change
  useEffect(() => {
    try {
      const raw = localStorage.getItem(`pref_collapsed_map_${returnType}`)
      if (raw) {
        const obj = JSON.parse(raw)
        if (obj && typeof obj === 'object') setCollapsedMap(obj)
        else setCollapsedMap({})
      } else {
        setCollapsedMap({})
      }
    } catch {
      setCollapsedMap({})
    }
  }, [returnType])

  // Clear data in all tabs when starting a new upload or while loading
  useEffect(() => {
    if (loading || !results.length) {
      setSummaryData(null)
      setSummaryLoading(false)
      setEditedSummary(null)
    }
  }, [loading, results.length])

  // Force clear on triggered refresh (e.g., Save Preferences click)
  useEffect(() => {
    if (results.length) {
      setSummaryData(null)
      setEditedSummary(null)
    }
  }, [refreshNonce])

  // When preferences change, clear current tables so they reload with new selection
    useEffect(() => {
      setDisplayedTables([...selectedCategories])
      setSummaryData(null)
      setEditedSummary(null)
    }, [JSON.stringify(selectedCategories), returnType, results.length])

  const downloadTablesExcel = async (useFiltered?: boolean) => {
    if (!results.length) return
    try {
      const selectedCatsForExport = useFiltered ? displayedTables : selectedCategories
      const payload = {
        records: includeFailedInExcel ? results : results.filter(r=>!r.__error__),
        returnType,
        selectedCategories: selectedCatsForExport,
        summaryOverride: editedSummary || undefined,
      }
      const res = await fetch(`${API_BASE}/api/tables_excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'multi_tables.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download tables failed', e)
    }
  }

  // Persist toggle per return type and reload on return type change
  useEffect(() => {
    try {
      const key = `pref_export_only_filtered_${returnType}`
      const raw = localStorage.getItem(key)
      if (raw === 'true' || raw === 'false') setExportOnlyFiltered(raw === 'true')
      else setExportOnlyFiltered(true)
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [returnType])

  const downloadSingleTableExcel = async (categoryName: string) => {
    if (!results.length) return
    try {
      const payload = {
        records: includeFailedInExcel ? results : results.filter(r=>!r.__error__),
        returnType,
        selectedCategories: [categoryName],
        summaryOverride: editedSummary || undefined,
      }
      const res = await fetch(`${API_BASE}/api/tables_excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${categoryName.replace(/\s+/g,'_').toLowerCase()}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download single table failed', e)
    }
  }

  // Tables split-button dropdown handlers (accessible menu)
  const [tablesMenuOpen, setTablesMenuOpen] = useState(false)
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!tablesDropdownRef.current) return
      if (!tablesDropdownRef.current.contains(e.target as Node)) {
        setTablesMenuOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setTablesMenuOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  // Auto-generate multi-level tables once processing completes or preferences change
  useEffect(() => {
    const run = async () => {
      if (!results.length || loading) return
      setSummaryLoading(true)
      try {
        const payload = {
          records: includeFailedInExcel ? results : results.filter(r=>!r.__error__),
          returnType,
          selectedCategories,
        }
        const res = await fetch(`${API_BASE}/api/summarize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const data = await res.json()
        setSummaryData(data)
        try { setEditedSummary(JSON.parse(JSON.stringify(data))) } catch { setEditedSummary(data) }
        lastSummarizedLenRef.current = results.length
      } catch (e) {
        console.error('Auto summarize failed', e)
      } finally {
        setSummaryLoading(false)
      }
    }
    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, results, returnType, includeFailedInExcel, JSON.stringify(selectedCategories), refreshNonce])

  // Month sorting helpers (April..March) with wildcard detection
  const monthOrder = ['april','may','june','july','august','september','october','november','december','january','february','march']
  const monthSynonyms: Record<string, string[]> = {
    april: ['apr','april'],
    may: ['may'],
    june: ['jun','june'],
    july: ['jul','july'],
    august: ['aug','august'],
    september: ['sep','sept','september'],
    october: ['oct','october'],
    november: ['nov','november'],
    december: ['dec','december'],
    january: ['jan','january'],
    february: ['feb','february'],
    march: ['mar','march'],
  }

  function EditableTable({ columns, rows, label, onDownloadExcel, collapsed: collapsedProp, onCollapseToggle, prefOpen }: { columns: string[], rows: Array<{ description?: string, key?: string, values: any[], column_index?: number|null }>, label?: string, onDownloadExcel?: (label: string) => void, collapsed?: boolean, onCollapseToggle?: (v:boolean)=>void, prefOpen?: boolean }) {
    const [tableRows, setTableRows] = useState(rows.map(r => ({ ...r, values: [...(r.values||[])] })))
    const [sortRowIdx, setSortRowIdx] = useState<number|null>(null)
    const [sortDir, setSortDir] = useState<'asc'|'desc'>('desc')
    const [collapsed, setCollapsed] = useState(!!collapsedProp)
    const isCollapsed = typeof collapsedProp === 'boolean' ? collapsedProp : collapsed
    const baseSortedIdx = computeSortedIndices(columns)
    const sortedIdx = (() => {
      if (sortRowIdx === null) return baseSortedIdx
      const values = (tableRows[sortRowIdx]?.values || [])
      const toNum = (v: any) => {
        if (v === null || v === undefined) return NaN
        if (typeof v === 'number') return Number.isFinite(v) ? v : NaN
        if (typeof v === 'string') {
          const s = v.replace(/,/g,'').trim()
          const n = Number(s)
          return Number.isFinite(n) ? n : NaN
        }
        return NaN
      }
      return [...baseSortedIdx].sort((a, b) => {
        const va = toNum(values[a])
        const vb = toNum(values[b])
        const cmp = (va - vb)
        return sortDir === 'asc' ? cmp : -cmp
      })
    })()
    useEffect(() => {
      setTableRows(rows.map(r => ({ ...r, values: [...(r.values||[])] })))
    }, [rows, columns.join('|')])

    const toNumber = (v: any) => {
      if (v === null || v === undefined) return NaN
      if (typeof v === 'number') return Number.isFinite(v) ? v : NaN
      if (typeof v === 'string') {
        const s = v.replace(/,/g,'').trim()
        const n = Number(s)
        return Number.isFinite(n) ? n : NaN
      }
      return NaN
    }
    const columnTotals = tableRows.map((row) => {
      let sum = 0
      for (const ci of sortedIdx) {
        const val = (row.values || [])[ci]
        const n = toNumber(val)
        if (Number.isFinite(n)) sum += n
      }
      return sum
    })

    const MAX_BODY_ROWS = 13
    const rowsExceedLimit = (sortedIdx.length + 1) > MAX_BODY_ROWS
    const TITLE_BAR_H = 28
    const HEADER_H = 28
    const ROW_H = 22
    const maxHeightPx = TITLE_BAR_H + HEADER_H + ROW_H * MAX_BODY_ROWS

    return (
      <div className="min-w-[48rem] text-xs rounded-2xl shadow-sm bg-surf">
        <div className="overflow-x-auto overflow-y-auto" style={{ maxHeight: rowsExceedLimit ? maxHeightPx : undefined }}>
        {label ? (
          <div className="sticky top-0 z-10 px-6 py-1 border-b border-border bg-sub/80 backdrop-blur-md text-sm font-semibold text-tx flex items-center justify-between">
            <span className="truncate" title={label}>{label}</span>
            <div className="flex items-center gap-2">
              <div className={`relative group ${prefOpen ? 'hidden' : ''}`}>
                <button
                  onClick={() => { const next = !isCollapsed; if (onCollapseToggle) { onCollapseToggle(next) } else { setCollapsed(next) } }}
                  aria-label={isCollapsed ? "Expand table" : "Collapse table"}
                  className="p-1 rounded cursor-pointer hover:bg-neutral-200/70 dark:hover:bg-neutral-600/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc"
                >
                  <ChevronDown className={`w-4 h-4 transition-transform ${isCollapsed ? 'rotate-0' : 'rotate-180'}`} strokeWidth={2.5} />
                </button>
                <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
                  {isCollapsed ? 'Expand table' : 'Collapse table'}
                </div>
              </div>
              <div className="relative group">
                <button
                  onClick={() => { if (onDownloadExcel && label) onDownloadExcel(label) }}
                  aria-label="Download table"
                  className={`relative z-0 p-1 rounded cursor-pointer hover:bg-neutral-200/70 dark:hover:bg-neutral-600/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc ${prefOpen ? 'opacity-0 pointer-events-none' : ''}`}
                >
                  <Download className="w-4 h-4" strokeWidth={2.5} />
                </button>
                <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
                  Download table
                </div>
              </div>
            </div>
          </div>
        ) : null}
        {!isCollapsed && (
        <Table className="min-w-full w-full">
          <TableHeader className="sticky top-[2rem] z-10 border-b dark:border-neutral-700 bg-surf/95 backdrop-blur-md">
            <TableRow>
              <TableHead className="sticky top-[2rem] left-0 z-10 px-1 py-[2px] text-sm font-semibold bg-surf/95 backdrop-blur-md">Period</TableHead>
              {tableRows.map((row, ri) => (
                <TableHead
                  key={ri}
                  onClick={() => { setSortRowIdx(prev => prev === ri ? null : ri); setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc')) }}
                  className="sticky top-[2rem] z-[5] px-1 py-[2px] text-sm font-semibold bg-surf/95 backdrop-blur-md cursor-pointer select-none text-right"
                  title="Click to sort columns by this row"
                >
                  <span className="inline-flex items-center gap-1 justify-end w-full">
                    {row.description || row.key}
                    {sortRowIdx === ri && <ArrowUpDown className={`w-3.5 h-3.5 ${sortDir === 'asc' ? 'rotate-180' : ''}`} />}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-border">
            {sortedIdx.map((ci) => (
              <TableRow key={ci} className="odd:bg-surf even:bg-sub/50 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all">
                <TableCell className="px-1 py-[2px] sticky left-0 bg-surf whitespace-nowrap z-10"><span className="text-[11px] leading-[1.1] text-tx">{columns[ci] || 'Period'}</span></TableCell>
                {tableRows.map((row, ri) => {
                  const val = (row.values || [])[ci]
                  const isNum = Number.isFinite(toNumber(val))
                  return (
                    <TableCell key={ri} className={`px-1 py-[2px] ${isNum ? 'text-right tabular-nums' : ''}`}>
                      <span className="text-[11px] leading-[1.1] text-tx">{fmt(val)}</span>
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
            <TableRow className="bg-sub">
              <TableCell className="px-1 py-[2px] text-xs font-semibold sticky left-0 bg-sub whitespace-nowrap z-10">Total</TableCell>
              {columnTotals.map((tot, ri) => (
                <TableCell key={`tot-${ri}`} className="px-1 py-[2px] text-right tabular-nums">
                  <span className="text-[11px] font-semibold text-tx">{fmt(tot)}</span>
                </TableCell>
              ))}
            </TableRow>
          </TableBody>
        </Table>
        )}
        </div>
      </div>
    )
  }

  const detectMonthIndex = (label: string): number | null => {
    const lc = String(label).toLowerCase()
    for (let i = 0; i < monthOrder.length; i++) {
      const m = monthOrder[i]
      const syns = monthSynonyms[m]
      for (const s of syns) {
        if (lc.includes(s)) return i
      }
    }
    return null
  }
  const computeSortedIndices = (cols: string[]): number[] => {
    const items = cols.map((c, idx) => ({ idx, c, m: detectMonthIndex(c) }))
    const known = items.filter(it => it.m !== null)
    const unknown = items.filter(it => it.m === null)
    known.sort((a, b) => (a.m! - b.m!) || (a.idx - b.idx))
    return [...known.map(k=>k.idx), ...unknown.map(u=>u.idx)]
  }
  const numberFmt = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
  const fmt = (v: any) => {
    if (v == null) return ''
    if (typeof v === 'number' && isFinite(v)) return numberFmt.format(v)
    if (typeof v === 'string') {
      const n = Number(v.replace(/,/g, ''))
      if (!Number.isNaN(n) && isFinite(n)) return numberFmt.format(n)
      return v
    }
    return String(v)
  }

  // Edited summary snapshot used to preserve changes in Excel export
  const [editedSummary, setEditedSummary] = useState<any|null>(null)

  // Helpers for filter dropdown
  const toggleTable = (name: string) => {
    setDisplayedTables(prev => prev.includes(name) ? prev.filter(c => c !== name) : [...prev, name])
  }
  const selectAllTables = () => setDisplayedTables([...selectedCategories])
  const deselectAllTables = () => setDisplayedTables([])

  const getDisplayedTitles = (): string[] => {
    if (!summaryData) return []
    const titles: string[] = []
    for (const section of summaryData.sections) {
      for (const cat of section.categories) {
        if (!selectedCategories.includes(cat.name) || !displayedTables.includes(cat.name)) continue
        const sec = section.heading || 'Section'
        const cn = cat.name || 'Category'
        if ((cat.subcategories || []).length) {
          for (const sub of cat.subcategories || []) {
            const sn = sub.name || ''
            const rawTitle = `${sec} - ${cn} - ${sn}`
            const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
            titles.push(title)
          }
        } else {
          const rawTitle = `${sec} - ${cn}`
          const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
          titles.push(title)
        }
      }
    }
    return titles
  }

  const displayedTitles = getDisplayedTitles()
  const allCollapsed = displayedTitles.length > 0 && displayedTitles.every(t => !!collapsedMap[t])

  const toggleAllTablesCollapsed = () => {
    const target = allCollapsed ? false : true
    setCollapsedMap(prev => {
      const next = { ...prev }
      for (const t of displayedTitles) next[t] = target
      return next
    })
  }

  return (
    <div className="bg-surf rounded-2xl shadow-soft border border-border p-4 sm:p-6 font-inter">
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex-1 hidden sm:block" />
        <div className="relative group">
          <button
            onClick={toggleAllTablesCollapsed}
            aria-label={allCollapsed ? "Expand all tables" : "Collapse all tables"}
            className="inline-flex items-center justify-center p-2 rounded-lg text-tx2 hover:text-tx transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
          >
            {allCollapsed ? <ChevronsDown className="w-5 h-5" strokeWidth={2.5} /> : <ChevronsUp className="w-5 h-5" strokeWidth={2.5} />}
          </button>
          <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
            {allCollapsed ? 'Expand all' : 'Collapse all'}
          </div>
        </div>
        <div className="relative group" ref={filterRef} style={{ display: results.length ? 'block' : 'none' }}>
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            aria-label="Filter tables"
            className="inline-flex items-center justify-center p-2 rounded-lg text-tx2 hover:text-tx transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
          >
            <Filter className="w-5 h-5" strokeWidth={2.5} />
          </button>
          <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">Filter tables</div>
          {filterOpen && (
            <div className="absolute right-0 z-40 mt-2 mb-4 rounded-xl border border-border bg-surf shadow-soft p-3"
                 style={{ minWidth: `${Math.max(...selectedCategories.map(c => String(c).length), 24) + 8}ch` }}>
              {(() => {
                const allSelected = selectedCategories.length > 0 && displayedTables.length === selectedCategories.length
                const noneSelected = displayedTables.length === 0
                return (
                  <div className="flex items-center justify-between mb-2">
                    <div role="group" aria-label="Select range" className="inline-flex rounded-2xl border border-border overflow-hidden mx-2">
                      <button
                        onClick={selectAllTables}
                        className={`text-xs font-semibold px-2 py-0.5 cursor-pointer ${allSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                      >
                        All
                      </button>
                      <button
                        onClick={deselectAllTables}
                        className={`text-xs font-semibold px-2 py-0.5 border-l border-border cursor-pointer ${noneSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                      >
                        None
                      </button>
                    </div>
                  </div>
                )
              })()}
              <div className="max-h-64 overflow-y-auto space-y-0.5 mb-2">
                {selectedCategories.length === 0 ? (
                  <div className="px-2 py-1 text-xs text-tx3">
                    No matching tables for current preferences. Adjust selections under Preferences.
                  </div>
                ) : (
                  selectedCategories.map((cat) => {
                    const checked = displayedTables.includes(cat)
                    return (
                      <label key={cat} className="flex items-center gap-1.5 text-sm px-2 py-0.5 rounded hover:bg-sub cursor-pointer whitespace-nowrap">
                        <input type="checkbox" className="sr-only" checked={checked} onChange={() => toggleTable(cat)} />
                        <Check className={`w-4 h-4 ${checked ? 'text-[#0ea5a3]' : 'opacity-0'}`} aria-hidden="true" />
                        <span className="text-tx">{cat}</span>
                      </label>
                    )
                  })
                )}
              </div>
            </div>
          )}
        </div>
        <div ref={tablesDropdownRef} className={prefOpen ? 'hidden' : 'relative inline-flex w-auto z-30'}>
          <div className="relative group">
            <button
              onClick={() => setTablesMenuOpen(v => !v)}
              aria-label="Download previewed tables"
              aria-haspopup="menu"
              aria-expanded={tablesMenuOpen}
              className="inline-flex items-center justify-center p-2 rounded-lg text-acc hover:opacity-70 transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
            >
              <Download className="w-5 h-5" strokeWidth={2.5} />
            </button>
            <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
              Download previewed tables
            </div>
          </div>
          {tablesMenuOpen && (
            <div
              role="menu"
              aria-label="Tables export options"
              className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-border bg-surf shadow-lg overflow-hidden shadow-soft z-[100] max-h-48 overflow-y-auto"
            >
              <ul className="py-1 px-1 space-y-1">
                <li>
                  <button
                    role="menuitem"
                    tabIndex={0}
                    onClick={() => { setExportOnlyFiltered(true); setTablesMenuOpen(false); downloadTablesExcel(true); }}
                    className="w-full text-left px-3 py-1.5 rounded-lg text-sm text-tx hover:bg-sub cursor-pointer whitespace-nowrap"
                  >
                    Download filtered tables only
                  </button>
                </li>
                <li>
                  <button
                    role="menuitem"
                    tabIndex={0}
                    onClick={() => { setExportOnlyFiltered(false); setTablesMenuOpen(false); downloadTablesExcel(false); }}
                    className="w-full text-left px-3 py-1.5 rounded-lg text-sm text-tx hover:bg-sub cursor-pointer whitespace-nowrap"
                  >
                    Download all preferred tables
                  </button>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
      {!results.length && <p className="text-sm text-tx3">No results yet.</p>}
      {!!results.length && (
        <div className="space-y-6">
          <>
            <h3 className="text-base font-semibold text-tx">Preview results</h3>
            <div className="text-xs text-tx3">Choose preferred tables from the Preferences menu to refine the list.</div>
            {!summaryData && (
              <div className="rounded-xl border border-border bg-surf p-4 text-sm text-tx2">
                Tables will appear here after processing.
              </div>
            )}
            {summaryData && (
              <div className="space-y-6">
                {displayedTables.length === 0 && (
                  <div className="rounded-xl border border-border bg-surf p-3 text-sm text-tx2">
                    {selectedCategories.length === 0
                      ? 'No matching tables for current preferences. Adjust selections under Preferences.'
                      : 'No tables selected. Use Filter or Preferences to choose tables.'}
                  </div>
                )}
                {summaryData.sections.map((section, si) => {
                  const visibleCats = (section.categories || []).filter((cat) => displayedTables.includes(String(cat.name || '')))
                  if (!visibleCats.length) return null
                  return (
                    <div key={si} className="space-y-3">
                      {visibleCats.map((cat, ci) => (
                        <div key={ci} className="space-y-2">
                          {/* Mobile list view (transposed) */}
                          <div className="md:hidden space-y-2">
                            {(() => {
                              const sortedIdx = computeSortedIndices(summaryData.columns)
                              if (cat.subcategories) {
                                return cat.subcategories.map((sub, subi) => (
                                  <div key={subi} className="space-y-2">
                                    {(() => {
                                      const sec = section.heading || 'Section'
                                      const cn = cat.name || 'Category'
                                      const sn = sub.name || ''
                                      const rawTitle = `${sec} - ${cn} - ${sn}`
                                      const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                                      return (<div className="font-semibold text-tx">{title}</div>)
                                    })()}
                                    {sortedIdx.map((ci) => (
                                      <div key={ci} className="rounded-xl border bg-surf dark:border-neutral-700 p-3 shadow-md hover:shadow-lg transition-all">
                                        <div className="font-medium mb-2 text-tx">{summaryData.columns[ci] || 'Period'}</div>
                                        <div className="space-y-1">
                                          {sub.rows.map((row, ri) => (
                                            <div key={ri} className="flex items-center justify-between text-xs">
                                              <span className="text-tx3 whitespace-nowrap mr-2">{row.description || row.key}</span>
                                              <span className="font-medium whitespace-nowrap text-tx text-right tabular-nums">{fmt((row.values || [])[ci])}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ))
                              }
                              const rows = cat.rows || []
                              const sec = section.heading || 'Section'
                              const cn = cat.name || 'Category'
                              const rawTitle = `${sec} - ${cn}`
                              const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                              return (
                                <div className="space-y-2">
                                  <div className="font-semibold text-tx">{title}</div>
                                  {sortedIdx.map((ci) => (
                                    <div key={ci} className="rounded-xl border bg-surf dark:border-neutral-700 p-3 shadow-md hover:shadow-lg transition-all">
                                      <div className="font-medium mb-2 text-tx">{summaryData.columns[ci] || 'Period'}</div>
                                      <div className="space-y-1">
                                        {rows.map((row, ri) => (
                                          <div key={ri} className="flex items-center justify-between text-xs">
                                            <span className="text-tx3 whitespace-nowrap mr-2">{row.description || row.key}</span>
                                            <span className="font-medium whitespace-nowrap text-tx text-right tabular-nums">{fmt((row.values || [])[ci])}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )
                            })()}
                          </div>
                          {/* Desktop/tablet table (transposed) */}
                          <div className="hidden md:block relative w-full max-w-full min-w-0 overflow-x-auto scrollbar-thin scrollbar-thumb-neutral-300 dark:scrollbar-thumb-neutral-700">
                            {(() => {
                              if (cat.subcategories) {
                                return cat.subcategories.map((sub, subi) => {
                                  const sec = section.heading || 'Section'
                                  const cn = cat.name || 'Category'
                                  const sn = sub.name || ''
                                  const rawTitle = `${sec} - ${cn} - ${sn}`
                                  const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                                  return (
                                    <div key={subi} className="mb-8">
                                      <EditableTable
                                        columns={summaryData.columns}
                                        rows={sub.rows}
                                        label={title}
                                        onDownloadExcel={() => downloadSingleTableExcel(String(cat.name || '').trim())}
                                        collapsed={!!collapsedMap[title]}
                                        onCollapseToggle={(next) => setCollapsedMap(prev => ({ ...prev, [title]: next }))}
                                        prefOpen={prefOpen}
                                      />
                                    </div>
                                  )
                                })
                              }
                              const rows = cat.rows || []
                              const sec = section.heading || 'Section'
                              const cn = cat.name || 'Category'
                              const rawTitle = `${sec} - ${cn}`
                              const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                              return (
                                <div className="mb-8">
                                  <EditableTable
                                    columns={summaryData.columns}
                                    rows={rows}
                                    label={title}
                                    onDownloadExcel={() => downloadSingleTableExcel(String(cat.name || '').trim())}
                                    collapsed={!!collapsedMap[title]}
                                    onCollapseToggle={(next) => setCollapsedMap(prev => ({ ...prev, [title]: next }))}
                                    prefOpen={prefOpen}
                                  />
                                </div>
                              )
                            })()}
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                })}
              </div>
            )}
          </>
        </div>
      )}
    </div>
  )
}

import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './components/ui/table'

// Auto-detect return type and file format from a single File object
async function detectReturnTypeAndFormat(file: File): Promise<{ returnType: 'GSTR-1'|'GSTR-3B'|'GSTR-2B', fileFormat: 'PDF'|'JSON' }> {
  const name = file.name.toLowerCase()

  // Detect format by extension
  const isJson = name.endsWith('.json')
  const fileFormat: 'PDF'|'JSON' = isJson ? 'JSON' : 'PDF'

  if (!isJson) {
    // For PDFs, detect return type from filename keywords
    if (name.includes('gstr1') || name.includes('gstr-1') || name.includes('gstr_1')) {
      return { returnType: 'GSTR-1', fileFormat }
    }
    if (name.includes('gstr2b') || name.includes('gstr-2b') || name.includes('gstr_2b')) {
      return { returnType: 'GSTR-2B', fileFormat: 'PDF' }
    }
    // Default PDF to GSTR-3B
    return { returnType: 'GSTR-3B', fileFormat }
  }

  // For JSON, inspect content to detect type
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    // GSTR-2B typically has 'data.docDtls' or specific 2B keys
    if (data?.data?.docDtls || data?.docDtls || name.includes('2b')) {
      return { returnType: 'GSTR-2B', fileFormat }
    }
    // GSTR-1 has b2b, b2cl, cdnr etc at root or under data
    const payload = data?.data ?? data
    if (payload?.b2b !== undefined || payload?.b2cl !== undefined || payload?.cdnr !== undefined || payload?.exp !== undefined) {
      return { returnType: 'GSTR-1', fileFormat }
    }
    // GSTR-3B has sup_details or inward_sup
    if (payload?.sup_details !== undefined || payload?.inward_sup !== undefined || payload?.itc_elg !== undefined) {
      return { returnType: 'GSTR-3B', fileFormat }
    }
  } catch {
    // If JSON parse fails, fall through to filename check
  }

  // Filename fallback for JSON
  if (name.includes('gstr1') || name.includes('gstr-1')) return { returnType: 'GSTR-1', fileFormat }
  if (name.includes('gstr2b') || name.includes('gstr-2b') || name.includes('2b')) return { returnType: 'GSTR-2B', fileFormat }
  return { returnType: 'GSTR-3B', fileFormat }
}

function App() {
  const [theme, setTheme] = useState<'light'|'dark'|'system'>(() => {
    try {
      const t = localStorage.getItem('theme')
      if (t === 'light' || t === 'dark' || t === 'system') return t
    } catch {}
    return 'system'
  })
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('sidebar_open')
      if (v === 'true') return true
      if (v === 'false') return false
    } catch {}
    return false
  })
  const [activeView, setActiveView] = useState<'upload' | 'reconciliation'>('upload')
  const [prefOpen, setPrefOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ParseResult[]>([])
  const [progress, setProgress] = useState<{done:number,total:number}>({done:0,total:0})
  const [includeFailedInExcel] = useState(true)
  const [lastReturnType, setLastReturnType] = useState<'GSTR-1'|'GSTR-3B'|'GSTR-2B'>('GSTR-3B')
  const [selectedTables, setSelectedTables] = useState<{['GSTR-1']: string[], ['GSTR-3B']: string[]}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [schemaStructure, setSchemaStructure] = useState<{['GSTR-1']: Array<{ heading: string, categories: Array<{ name: string, subcategories?: string[] }> }>, ['GSTR-3B']: Array<{ heading: string, categories: Array<{ name: string, subcategories?: string[] }> }>}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [activeSettingsTab, setActiveSettingsTab] = useState<'GSTR-1'|'GSTR-3B'>('GSTR-1')
  const [draftSelectedTables, setDraftSelectedTables] = useState<{['GSTR-1']: string[], ['GSTR-3B']: string[]}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [expandedSections, setExpandedSections] = useState<{['GSTR-1']: Record<string, boolean>, ['GSTR-3B']: Record<string, boolean>}>({ 'GSTR-1': {}, 'GSTR-3B': {} })
  const [showToast, setShowToast] = useState(false)
  const [toastText, setToastText] = useState<string>('')
  const [refreshNonce, setRefreshNonce] = useState(0)
  const prefModalRef = useRef<HTMLDivElement|null>(null)
  const prevFocusedElRef = useRef<HTMLElement|null>(null)
  const abortControllerRef = useRef<AbortController|null>(null)
  const processIdRef = useRef(0)
  

  // Lock page scroll when Preferences modal is open
  useEffect(() => {
    try {
      const html = document.documentElement
      const body = document.body
      if (prefOpen) {
        html.style.overflow = 'hidden'
        body.style.overflow = 'hidden'
      } else {
        html.style.overflow = ''
        body.style.overflow = ''
      }
    } catch {}
    return () => {
      try {
        document.documentElement.style.overflow = ''
        document.body.style.overflow = ''
      } catch {}
    }
  }, [prefOpen])

  // Focus trap and Escape to close for Preferences modal
  useEffect(() => {
    if (!prefOpen) {
      try { prevFocusedElRef.current?.focus() } catch {}
      return
    }
    prevFocusedElRef.current = document.activeElement as HTMLElement | null
    const container = prefModalRef.current
    if (!container) return
    const focusableSelectors = [
      'a[href]', 'area[href]', 'input:not([disabled])', 'select:not([disabled])', 'textarea:not([disabled])',
      'button:not([disabled])', 'iframe', 'object', 'embed', '[contenteditable]', '[tabindex]:not([tabindex="-1"])'
    ].join(', ')
    const focusables = Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors)).filter(el => el.offsetParent !== null)
    const first = focusables[0] || container
    try { first.focus() } catch {}
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        try { setDraftSelectedTables(selectedTables) } catch {}
        setPrefOpen(false)
        return
      }
      if (e.key === 'Tab') {
        if (!focusables.length) return
        const active = document.activeElement as HTMLElement
        const idx = focusables.indexOf(active)
        if (e.shiftKey) {
          if (idx <= 0) { e.preventDefault(); focusables[focusables.length - 1].focus() }
        } else {
          if (idx === focusables.length - 1) { e.preventDefault(); focusables[0].focus() }
        }
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [prefOpen])

  // Persist sidebar open/collapse state
  useEffect(() => {
    try { localStorage.setItem('sidebar_open', sidebarOpen ? 'true' : 'false') } catch {}
  }, [sidebarOpen])

  // Apply theme and persist
  useEffect(() => {
    const apply = () => {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      const isDark = theme === 'dark' || (theme === 'system' && prefersDark)
      const root = document.documentElement
      root.classList.toggle('dark', isDark)
      root.setAttribute('data-theme', isDark ? 'dark' : 'light')
      try { localStorage.setItem('theme', theme) } catch {}
    }
    apply()
    const mm = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
    const onChange = () => { if (theme === 'system') apply() }
    mm?.addEventListener('change', onChange)
    return () => mm?.removeEventListener('change', onChange)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  useEffect(() => {
    const loadPrefs = (rt: 'GSTR-1'|'GSTR-3B', cats: string[]) => {
      const key = rt === 'GSTR-1' ? 'pref_tables_gstr1' : 'pref_tables_gstr3b'
      try {
        const saved = localStorage.getItem(key)
        if (saved) {
          const arr = JSON.parse(saved)
          if (Array.isArray(arr)) return arr.filter((c: string) => cats.includes(c))
        }
      } catch {}
      return cats
    }
    const fetchCategories = async () => {
      try {
        const resCats = await fetch(`${API_BASE}/api/schema_categories`)
        const dataCats = await resCats.json()
        const g1 = (dataCats['GSTR-1']?.categories ?? []) as string[]
        const g3b = (dataCats['GSTR-3B']?.categories ?? []) as string[]
        setSelectedTables({ 'GSTR-1': loadPrefs('GSTR-1', g1), 'GSTR-3B': loadPrefs('GSTR-3B', g3b) })
        const resStruct = await fetch(`${API_BASE}/api/schema_structure`)
        const dataStruct = await resStruct.json()
        setSchemaStructure({ 'GSTR-1': dataStruct['GSTR-1'] ?? [], 'GSTR-3B': dataStruct['GSTR-3B'] ?? [] })
        setDraftSelectedTables({ 'GSTR-1': loadPrefs('GSTR-1', g1), 'GSTR-3B': loadPrefs('GSTR-3B', g3b) })
        setExpandedSections({
          'GSTR-1': Object.fromEntries((dataStruct['GSTR-1'] ?? []).map((s: any) => [s.heading || 'Section', false])),
          'GSTR-3B': Object.fromEntries((dataStruct['GSTR-3B'] ?? []).map((s: any) => [s.heading || 'Section', false])),
        })
      } catch (e) {
        console.error('Failed to load schema categories', e)
      }
    }
    fetchCategories()
  }, [])

  const toggleCategoryDraft = (rt: 'GSTR-1'|'GSTR-3B', cat: string) => {
    setDraftSelectedTables(prev => {
      const current = new Set(prev[rt])
      if (current.has(cat)) current.delete(cat); else current.add(cat)
      return { ...prev, [rt]: Array.from(current) }
    })
  }

  const setSectionSelection = (rt: 'GSTR-1'|'GSTR-3B', heading: string, selectAll: boolean) => {
    const section = (schemaStructure[rt] || []).find(s => (s.heading || 'Section') === heading)
    const cats = section ? section.categories.map(c => c.name) : []
    setDraftSelectedTables(prev => {
      const current = new Set(prev[rt])
      if (selectAll) { cats.forEach(c => current.add(c)) } else { cats.forEach(c => current.delete(c)) }
      return { ...prev, [rt]: Array.from(current) }
    })
  }

  const toggleExpand = (rt: 'GSTR-1'|'GSTR-3B', heading: string) => {
    setExpandedSections(prev => ({ ...prev, [rt]: { ...prev[rt], [heading]: !prev[rt][heading] } }))
  }

  const toggleAllExpanded = (rt: 'GSTR-1'|'GSTR-3B') => {
    const sections = schemaStructure[rt] || []
    const headings = sections.map(s => s.heading || 'Section')
    const allOpen = headings.length > 0 && headings.every(h => !!expandedSections[rt]?.[h])
    setExpandedSections(prev => ({ ...prev, [rt]: Object.fromEntries(headings.map(h => [h, !allOpen])) }))
  }

  const savePreferences = () => {
    setSelectedTables(draftSelectedTables)
    try {
      localStorage.setItem('pref_tables_gstr1', JSON.stringify(draftSelectedTables['GSTR-1']))
      localStorage.setItem('pref_tables_gstr3b', JSON.stringify(draftSelectedTables['GSTR-3B']))
    } catch {}
    setRefreshNonce(n => n + 1)
    setToastText('Preferences saved')
    setShowToast(true)
    setTimeout(() => setShowToast(false), 1600)
  }

  const cancelPreferences = () => {
    setDraftSelectedTables(selectedTables)
  }

    // Auto-detect return type and format per file, then process
  const onProcess = async (files: File[]) => {
    if (!files.length) {
      setToastText('Select returns to extract')
      setShowToast(true)
      setTimeout(() => setShowToast(false), 1600)
      return
    }

    const myId = ++processIdRef.current
    try { abortControllerRef.current?.abort() } catch {}
    abortControllerRef.current = new AbortController()
    const signal = abortControllerRef.current.signal

    setLoading(true)
    setResults([])
    setProgress({ done: 0, total: files.length })
    let dominantSet = false

    try {
      const allResults: ParseResult[] = []
      const tasks = files.map(async (file) => {
  try {
    const { returnType, fileFormat } = await detectReturnTypeAndFormat(file)
    if (!dominantSet) {
      dominantSet = true
      setLastReturnType(returnType)
    }

    let res: Response
    if (fileFormat === 'PDF') {
            const form = new FormData()
            form.append('file', file)
            const url = returnType === 'GSTR-1'
              ? `${API_BASE}/api/gstr1/pdf`
              : `${API_BASE}/api/gstr3b/pdf`
            res = await fetch(url, { method: 'POST', body: form, signal })
          } else {
            const text = await file.text()
            let payload: any
            try { payload = JSON.parse(text) } catch { throw new Error('Invalid JSON file') }
            const url = returnType === 'GSTR-1'
              ? `${API_BASE}/api/gstr1/json`
              : returnType === 'GSTR-2B'
              ? `${API_BASE}/api/gstr2b/json`
              : `${API_BASE}/api/gstr3b/json`
            res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal })
          }

          const data = await res.json()
          allResults.push({ ...data, filename: file.name })
        } catch (err: any) {
          allResults.push({ filename: file.name, __error__: err?.message || 'Failed to process file' })
        } finally {
          if (processIdRef.current === myId) {
            setProgress(prev => ({ done: prev.done + 1, total: prev.total }))
          }
        }
      })

      await Promise.all(tasks)

      if (processIdRef.current === myId) {
        setResults(allResults)
        setRefreshNonce(n => n + 1)
      }
    } catch (e) {
      console.error(e)
    } finally {
      if (processIdRef.current === myId) {
        setLoading(false)
      }
      abortControllerRef.current = null
    }
  }

  // Download raw parsed data (JSON -> Excel)
  const downloadExcel = async () => {
    if (!results.length) return
    const res = await fetch(`${API_BASE}/api/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(includeFailedInExcel ? results : results.filter(r => !r.__error__))
    })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'returns_data.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen flex font-inter text-tx bg-bg">
      <AppSidebar
        activeView={activeView}
        onSelectView={setActiveView}
        isCollapsed={!sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      <div className="flex-1 min-w-0 flex flex-col">
        <AppHeader theme={theme} onToggleTheme={toggleTheme} statusLabel={results.length ? `${results.length} file(s) processed` : null} />
        <div className="flex-1 space-y-4 sm:space-y-6 py-4 sm:py-6">
          {activeView === 'upload' && (
  <>
    <UploadCard
      onProcess={onProcess}
      onFilesSelected={() => {
        try { abortControllerRef.current?.abort() } catch {}
        abortControllerRef.current = null
        processIdRef.current++
        setResults([])
        setProgress({ done: 0, total: 0 })
        setLoading(false)
      }}
      progressDone={progress.done}
      progressTotal={progress.total}
    />
    <div className="space-y-3">
      <div className="mx-6 bg-white rounded-2xl shadow-soft border border-neutral-200 px-6 py-4 dark:bg-neutral-800 dark:border-neutral-700">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-start sm:justify-between gap-2 sm:gap-0 max-w-full overflow-hidden">
          <div className="text-sm font-semibold text-tx">Raw Data Export</div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative group">
              <button
                onClick={downloadExcel}
                aria-label="Download raw data"
                disabled={!(progress.total > 0 && progress.done >= progress.total)}
                className="inline-flex items-center justify-center p-2 rounded-lg text-[#0ea5a3] hover:text-[#0ea5a3]/80 transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0ea5a3] disabled:opacity-60 disabled:cursor-not-allowed w-auto cursor-pointer"
              >
                <Download className="w-5 h-5" strokeWidth={2.5} />
              </button>
              <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap z-40">
                Download the extracted returns as a single table
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div className="mx-6 flex justify-end">
      <button
        onClick={() => setPrefOpen(true)}
        className="inline-flex items-center gap-2 px-4 h-9 rounded-xl border border-border bg-surf text-tx text-xs font-semibold hover:bg-sub transition cursor-pointer"
      >
        <ChevronsDown className="w-4 h-4" /> Preferences
      </button>
    </div>
    <div className="mx-6">
      <ResultsTabs
        results={results}
        includeFailedInExcel={includeFailedInExcel}
        returnType={lastReturnType === 'GSTR-2B' ? 'GSTR-3B' : lastReturnType}
        selectedCategories={selectedTables[lastReturnType === 'GSTR-2B' ? 'GSTR-3B' : lastReturnType] ?? []}
        loading={loading}
        refreshNonce={refreshNonce}
        prefOpen={prefOpen}
      />
    </div>
  </>
)}

        {activeView === 'reconciliation' && <ReconciliationPage />}
{/* RECONCILIATION VIEW */}

          {/* Preferences Floating Modal */}
          {prefOpen && (
            <div className="fixed inset-0 z-50">
              <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => { cancelPreferences(); setPrefOpen(false) }} />
              <div
                ref={prefModalRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="preferences-title"
                tabIndex={-1}
                className="relative mt-10 mx-auto w-[calc(100%-2rem)] sm:w-auto max-w-4xl bg-surf border border-border rounded-2xl shadow-xl flex flex-col max-h-[85vh] overflow-hidden"
              >
                <div className="px-8 py-6 border-b border-border">
                  <div className="flex items-center justify-between">
                    <h2 id="preferences-title" className="text-2xl font-semibold">Preferences</h2>
                    <div className="relative group">
                      <button
                        aria-label="Close preferences"
                        className="inline-flex items-center justify-center p-2 rounded-lg bg-transparent text-tx2 hover:text-tx transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
                        onClick={() => { cancelPreferences(); setPrefOpen(false) }}
                      >
                        <X className="w-5 h-5" strokeWidth={2.5} />
                      </button>
                      <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
                        Close
                      </div>
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-tx3">Choose the tables to be extracted from the given list. Your preferences will be saved.</div>
                  <div className="mt-3 flex items-center">
                    <div className="flex-1"></div>
                    <div className="flex-1 flex justify-center">
                      <div className="relative inline-flex items-center w-64 h-10 rounded-3xl border border-border bg-surf/70 shadow-sm overflow-hidden">
                        <span
                          className="absolute top-0 left-0 h-full w-1/2 rounded-3xl transition-transform duration-300"
                          style={{ background: 'linear-gradient(to right, rgba(154,51,36,0.12), rgba(229,115,115,0.15))', transform: activeSettingsTab === 'GSTR-3B' ? 'translateX(100%)' : 'translateX(0%)' }}
                        />
                        <button onClick={() => setActiveSettingsTab('GSTR-1')} className={`relative z-10 flex-1 h-full text-sm font-medium ${activeSettingsTab === 'GSTR-1' ? 'text-acc' : 'text-tx2'} cursor-pointer`}>GSTR-1</button>
                        <button onClick={() => setActiveSettingsTab('GSTR-3B')} className={`relative z-10 flex-1 h-full text-sm font-medium ${activeSettingsTab === 'GSTR-3B' ? 'text-acc' : 'text-tx2'} cursor-pointer`}>GSTR-3B</button>
                      </div>
                    </div>
                    <div className="flex-1 flex justify-end items-center gap-2">
                      {(() => {
                        const allCats = (schemaStructure[activeSettingsTab] || []).flatMap(s => (s.categories || []).map(c => c.name))
                        const allSelected = allCats.length > 0 && (draftSelectedTables[activeSettingsTab] || []).length === allCats.length
                        const noneSelected = (draftSelectedTables[activeSettingsTab] || []).length === 0
                        return (
                          <div role="group" aria-label="Select range" className="inline-flex rounded-2xl border border-border overflow-hidden">
                            <button
                              onClick={() => setDraftSelectedTables(prev => ({ ...prev, [activeSettingsTab]: allCats }))}
                              className={`text-xs font-semibold px-2 py-0.5 cursor-pointer ${allSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                            >All</button>
                            <button
                              onClick={() => setDraftSelectedTables(prev => ({ ...prev, [activeSettingsTab]: [] }))}
                              className={`text-xs font-semibold px-2 py-0.5 border-l border-border cursor-pointer ${noneSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                            >None</button>
                          </div>
                        )
                      })()}
                      <div className="relative group">
                        <button
                          onClick={() => toggleAllExpanded(activeSettingsTab)}
                          aria-label={(() => {
                            const headings = (schemaStructure[activeSettingsTab] || []).map(s => s.heading || 'Section')
                            return headings.length > 0 && headings.every(h => !!expandedSections[activeSettingsTab]?.[h]) ? 'Collapse All' : 'Expand All'
                          })()}
                          className="inline-flex items-center justify-center p-2 rounded-lg text-acc hover:opacity-70 transition transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
                        >
                          {(() => {
                            const headings = (schemaStructure[activeSettingsTab] || []).map(s => s.heading || 'Section')
                            const allOpen = headings.length > 0 && headings.every(h => !!expandedSections[activeSettingsTab]?.[h])
                            return allOpen ? <ChevronsUp className="w-5 h-5" strokeWidth={2.5} /> : <ChevronsDown className="w-5 h-5" strokeWidth={2.5} />
                          })()}
                        </button>
                        <div className="absolute right-0 top-full mt-1 px-2 py-1 rounded-md text-xs bg-neutral-900 text-white opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-40">
                          {(() => {
                            const headings = (schemaStructure[activeSettingsTab] || []).map(s => s.heading || 'Section')
                            return headings.length > 0 && headings.every(h => !!expandedSections[activeSettingsTab]?.[h]) ? 'Collapse all sections' : 'Expand all sections'
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto px-8 py-6 space-y-4">
                  {(schemaStructure[activeSettingsTab] || []).map((section, si) => {
                    const heading = section.heading || 'Section'
                    const isOpen = expandedSections[activeSettingsTab][heading]
                    return (
                      <div key={si} className="rounded-xl border border-border shadow">
                        <div
                          className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-sub cursor-pointer"
                          role="button"
                          aria-expanded={isOpen}
                          tabIndex={0}
                          onClick={() => toggleExpand(activeSettingsTab, heading)}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(activeSettingsTab, heading) } }}
                        >
                          <div className="inline-flex items-center gap-2">
                            <span className="text-sm font-medium text-tx">{heading}</span>
                            <ChevronDown className={`w-5 h-5 text-tx3 transition-transform ${isOpen ? 'rotate-180' : 'rotate-0'}`} strokeWidth={2.5} />
                          </div>
                          {(() => {
                            const catsInSection = (section.categories || []).map(c => c.name)
                            const selectedCount = catsInSection.filter(name => draftSelectedTables[activeSettingsTab].includes(name)).length
                            const allSelected = catsInSection.length > 0 && selectedCount === catsInSection.length
                            const noneSelected = selectedCount === 0
                            return (
                              <div role="group" aria-label="Select range" className="inline-flex rounded-2xl border border-border overflow-hidden" onClick={(e) => e.stopPropagation()}>
                                <button
                                  onClick={() => setSectionSelection(activeSettingsTab, heading, true)}
                                  className={`text-xs font-semibold px-2 py-0.5 cursor-pointer ${allSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                                >All</button>
                                <button
                                  onClick={() => setSectionSelection(activeSettingsTab, heading, false)}
                                  className={`text-xs font-semibold px-2 py-0.5 border-l border-border cursor-pointer ${noneSelected ? 'bg-[#0ea5a3] text-white' : 'bg-transparent text-tx hover:bg-sub'}`}
                                >None</button>
                              </div>
                            )
                          })()}
                        </div>
                        {isOpen && (
                          <div className="px-4 pb-3">
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                              {section.categories.map((cat, ci) => (
                                <label key={ci} className="flex items-center gap-2 rounded-lg border border-border bg-surf p-2 hover:shadow hover:border-border2 transition-all cursor-pointer">
                                  <input type="checkbox" className="sr-only" checked={draftSelectedTables[activeSettingsTab].includes(cat.name)} onChange={() => toggleCategoryDraft(activeSettingsTab, cat.name)} />
                                  <Check className={`w-4 h-4 shrink-0 ${draftSelectedTables[activeSettingsTab].includes(cat.name) ? 'text-[#0ea5a3]' : 'opacity-0'}`} aria-hidden="true" />
                                  <span className="font-medium text-xs text-tx">{cat.name}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                  <p className="text-xs text-tx3">Selections follow the original schema order and are saved per return type.</p>
                </div>
                <div className="px-8 py-6 border-t border-border bg-surf/60 flex items-center justify-end gap-2">
                  <button
                    className="inline-flex items-center justify-center gap-2 px-4 h-11 text-sm rounded-xl border border-border bg-surf text-tx hover:bg-sub shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer"
                    onClick={() => { cancelPreferences(); setPrefOpen(false) }}
                  >Cancel</button>
                  <button
                    className="inline-flex items-center justify-center gap-2 px-4 h-11 text-sm rounded-xl text-white hover:opacity-90 shadow-lg shadow-acc/15 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acc cursor-pointer hover:shadow-xl"
                    style={{ background: 'linear-gradient(to right, var(--color-acc) 0%, #e57373 100%)' }}
                    onClick={() => { savePreferences(); setPrefOpen(false) }}
                  >Save Preferences</button>
                </div>
              </div>
            </div>
          )}
        </div>
        <Footer />
      </div>
      {showToast && (
        <div className="fixed bottom-5 right-5 z-[60]">
          <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-[#14b8a6] text-white shadow-lg shadow-[#14b8a6]/20 border border-[#14b8a6]">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm font-medium">{toastText}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default App