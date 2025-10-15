export default function DisclaimerContent() {
  return (
    <div className="bg-white dark:bg-neutral-800 rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 p-6 space-y-3 text-sm text-neutral-800 dark:text-neutral-200">
      <h1 className="font-semibold text-base">Disclaimer</h1>
      <p>
        This tool is intended for informational purposes only and should not be
        considered as professional tax advice. This tool is for the exclusive use of
        Varma & Varma Chartered Accountants.
      </p>
      <p>
        <span className="font-semibold">Accuracy Warning:</span> The data extracted by this tool is based on OCR and
        pattern matching from PDF documents. While efforts are made to ensure accuracy, discrepancies may occur due to
        variations in PDF formats, scanning quality, or document structure.
      </p>
      <p>
        <span className="font-semibold">Verification Required:</span> Always cross-verify the extracted data with official
        records and the GSTN portal before making any financial decisions or filings.
      </p>
      <p>
        <span className="font-semibold">Limitations:</span> This tool may not be able to extract all data points from all
        types of GSTR-3B PDFs, especially those with non-standard layouts or complex tables.
      </p>
      <p>
        <span className="font-semibold">No Liability:</span> The developers of this tool are not liable for any errors,
        omissions, or damages arising from the use or misuse of the extracted information.
      </p>
      <p>
        <span className="font-semibold">Data Privacy:</span> Ensure that you handle your sensitive tax data responsibly.
        This tool processes data locally and does not transmit it externally unless explicitly configured by the user
        for other purposes (e.g., saving to a local file).
      </p>
    </div>
  )
}