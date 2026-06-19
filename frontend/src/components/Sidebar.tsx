import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Settings, HelpCircle, AlertTriangle, Menu, X, ChevronLeft, ChevronRight } from 'lucide-react'

export type SidebarView = 'upload' | 'help' | 'disclaimer'

interface NavItem {
  id: SidebarView | 'preferences'
  label: string
  icon: typeof Upload
}

const NAV_ITEMS: NavItem[] = [
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'preferences', label: 'Preferences', icon: Settings },
  { id: 'help', label: 'Help', icon: HelpCircle },
  { id: 'disclaimer', label: 'Disclaimer', icon: AlertTriangle },
]

interface Props {
  activeView: SidebarView
  onSelectView: (v: SidebarView) => void
  onOpenPreferences: () => void
  isCollapsed: boolean
  onToggle: () => void
}

export default function Sidebar({ activeView, onSelectView, onOpenPreferences, isCollapsed, onToggle }: Props) {
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  const handleClick = (id: NavItem['id']) => {
    if (id === 'preferences') {
      onOpenPreferences()
    } else {
      onSelectView(id)
    }
    setIsMobileOpen(false)
  }

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      <div className="h-14 border-b border-border flex items-center px-4 justify-between flex-shrink-0">
        <AnimatePresence initial={false}>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-tx3 whitespace-nowrap">
                GST Reconciler
              </span>
            </motion.div>
          )}
        </AnimatePresence>
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg text-tx3 hover:text-tx hover:bg-sub/60 transition-colors flex-shrink-0"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-0.5 scrollbar-thin">
        {NAV_ITEMS.map((item) => {
          const isActive = item.id !== 'preferences' && item.id === activeView
          return (
            <button
              key={item.id}
              onClick={() => handleClick(item.id)}
              title={isCollapsed ? item.label : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-150 relative group ${
                isActive ? 'bg-acc/10 text-acc' : 'text-tx2 hover:bg-sub/70 hover:text-tx'
              } ${isCollapsed ? 'justify-center' : ''}`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeSidebarItem"
                  className="absolute left-0 top-1.5 bottom-1.5 w-[3px] bg-acc rounded-full"
                />
              )}
              <item.icon size={17} className={`flex-shrink-0 ${isActive ? 'text-acc' : 'text-tx3 group-hover:text-tx2'}`} />
              <AnimatePresence initial={false}>
                {!isCollapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
          )
        })}
      </div>
    </div>
  )

  return (
    <>
      <button
        onClick={() => setIsMobileOpen(true)}
        className="md:hidden fixed top-3.5 left-4 z-50 p-2 rounded-xl border border-border bg-surf shadow-soft"
      >
        <Menu size={18} />
      </button>

      <motion.aside
        animate={{ width: isCollapsed ? 64 : 224 }}
        transition={{ duration: 0.22, ease: 'easeInOut' }}
        className="hidden md:flex h-screen sticky top-0 border-r border-border bg-surf flex-col overflow-hidden flex-shrink-0"
      >
        <SidebarContent />
      </motion.aside>

      <AnimatePresence>
        {isMobileOpen && (
          <>
            <motion.div
              className="md:hidden fixed inset-0 bg-black/40 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMobileOpen(false)}
            />
            <motion.aside
              className="md:hidden fixed left-0 top-0 bottom-0 w-64 bg-surf border-r border-border z-50"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.22 }}
            >
              <div className="h-14 border-b border-border flex items-center justify-between px-4">
                <span className="font-serif font-semibold text-acc">GST Reconciler</span>
                <button onClick={() => setIsMobileOpen(false)} className="p-1.5 rounded-lg hover:bg-sub/60">
                  <X size={18} />
                </button>
              </div>
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
