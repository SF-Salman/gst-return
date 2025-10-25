import { AlertTriangle, ShieldAlert, Info } from "lucide-react";

export default function DisclaimerContent() {
  return (
    <div className="max-w-4xl mx-auto mb-6">
      <div className="rounded-2xl shadow-soft border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
        <div className="p-8 space-y-4">
          {/* Intro notice */}
          <div className="flex items-start gap-4 p-5 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
            <Info className="h-5 w-5 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
            <p className="text-neutral-800 dark:text-neutral-200 leading-relaxed text-sm">
              This tool is intended for informational purposes only and should not be considered as professional tax advice.
            </p>
          </div>

          {/* Details */}
          <div className="space-y-3 text-neutral-800 dark:text-neutral-200">
            <div className="flex items-start gap-4">
              <ShieldAlert className="h-5 w-5 text-rose-600 dark:text-rose-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-base mb-1.5">Accuracy Warning:</h3>
                <p className="leading-relaxed text-sm">
                  The data extracted by this tool is based on OCR and pattern matching from PDF documents. While efforts are made to ensure accuracy, discrepancies may occur due to variations in PDF formats, scanning quality, or document structure.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-base mb-1.5">Verification Required:</h3>
                <p className="leading-relaxed text-sm">
                  Always cross-verify the extracted data with official records and the GSTN portal before making any financial decisions or filings.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-base mb-1.5">Limitations:</h3>
                <p className="leading-relaxed text-sm">
                  This tool may not be able to extract all data points from all types of GSTR-3B PDFs, especially those with non-standard layouts or complex tables.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <ShieldAlert className="h-5 w-5 text-rose-600 dark:text-rose-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-base mb-1.5">No Liability:</h3>
                <p className="leading-relaxed text-sm">
                  The developers of this tool are not liable for any errors, omissions, or damages arising from the use or misuse of the extracted information.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <Info className="h-5 w-5 text-emerald-600 dark:text-emerald-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-base mb-1.5">Data Privacy:</h3>
                <p className="leading-relaxed text-sm">
                  Ensure that you handle your sensitive tax data responsibly. This tool processes data locally and does not transmit it externally unless explicitly configured by the user for other purposes (e.g., saving to a local file).
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}