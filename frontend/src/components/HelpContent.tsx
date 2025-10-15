export default function HelpContent() {
  return (
    <div className="bg-white dark:bg-neutral-800 rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 p-6 space-y-3 text-sm text-neutral-800 dark:text-neutral-200">
      <h2 className="font-semibold text-base">Instructions</h2>
      <ol className="list-decimal list-inside space-y-1">
        <li>Select the return type (GSTR-1 or GSTR-3B) and file format (PDF or JSON).</li>
        <li>Upload one or more files and click <strong>Extract</strong>.</li>
        <li>Download the complete extracted data using the <strong>Raw Data</strong> button.</li>
        <li>Alternatively, download structured tables extracted from the returns.</li>
        <li>Open <strong>Preferences</strong> to select which tables to extract. You can update preferences anytime, even after uploading files.</li>
        <li>Once extraction is complete, preview your preferred tables.</li>
        <li>Use <strong>Filter</strong> to refine which tables are displayed.</li>
        <li>Click <strong>Tables</strong> to download all preferred tables or only the filtered ones.</li>
      </ol>
      <div className="pt-4">
        <h3 className="font-semibold text-base">Known Limitations</h3>
        <ol className="list-decimal list-inside space-y-1">
          <li>Heavily watermarked PDFs may result in reduced extraction accuracy.</li>
          <li>Scanned PDFs require high-quality scans for reliable text extraction.</li>
        </ol>
      </div>
      <div className="pt-4">
        <h3 className="font-semibold text-base">Contact Us</h3>
        <p>
          If you have any questions or need support, please contact us at
          {' '}<a href="mailto:support@varma.ai" className="text-blue-600 dark:text-blue-400 underline">support@varma.ai</a>.(mail id to be updated)
        </p>
        <p>
          Write your feedback
          {' '}<a href="https://forms.gle/hWeqCvZQ5F1T4j8A8" className="text-blue-600 dark:text-blue-400 underline">here</a>
        </p>
      </div>
    </div>
  )
}
