export default function HelpContent() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 text-neutral-800 dark:text-neutral-200">
      {/* Instructions */}
      <div className="rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
        <div className="px-6 pt-6">
          <h2 className="text-xl font-semibold">Instructions</h2>
        </div>
        <div className="px-6 pb-6 space-y-2">
          <ol className="space-y-2 list-decimal list-inside text-sm">
            <li className="leading-relaxed">
              Select the return type (GSTR-1 or GSTR-3B) and file format (PDF or JSON).
            </li>
            <li className="leading-relaxed">
              Upload one or more files and click <span className="font-semibold">Extract</span>.
            </li>
            <li className="leading-relaxed">
              Download the complete extracted data using the <span className="font-semibold">Raw Data</span> button.
            </li>
            <li className="leading-relaxed">
              Alternatively, download structured tables extracted from the returns.
            </li>
            <li className="leading-relaxed">
              Open <span className="font-semibold">Preferences</span> to select which tables to extract. You can update preferences anytime, even after uploading files.
            </li>
            <li className="leading-relaxed">
              Once extraction is complete, preview your preferred tables.
            </li>
            <li className="leading-relaxed">
              Use <span className="font-semibold">Filter</span> to refine which tables are displayed.
            </li>
            <li className="leading-relaxed">
              Click <span className="font-semibold">Tables</span> to download all preferred tables or only the filtered ones.
            </li>
            <li className="leading-relaxed">
              It is recommended to extract all returns for a financial year for each registration in a single run. If you have multiple registrations, you may either repeat the extraction process for each one or use the <span className="font-semibold">raw data extraction</span> option and consolidate the data in Excel.
            </li>
          </ol>
        </div>
      </div>

      {/* Known Limitations */}
      <div className="rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
        <div className="px-6 pt-6">
          <h3 className="text-lg font-semibold">Known Limitations</h3>
        </div>
        <div className="px-6 pb-6 space-y-2">
          <ol className="space-y-2 list-decimal list-inside text-sm">
            <li className="leading-relaxed">Heavily watermarked PDFs may result in reduced extraction accuracy.</li>
            <li className="leading-relaxed">Scanned PDFs require high-quality scans for reliable text extraction.</li>
          </ol>
        </div>
      </div>

      {/* Contact Us */}
      <div className="rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 bg-gradient-to-br from-white to-indigo-50/40 dark:from-neutral-900 dark:to-indigo-900/15 mb-6">
        <div className="px-6 pt-6">
          <h3 className="text-lg font-semibold">Contact Us</h3>
        </div>
        <div className="px-6 pb-6 space-y-2">
          <p className="leading-relaxed text-sm">
            If you have any questions or need support, please contact us at{' '}
            <a href="mailto:farissalmanul60@gmail.com" className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline">support@fincod.com</a>.
          </p>
          <p className="leading-relaxed text-sm">
            Write your feedback{' '}
            <a href="https://forms.gle/hWeqCvZQ5F1T4j8A8" target="_blank" rel="noopener noreferrer" className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline">here</a>.
          </p>
        </div>
      </div>
    </div>
  )
}
