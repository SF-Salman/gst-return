import { useState, useRef, useEffect } from 'react'
import Footer from './components/Footer'
import { Upload, Settings, ChevronLeft, ChevronRight, Download, CheckCircle, ChevronDown, HelpCircle, AlertTriangle, Sun, Moon, BarChart3 } from 'lucide-react'

type ParseResult = Record<string, any> & { filename?: string, __error__?: string }

// Environment-based API base URL: prefers VITE_API_BASE, otherwise infer dev vs prod
const inferDefaultApiBase = () => {
  if (typeof window === 'undefined') return ''
  const port = window.location.port
  const devPorts = new Set(['5173','5174','5175','5176','5177','3000'])
  return devPorts.has(port) ? 'http://127.0.0.1:8000' : window.location.origin
}
const API_BASE: string = (import.meta.env.VITE_API_BASE as string) || inferDefaultApiBase()

function TopBar({ theme, onToggleTheme }: { theme: 'light'|'dark'|'system', onToggleTheme: ()=>void }) {
  return (
    <div className="sticky top-0 z-40 bg-white/95 dark:bg-neutral-800/95 backdrop-blur border-b border-neutral-200 dark:border-neutral-700 shadow-sm">
      <div className="mx-auto max-w-7xl px-3 sm:px-4 py-2 sm:py-3 flex items-center justify-between gap-2 sm:gap-3">
        <div className="flex items-center gap-2 sm:gap-3">
          <img src="/icon.png" alt="Logo" className="w-7 h-7 sm:w-8 sm:h-8 rounded-full shadow-sm" />
          <span className="font-poppins font-semibold text-lg sm:text-xl tracking-tight text-neutral-900 dark:text-neutral-100">GST Returns Extractor</span>
        </div>
        <div className="flex items-center gap-1">
          {(() => {
            const prefersDark = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            const isDarkActive = theme === 'dark' || (theme === 'system' && prefersDark)
            return (
              <button
                aria-label={isDarkActive ? 'Switch to light theme' : 'Switch to dark theme'}
                title={isDarkActive ? 'Light' : 'Dark'}
                onClick={() => { console.log('TopBar: toggle button clicked'); onToggleTheme(); }}
                aria-pressed={isDarkActive}
                className="p-2 text-sm rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-all duration-200 ease-out hover:shadow-md active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 group"
              >
                {isDarkActive ? <Sun className="w-4 h-4 transition-transform duration-200 group-hover:rotate-12" /> : <Moon className="w-4 h-4 transition-transform duration-200 group-hover:rotate-12" />}
              </button>
            )
          })()}
        </div>
      </div>
    </div>
  )
}

function Sidebar({ open, onToggle, activeView, onSelectView }: { open: boolean, onToggle: ()=>void, activeView: 'upload'|'preferences'|'help'|'disclaimer', onSelectView: (v:'upload'|'preferences'|'help'|'disclaimer')=>void }) {
  return (
    <aside className={`hidden md:block ${open ? 'w-56' : 'w-16'} flex-none transition-all duration-300 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 shadow-soft rounded-r-xl relative`}> 
      <nav className="flex flex-col py-4">
        <button
          aria-label="Toggle sidebar"
          onClick={onToggle}
          className="absolute -right-3 top-4 p-2 rounded-full bg-indigo-600 text-white shadow-lg transition transform active:scale-95 hover:bg-indigo-700"
        >
          {open ? <ChevronLeft className="w-4 h-4 transition-transform" /> : <ChevronRight className="w-4 h-4 transition-transform" />}
        </button>
        <button
          onClick={()=>onSelectView('upload')}
          className={`flex items-center gap-3 mx-2 px-3 py-2 text-sm rounded-lg transition ${activeView==='upload' ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}
        >
          <Upload className="w-5 h-5" />
          {open && <span>Upload</span>}
        </button>
        <button
          onClick={()=>onSelectView('preferences')}
          className={`flex items-center gap-3 mx-2 px-3 py-2 text-sm rounded-lg transition ${activeView==='preferences' ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}
        >
          <Settings className="w-5 h-5" />
          {open && <span>Preferences</span>}
        </button>
        <button
          onClick={()=>onSelectView('help')}
          className={`flex items-center gap-3 mx-2 px-3 py-2 text-sm rounded-lg transition ${activeView==='help' ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}
        >
          <HelpCircle className="w-5 h-5" />
          {open && <span>Help</span>}
        </button>
        <button
          onClick={()=>onSelectView('disclaimer')}
          className={`flex items-center gap-3 mx-2 px-3 py-2 text-sm rounded-lg transition ${activeView==='disclaimer' ? 'bg-indigo-50 text-indigo-700 shadow-sm dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}
        >
          <AlertTriangle className="w-5 h-5" />
          {open && <span>Disclaimer</span>}
        </button>
      </nav>
    </aside>
  )
}

function MobileNav({ activeView, onSelectView }: { activeView: 'upload'|'preferences'|'help'|'disclaimer', onSelectView: (v:'upload'|'preferences'|'help'|'disclaimer')=>void }) {
  return (
    <div className="md:hidden bg-white dark:bg-neutral-800 rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 p-3">
      <div className="flex gap-2">
        <button onClick={()=>onSelectView('upload')} className={`flex-1 px-3 py-2 text-sm rounded-lg border ${activeView==='upload' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}>Upload</button>
        <button onClick={()=>onSelectView('preferences')} className={`flex-1 px-3 py-2 text-sm rounded-lg border ${activeView==='preferences' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}>Preferences</button>
        <button onClick={()=>onSelectView('help')} className={`flex-1 px-3 py-2 text-sm rounded-lg border ${activeView==='help' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}>Help</button>
        <button onClick={()=>onSelectView('disclaimer')} className={`flex-1 px-3 py-2 text-sm rounded-lg border ${activeView==='disclaimer' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}>Disclaimer</button>
      </div>
    </div>
  )
}

// Removed unused Dropdown component

// Split button style dropdown with fixed width and attached arrow button
function SplitDropdown({ value, options, onChange, widthClass = 'w-44' }: { value: string, options: string[], onChange: (v: string)=>void, widthClass?: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement|null>(null)
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!ref.current) return
      if (!ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])
  return (
    <div className={`relative inline-flex ${widthClass}`} ref={ref}>
      <button type="button"
        className="flex-1 inline-flex items-center justify-between px-3 py-2 text-sm rounded-l-lg border border-neutral-300 bg-white hover:bg-neutral-100 shadow-sm transition-colors dark:border-neutral-700 dark:bg-neutral-800 dark:hover:bg-neutral-700"
        aria-haspopup="menu" aria-expanded={open}
      >
        <span className="text-neutral-800 dark:text-neutral-200 truncate">{value}</span>
      </button>
      <button type="button" onClick={()=>setOpen(v=>!v)}
        className="px-2 py-2 text-sm rounded-r-lg border border-l-0 border-neutral-300 bg-white hover:bg-neutral-100 shadow-sm transition-colors dark:border-neutral-700 dark:bg-neutral-800 dark:hover:bg-neutral-700"
        aria-label="Toggle dropdown"
      >
        {/* minimal down arrow icon */}
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div role="menu" className="absolute left-0 right-0 z-50 mt-2 w-full min-w-full rounded-xl border border-neutral-200 bg-white shadow-lg overflow-hidden dark:border-neutral-700 dark:bg-neutral-800 shadow-soft">
          <ul className="py-1">
            {options.map(opt => (
              <li key={opt}>
                <button className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors text-neutral-800 dark:text-neutral-200" onClick={()=>{ onChange(opt); setOpen(false) }}>
                  {opt}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
function ProgressBar({ done, total, loading }: { done:number, total:number, loading:boolean }) {
  if (!total) return null
  const pct = total ? Math.round((done/total)*100) : 0
  return (
    <div className="bg-white rounded-2xl shadow-soft border border-neutral-200 p-4 dark:bg-neutral-800 dark:border-neutral-700">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
          <div className="h-3 bg-emerald-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="text-sm text-neutral-700 dark:text-neutral-300 whitespace-nowrap">{done}/{total}</div>
        {!loading && done===total && (
          <CheckCircle className="w-5 h-5 text-emerald-600" />
        )}
      </div>
    </div>
  )
}

function UploadCard({ onProcess, onFilesSelected }: { onProcess: (files: File[], returnType: 'GSTR-1'|'GSTR-3B', fileFormat: 'PDF'|'JSON') => void, onFilesSelected?: (files: File[]) => void }) {
  const [files, setFiles] = useState<File[]>([])
  const [returnType, setReturnType] = useState<'GSTR-1'|'GSTR-3B'>('GSTR-3B')
  const [fileFormat, setFileFormat] = useState<'PDF'|'JSON'>('PDF')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement|null>(null)

  // Restore Type/Format selection from localStorage
  useEffect(() => {
    try {
      const savedRT = localStorage.getItem('pref_returnType')
      if (savedRT === 'GSTR-1' || savedRT === 'GSTR-3B') setReturnType(savedRT as any)
    } catch {}
    try {
      const savedFF = localStorage.getItem('pref_fileFormat')
      if (savedFF === 'PDF' || savedFF === 'JSON') setFileFormat(savedFF as any)
    } catch {}
  }, [])

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
  }

  return (
    <div className="bg-white rounded-2xl shadow-soft border border-neutral-200 p-4 sm:p-6 dark:bg-neutral-800 dark:border-neutral-700">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-4">
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full sm:w-auto">
          <SplitDropdown value={returnType} options={['GSTR-1','GSTR-3B']} onChange={(v)=>{ setReturnType(v as any); try { localStorage.setItem('pref_returnType', v) } catch {} }} widthClass="w-full sm:w-44" />
          <SplitDropdown value={fileFormat} options={['PDF','JSON']} onChange={(v)=>{ setFileFormat(v as any); try { localStorage.setItem('pref_fileFormat', v) } catch {} }} widthClass="w-full sm:w-44" />
        </div>
      </div>
      <div
        onDragOver={(e)=>{e.preventDefault(); setIsDragging(true)}}
        onDragLeave={()=>setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-6 sm:p-10 text-center ${isDragging ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-900/30' : 'border-neutral-300 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800'}`}
      >
        <p className="text-neutral-700 dark:text-neutral-300 mb-3 text-sm">Drag and drop files here or select manually</p>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-2 sm:gap-3 w-full">
          <button className="inline-flex items-center justify-center gap-2 w-full sm:w-40 px-4 py-2 text-sm rounded-lg border bg-white hover:bg-neutral-50 shadow-sm transition dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200 dark:hover:bg-neutral-700" onClick={()=>fileInputRef.current?.click()}>
            <Upload className="w-4 h-4" /> Choose Files
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 w-full sm:w-40 bg-indigo-600 text-white rounded-lg px-4 py-2 text-sm hover:bg-indigo-700 shadow-sm transition"
            onClick={()=>onProcess(files, returnType, fileFormat)}
          >
          <BarChart3 className="w-4 h-4" /> Extract
          </button>
        </div>
        <input ref={fileInputRef} className="hidden" type="file" multiple accept={fileFormat==='PDF' ? '.pdf' : '.json'} onChange={handleSelect} />
        {files.length > 0 && (
          <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">{files.length} file(s) selected</p>
        )}
      </div>
    </div>
  )
}

function ResultsTabs({ results, includeFailedInExcel = true, returnType, selectedCategories, loading, refreshNonce = 0 }: { results: ParseResult[], includeFailedInExcel?: boolean, returnType: 'GSTR-1'|'GSTR-3B', selectedCategories: string[], loading: boolean, refreshNonce?: number }) {
  // Dropdown filter for tables shown (from preferences), persisted per return type
  const [filterOpen, setFilterOpen] = useState(false)
  const filterRef = useRef<HTMLDivElement|null>(null)
  const tablesDropdownRef = useRef<HTMLDivElement|null>(null)
  const [displayedTables, setDisplayedTables] = useState<string[]>(() => {
    try {
      const key = `pref_displayed_tables_${returnType}`
      const raw = localStorage.getItem(key)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) return arr.filter((c: string) => selectedCategories.includes(c))
      }
    } catch {}
    return [...selectedCategories]
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

  // Persist filter selection
  useEffect(() => {
    try { localStorage.setItem(`pref_displayed_tables_${returnType}`, JSON.stringify(displayedTables)) } catch {}
  }, [displayedTables, returnType])

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
    // Sync displayed tables with latest selectedCategories; default to all
    setDisplayedTables(prev => {
      const next = prev.filter(c => selectedCategories.includes(c))
      return next.length ? next : [...selectedCategories]
    })
    if (results.length) {
      setSummaryData(null)
    }
  }, [JSON.stringify(selectedCategories), returnType])

  // Removed unused downloadExcel; raw export handled in App

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

  // Removed unused toggleExportOnlyFiltered helper

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

  function EditableTable({ columns, rows, label }: { columns: string[], rows: Array<{ description?: string, key?: string, values: any[], column_index?: number|null }>, label?: string }) {
    const [tableRows, setTableRows] = useState(rows.map(r => ({ ...r, values: [...(r.values||[])] })))
    const sortedIdx = computeSortedIndices(columns)
    useEffect(() => {
      setTableRows(rows.map(r => ({ ...r, values: [...(r.values||[])] })))
    }, [rows, columns.join('|')])
    // Read-only table; editing removed per request

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

    return (
      <div className="min-w-[48rem] text-sm rounded-2xl shadow-sm bg-white dark:bg-neutral-800">
        {label ? (
          <div className="sticky top-0 z-40 px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700 text-sm font-semibold text-neutral-800 dark:text-neutral-100">
            {label}
          </div>
        ) : null}
        <table className="w-full">
          <thead className="sticky top-10 bg-gradient-to-r from-white to-neutral-50 dark:from-neutral-800 dark:to-neutral-700 border-b dark:border-neutral-700 z-30">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-neutral-700 dark:text-neutral-300 sticky left-0 bg-gradient-to-r from-white to-neutral-50 dark:from-neutral-800 dark:to-neutral-700 whitespace-nowrap z-20">Period</th>
              {tableRows.map((row, ri) => (
                <th key={ri} className="text-left px-4 py-3 font-medium text-neutral-700 dark:text-neutral-300 whitespace-nowrap">{row.description || row.key}</th>
              ))}
              {/* Removed summary columns */}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100 dark:divide-neutral-700">
            {sortedIdx.map((ci) => (
              <tr key={ci} className="odd:bg-white even:bg-neutral-50 dark:odd:bg-neutral-800 dark:even:bg-neutral-700 hover:bg-indigo-50/40 dark:hover:bg-indigo-900/30 transition-colors">
                <td className="px-4 py-3 font-medium sticky left-0 bg-white dark:bg-neutral-800 whitespace-nowrap">{columns[ci] || 'Period'}</td>
                {tableRows.map((row, ri) => {
                  const val = (row.values || [])[ci]
                  return (
                    <td key={ri} className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm">{fmt(val)}</span>
                    </td>
                  )
                })}
                {/* Removed right-side summary columns */}
              </tr>
            ))}
            {/* Total row across all periods */}
            <tr className="bg-neutral-100 dark:bg-neutral-700">
              <td className="px-4 py-3 font-semibold sticky left-0 bg-neutral-100 dark:bg-neutral-700 whitespace-nowrap">Total</td>
              {columnTotals.map((tot, ri) => (
                <td key={`tot-${ri}`} className="px-4 py-3 whitespace-nowrap">
                  <span className="font-semibold text-neutral-900 dark:text-neutral-100">{fmt(tot)}</span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
        {/* Read-only table; editing disabled */}
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

  // Removed unused getPeriod/getYear helpers
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

  return (
    <div className="bg-white dark:bg-neutral-800 rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 p-4 sm:p-6 font-inter">
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative" ref={filterRef}>
          <button onClick={()=>setFilterOpen(!filterOpen)} className="w-full sm:w-auto inline-flex items-center gap-2 px-4 py-2 rounded-lg border bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700">
            <ChevronDown className={`w-4 h-4 transition-transform ${filterOpen ? 'rotate-180' : 'rotate-0'}`} /> Filter Tables
          </button>
          {filterOpen && (
            <div className="absolute z-50 mt-2 w-80 rounded-xl border bg-white dark:bg-neutral-800 shadow-soft p-3">
              <div className="flex items-center justify-between mb-2">
                <button onClick={selectAllTables} className="text-xs px-2 py-1 rounded-md border hover:bg-neutral-50 dark:hover:bg-neutral-700">Select All</button>
                <button onClick={deselectAllTables} className="text-xs px-2 py-1 rounded-md border hover:bg-neutral-50 dark:hover:bg-neutral-700">Deselect All</button>
              </div>
              <div className="max-h-64 overflow-y-auto space-y-0.5">
                {selectedCategories.map((cat) => {
                  const checked = displayedTables.includes(cat)
                  return (
                    <label key={cat} className="flex items-center gap-1.5 text-sm px-2 py-0.5 rounded hover:bg-neutral-50 dark:hover:bg-neutral-700 cursor-pointer">
                      <input type="checkbox" className="rounded" checked={checked} onChange={()=>toggleTable(cat)} />
                      <span className="text-neutral-800 dark:text-neutral-200">{cat}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}
        </div>
        <div className="flex-1 hidden sm:block" />
        {/* Split button: Tables with integrated dropdown */}
        <div ref={tablesDropdownRef} className="relative inline-flex w-auto z-[100]">
          <button
            onClick={()=>setTablesMenuOpen(v=>!v)}
            aria-label="Download tables"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-l-lg bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-soft"
          >
            <Download className="w-4 h-4" />
            <span>Tables</span>
          </button>
          <button
            onClick={()=>setTablesMenuOpen(v=>!v)}
            aria-haspopup="menu"
            aria-expanded={tablesMenuOpen}
            aria-label="Tables export options"
            className="inline-flex items-center justify-center px-3 py-2 text-sm rounded-r-lg bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 border-l border-indigo-700/40"
          >
            <ChevronDown className={`w-4 h-4 transition-transform ${tablesMenuOpen ? 'rotate-180' : 'rotate-0'}`} />
          </button>
          {tablesMenuOpen && (
            <div
              role="menu"
              aria-label="Tables export options"
              className="absolute right-0 top-full mt-2 w-64 rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 shadow-soft p-2 z-[120]"
            >
              <button
                role="menuitem"
                tabIndex={0}
                onClick={()=>{ setExportOnlyFiltered(true); setTablesMenuOpen(false); downloadTablesExcel(true); }}
                className="w-full text-left px-3 py-1.5 rounded-md text-sm text-neutral-800 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                Download filtered tables only
              </button>
              <button
                role="menuitem"
                tabIndex={0}
                onClick={()=>{ setExportOnlyFiltered(false); setTablesMenuOpen(false); downloadTablesExcel(false); }}
                className="w-full text-left px-3 py-1.5 rounded-md text-sm text-neutral-800 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                Download all preferred tables
              </button>
            </div>
          )}
        </div>
      </div>
      {!results.length && <p className="text-sm text-neutral-600 dark:text-neutral-300">No results yet.</p>}
      {!!results.length && (
        <div className="space-y-6">
          {/* Summary tab removed */}
            <>
              {/* Hint above tables */}
              <div className="text-xs text-neutral-600 dark:text-neutral-300">Choose preferred tables from the Preferences menu to refine the list.</div>
              {!summaryData && (
                <div className="rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-4 text-sm text-neutral-700 dark:text-neutral-300">
                  Tables will appear here after processing.
                </div>
              )}
              {summaryData && (
                <div className="space-y-6">
                  {displayedTables.length === 0 && (
                    <div className="rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-3 text-sm text-neutral-700 dark:text-neutral-300">No tables selected. Use Filter or Preferences to choose tables.</div>
                  )}
                  {(() => {
                    const anyVisible = summaryData.sections.some((sec: any) => (sec.categories || []).some((cat: any) => displayedTables.includes(String(cat.name || ''))))
                    return anyVisible ? null : (
                      <div className="rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-3 text-sm text-neutral-700 dark:text-neutral-300">No matching tables for current preferences. Adjust selections under Preferences.</div>
                    )
                  })()}
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
                                      return (<div className="font-semibold text-neutral-800 dark:text-neutral-200">{title}</div>)
                                    })()}
                                    {sortedIdx.map((ci) => (
                                      <div key={ci} className="rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-3 shadow-soft">
                                        <div className="font-medium mb-2 text-neutral-800 dark:text-neutral-200">{summaryData.columns[ci] || 'Period'}</div>
                                        <div className="space-y-1">
                                          {sub.rows.map((row, ri) => (
                                            <div key={ri} className="flex items-center justify-between text-xs">
                                              <span className="text-neutral-600 dark:text-neutral-300 whitespace-nowrap mr-2">{row.description || row.key}</span>
                                              <span className="font-medium whitespace-nowrap text-neutral-900 dark:text-neutral-100">{fmt((row.values || [])[ci])}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ))
                              }
                              const rows = cat.rows || []
                              {(() => {
                                const sec = section.heading || 'Section'
                                const cn = cat.name || 'Category'
                                const rawTitle = `${sec} - ${cn}`
                                const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                                return (<div className="font-semibold text-neutral-800 dark:text-neutral-200">{title}</div>)
                              })()}
                              return sortedIdx.map((ci) => (
                                <div key={ci} className="rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-3 shadow-soft">
                                  <div className="font-medium mb-2 text-neutral-800 dark:text-neutral-200">{summaryData.columns[ci] || 'Period'}</div>
                                  <div className="space-y-1">
                                    {rows.map((row, ri) => (
                                      <div key={ri} className="flex items-center justify-between text-xs">
                                        <span className="text-neutral-600 dark:text-neutral-300 whitespace-nowrap mr-2">{row.description || row.key}</span>
                                        <span className="font-medium whitespace-nowrap text-neutral-900 dark:text-neutral-100">{fmt((row.values || [])[ci])}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))
                            })()}
                          </div>
                          {/* Desktop/tablet table (transposed) */}
                          <div className="hidden md:block relative w-full max-w-full min-w-0 overflow-x-scroll overflow-y-auto md:max-h-[28rem]">
                            {(() => {
                              if (cat.subcategories) {
                                return cat.subcategories.map((sub, subi) => {
                                  const sec = section.heading || 'Section'
                                  const cn = cat.name || 'Category'
                                  const sn = sub.name || ''
                                  const rawTitle = `${sec} - ${cn} - ${sn}`
                                  const title = rawTitle.replace(/^[\s-]+|[\s-]+$/g, '')
                                  return (
                                    <div key={subi} className="mb-3">
                                      <EditableTable
                                        columns={summaryData.columns}
                                        rows={sub.rows}
                                        label={title}
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
                                <EditableTable
                                  columns={summaryData.columns}
                                  rows={rows}
                                  label={title}
                                />
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
          {/* JSON tab removed */}
          
        </div>
      )}
    </div>
  )
}


import HelpContent from './components/HelpContent'
import DisclaimerContent from './components/DisclaimerContent'

function App() {
  const [theme, setTheme] = useState<'light'|'dark'|'system'>(() => {
    try {
      const t = localStorage.getItem('theme')
      if (t === 'light' || t === 'dark' || t === 'system') return t
    } catch {}
    return 'system'
  })
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [activeView, setActiveView] = useState<'upload'|'preferences'|'help'|'disclaimer'>(() => {
    try {
      const v = localStorage.getItem('active_view')
      if (v === 'upload' || v === 'preferences' || v === 'help' || v === 'disclaimer') return v as 'upload'|'preferences'|'help'|'disclaimer'
    } catch {}
    return 'upload'
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ParseResult[]>([])
  const [progress, setProgress] = useState<{done:number,total:number}>({done:0,total:0})
  const [includeFailedInExcel] = useState(true)
  const [lastReturnType, setLastReturnType] = useState<'GSTR-1'|'GSTR-3B'>('GSTR-3B')

  // Schema categories and user-selected tables preferences
  // Removed unused schemaCategories state
  const [selectedTables, setSelectedTables] = useState<{['GSTR-1']: string[], ['GSTR-3B']: string[]}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [schemaStructure, setSchemaStructure] = useState<{['GSTR-1']: Array<{ heading: string, categories: Array<{ name: string, subcategories?: string[] }> }>, ['GSTR-3B']: Array<{ heading: string, categories: Array<{ name: string, subcategories?: string[] }> }>}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [activeSettingsTab, setActiveSettingsTab] = useState<'GSTR-1'|'GSTR-3B'>('GSTR-1')
  const [draftSelectedTables, setDraftSelectedTables] = useState<{['GSTR-1']: string[], ['GSTR-3B']: string[]}>({ 'GSTR-1': [], 'GSTR-3B': [] })
  const [expandedSections, setExpandedSections] = useState<{['GSTR-1']: Record<string, boolean>, ['GSTR-3B']: Record<string, boolean>}>({ 'GSTR-1': {}, 'GSTR-3B': {} })
  const [showToast, setShowToast] = useState(false)
  const [refreshNonce, setRefreshNonce] = useState(0)

  // Persist which main view was last active
  useEffect(() => {
    try { localStorage.setItem('active_view', activeView) } catch {}
  }, [activeView])

  // Apply theme and persist
  useEffect(() => {
    const apply = () => {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      const isDark = theme === 'dark' || (theme === 'system' && prefersDark)
      const root = document.documentElement
      root.classList.toggle('dark', isDark)
      root.setAttribute('data-theme', isDark ? 'dark' : 'light')
      try { localStorage.setItem('theme', theme) } catch {}
      console.log('Applied theme:', theme, 'isDark:', isDark)
      console.log('html classes after apply:', root.className)
    }
    apply()
    const mm = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
    const onChange = () => { if (theme === 'system') apply() }
    mm?.addEventListener('change', onChange)
    return () => mm?.removeEventListener('change', onChange)
  }, [theme])

  const toggleTheme = () => {
    console.log('toggleTheme: clicked')
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      console.log('toggleTheme: prev =', prev, 'next =', next)
      return next
    })
  }

  // Debug each render
  useEffect(() => {
    try {
      console.log('render theme:', theme)
      console.log('html classes on render:', document.documentElement.className)
    } catch {}
  })

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
        // Load structured schema for tabulated preferences
    const resStruct = await fetch(`${API_BASE}/api/schema_structure`)
        const dataStruct = await resStruct.json()
        setSchemaStructure({ 'GSTR-1': dataStruct['GSTR-1'] ?? [], 'GSTR-3B': dataStruct['GSTR-3B'] ?? [] })
        // Initialize drafts and expanded states from saved selections
        setDraftSelectedTables({ 'GSTR-1': loadPrefs('GSTR-1', g1), 'GSTR-3B': loadPrefs('GSTR-3B', g3b) })
        // Collapse all sections by default
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
      if (selectAll) {
        cats.forEach(c => current.add(c))
      } else {
        cats.forEach(c => current.delete(c))
      }
      return { ...prev, [rt]: Array.from(current) }
    })
  }

  const toggleExpand = (rt: 'GSTR-1'|'GSTR-3B', heading: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [rt]: { ...prev[rt], [heading]: !prev[rt][heading] }
    }))
  }

  // Toggle all sections for a given return type
  const toggleAllExpanded = (rt: 'GSTR-1'|'GSTR-3B') => {
    const sections = schemaStructure[rt] || []
    const headings = sections.map(s => s.heading || 'Section')
    const allOpen = headings.length > 0 && headings.every(h => !!expandedSections[rt]?.[h])
    setExpandedSections(prev => ({
      ...prev,
      [rt]: Object.fromEntries(headings.map(h => [h, !allOpen]))
    }))
  }

  const savePreferences = () => {
    setSelectedTables(draftSelectedTables)
    try {
      localStorage.setItem('pref_tables_gstr1', JSON.stringify(draftSelectedTables['GSTR-1']))
      localStorage.setItem('pref_tables_gstr3b', JSON.stringify(draftSelectedTables['GSTR-3B']))
    } catch {}
    // Trigger tables reload with latest preferences
    setRefreshNonce(n => n + 1)
    setShowToast(true)
    setTimeout(() => setShowToast(false), 1600)
  }

  const cancelPreferences = () => {
    setDraftSelectedTables(selectedTables)
  }

  

  const onProcess = async (files: File[], returnType: 'GSTR-1'|'GSTR-3B', fileFormat: 'PDF'|'JSON') => {
    if (!files.length) return
    setLoading(true)
    setResults([])
    setProgress({done:0,total:files.length})
    setLastReturnType(returnType)
    try {
      const tasks = files.map(async (file) => {
        try {
          let res: Response
          if (fileFormat === 'PDF') {
            const form = new FormData()
            form.append('file', file)
      const url = returnType === 'GSTR-1' ? `${API_BASE}/api/gstr1/pdf` : `${API_BASE}/api/gstr3b/pdf`
            res = await fetch(url, { method: 'POST', body: form })
          } else {
            const text = await file.text()
            let payload: any
            try { payload = JSON.parse(text) } catch (e) { throw new Error('Invalid JSON file') }
      const url = returnType === 'GSTR-1' ? `${API_BASE}/api/gstr1/json` : `${API_BASE}/api/gstr3b/json`
            res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
          }
          const data = await res.json()
          const enriched = { ...data, filename: file.name }
          setResults(prev => [...prev, enriched])
        } catch (err: any) {
          setResults(prev => [...prev, { filename: file.name, __error__: err?.message || 'Failed to process file' }])
        } finally {
          setProgress(prev => ({ done: prev.done + 1, total: prev.total }))
        }
      })
      await Promise.all(tasks)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  // Download raw parsed data (JSON -> Excel) aligned to progress/status section
  const downloadExcel = async () => {
    if (!results.length) return
        const res = await fetch(`${API_BASE}/api/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(includeFailedInExcel ? results : results.filter(r=>!r.__error__))
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
    <div className="min-h-screen flex flex-col font-inter text-neutral-900 dark:text-neutral-100 bg-neutral-50 dark:bg-neutral-900">
      <TopBar theme={theme} onToggleTheme={toggleTheme} />
      <div className="mx-auto max-w-7xl w-full px-3 sm:px-4 py-4 sm:py-6 flex flex-col md:flex-row gap-4 md:gap-6 flex-1">
        <Sidebar open={sidebarOpen} onToggle={()=>setSidebarOpen(!sidebarOpen)} activeView={activeView} onSelectView={setActiveView} />
        <div className="flex-1 min-w-0 space-y-4 sm:space-y-6">
          <MobileNav activeView={activeView} onSelectView={setActiveView} />
          {activeView === 'upload' && (
            <>
              <UploadCard onProcess={onProcess} onFilesSelected={()=>{
                // Clear all results data immediately on new file selection
                setResults([])
                setProgress({done:0,total:0})
                setLoading(false)
              }} />
              <div className="space-y-3">
                <ProgressBar done={progress.done} total={progress.total} loading={loading} />
                <div className="bg-white rounded-2xl shadow-soft border border-neutral-200 p-4 dark:bg-neutral-800 dark:border-neutral-700">
                  <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200">Raw data Export</div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={downloadExcel}
                        aria-label="Download raw data"
                        disabled={!results.length}
                        aria-disabled={!results.length}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-400 shadow-soft disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        <Download className="w-4 h-4" /> Raw data
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <ResultsTabs results={results} includeFailedInExcel={includeFailedInExcel} returnType={lastReturnType} selectedCategories={selectedTables[lastReturnType]} loading={loading} refreshNonce={refreshNonce} />
            </>
          )}
          {activeView === 'preferences' && (
            <div className="relative">
              <div className="bg-white dark:bg-neutral-800 rounded-2xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-4 sm:p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-sans font-semibold text-base sm:text-lg text-neutral-900 dark:text-neutral-100">Preferences</h2>
                  <div className="flex items-center gap-2">
                    <div className="inline-flex rounded-lg border bg-white dark:bg-neutral-800 shadow-sm overflow-hidden">
                      {(['GSTR-1','GSTR-3B'] as const).map(rt => (
                        <button key={rt} onClick={()=>setActiveSettingsTab(rt)} className={`px-3 py-2 text-sm ${activeSettingsTab===rt ? 'bg-indigo-600 text-white' : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700'}`}>{rt}</button>
                      ))}
                    </div>
                    <button
                      onClick={()=>toggleAllExpanded(activeSettingsTab)}
                      className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 w-36 justify-center whitespace-nowrap"
                    >
                      {(() => {
                        const sections = schemaStructure[activeSettingsTab] || []
                        const headings = sections.map(s => s.heading || 'Section')
                        const allOpen = headings.length > 0 && headings.every(h => !!expandedSections[activeSettingsTab]?.[h])
                        return allOpen ? 'Collapse All' : 'Expand All'
                      })()}
                    </button>
                  </div>
                </div>
                <div className="space-y-4">
                  {(schemaStructure[activeSettingsTab] || []).map((section, si) => {
                    const heading = section.heading || 'Section'
                    const isOpen = expandedSections[activeSettingsTab][heading]
                    return (
                      <div key={si} className="rounded-2xl border border-neutral-200 dark:border-neutral-700 shadow-sm">
                        <button onClick={()=>toggleExpand(activeSettingsTab, heading)} className="w-full flex items-center justify-between px-4 py-3">
                          <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{heading}</span>
                          <ChevronDown className={`w-4 h-4 text-neutral-600 dark:text-neutral-300 transition-transform ${isOpen ? 'rotate-180' : 'rotate-0'}`} />
                        </button>
                        {isOpen && (
                          <div className="px-4 pb-3">
                            <div className="flex items-center justify-end gap-2 mb-2">
                              <button className="text-xs px-2 py-1 rounded-md border hover:bg-neutral-50 dark:hover:bg-neutral-700" onClick={()=>setSectionSelection(activeSettingsTab, heading, true)}>Select All</button>
                              <button className="text-xs px-2 py-1 rounded-md border hover:bg-neutral-50 dark:hover:bg-neutral-700" onClick={()=>setSectionSelection(activeSettingsTab, heading, false)}>Deselect All</button>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                              {section.categories.map((cat, ci) => (
                                <label key={ci} className="flex items-center gap-3 rounded-xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 p-3 hover:shadow-sm transition">
                                  <input type="checkbox" className="accent-indigo-600" checked={draftSelectedTables[activeSettingsTab].includes(cat.name)} onChange={()=>toggleCategoryDraft(activeSettingsTab, cat.name)} />
                                  <span className="font-medium text-sm text-neutral-800 dark:text-neutral-200">{cat.name}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
                <p className="text-xs text-neutral-600 dark:text-neutral-300 mt-3">Selections follow the original schema order and are saved per return type.</p>
              </div>
              {/* Fixed bottom action bar */}
              <div className="fixed left-0 right-0 bottom-0 z-40">
                <div className="mx-auto max-w-7xl px-3 sm:px-4 pb-3">
                  <div className="rounded-2xl border bg-white dark:bg-neutral-800 dark:border-neutral-700 shadow-sm p-3 flex items-center justify-end gap-2">
                    <button className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg border text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700" onClick={cancelPreferences}>Cancel</button>
                    <button className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700" onClick={savePreferences}>Save Preferences</button>
                  </div>
                </div>
              </div>
              {/* Success toast */}
              {showToast && (
                <div className="fixed right-4 bottom-20 z-50">
                  <div className="flex items-center gap-2 bg-emerald-100 text-emerald-800 rounded-lg shadow-sm px-3 py-2 text-sm">
                    <CheckCircle className="w-4 h-4" /> Preferences saved successfully
                  </div>
                </div>
              )}
            </div>
          )}
          {activeView === 'help' && (
            <HelpContent />
          )}
          {activeView === 'disclaimer' && (
            <DisclaimerContent />
          )}
        </div>
      </div>
      <Footer />
    </div>
  )
}

export default App
