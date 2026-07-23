export type InvoiceRecord = {
  gstin: string
  invoice_no: string
  invoice_date: string
  taxable_value: number
  cgst: number
  sgst: number
  igst: number
  source: "GSTR-1" | "2A" | "2B" | "PR"
}

export type MatchedPair = {
  source: InvoiceRecord
  target: InvoiceRecord
}

export type MismatchedPair = {
  source: InvoiceRecord
  target: InvoiceRecord
  differences: {
    field: string
    source_value: number
    target_value: number
    diff: number
  }[]
}

export type ReconcileResponse = {
  matched: MatchedPair[]
  mismatched: MismatchedPair[]
  only_in_source: InvoiceRecord[]
  only_in_target: InvoiceRecord[]
  summary: {
    total_source: number
    total_target: number
    matched_count: number
    mismatch_count: number
    unmatched_source: number
    unmatched_target: number
  }
}