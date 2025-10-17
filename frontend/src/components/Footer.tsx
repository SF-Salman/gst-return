function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer role="contentinfo" className="mt-auto bg-gradient-to-b from-white via-white to-neutral-100 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
      <div className="mx-auto max-w-7xl px-3 sm:px-4 py-2 text-center">
        <p className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
          © {year} Varma & Varma Chartered Accountants. All rights reserved.
        </p>
      </div>
    </footer>
  )
}

export default Footer