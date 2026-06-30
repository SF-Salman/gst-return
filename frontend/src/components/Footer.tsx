function Footer() {
  const year = new Date().getFullYear()
  const month = String(new Date().getMonth() + 1).padStart(2, '0')
  return (
    <footer role="contentinfo" className="mt-auto bg-[#a33d2e] border-t border-[#a33d2e]">
      <div className="mx-auto max-w-7xl px-3 sm:px-4 py-2 text-center">
        <p className="text-sm font-mono font-medium text-white/90 tracking-wide">
          © Varma & Varma Chartered Accountants · {month}.{year}
        </p>
      </div>
    </footer>
  )
}

export default Footer
