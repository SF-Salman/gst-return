import { Sun, Moon,} from 'lucide-react'

interface Props {
  theme: 'light' | 'dark' | 'system'
  onToggleTheme: () => void
  statusLabel?: string | null
}

export default function Header({ theme, onToggleTheme, statusLabel }: Props) {
  const prefersDark = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDarkActive = theme === 'dark' || (theme === 'system' && prefersDark)

  return (
    <header className="h-16 flex items-center justify-between px-4 sm:px-6 bg-surf border-b border-border sticky top-0 z-40">
      <div>  </div>

      <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center select-none">
        <span className="leading-none text-tx font-serif font-semibold text-[1.35rem]">
          GST <span style={{ color: 'var(--color-acc)' }}>Reconciler</span>
        </span>
        <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-tx3 mt-0.5">
          Returns &amp; Reconciliation
        </span>
      </div>

      <div className="flex items-center gap-3">
        {statusLabel && (
          <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] font-mono text-tx3 max-w-[220px] truncate" title={statusLabel}>
            <span className="w-1.5 h-1.5 rounded-full bg-acc" />
            {statusLabel}
          </span>
        )}
        <button
          aria-label={isDarkActive ? 'Switch to light theme' : 'Switch to dark theme'}
          title={isDarkActive ? 'Light' : 'Dark'}
          onClick={onToggleTheme}
          aria-pressed={isDarkActive}
          className="inline-flex items-center justify-center w-9 h-9 rounded-xl border border-border bg-surf text-tx3 hover:text-acc hover:border-acc/50 transition-all duration-200 cursor-pointer"
        >
          {isDarkActive ? <Sun size={16} /> : <Moon size={16} />}
          <span className="sr-only">Toggle theme</span>
        </button>
      </div>
    </header>
  )
}
