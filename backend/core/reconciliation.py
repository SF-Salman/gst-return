from rapidfuzz import fuzz
from backend.core.models import InvoiceRecord

AMOUNT_TOLERANCE = 1.0       # ₹1 absolute
AMOUNT_TOLERANCE_PCT = 0.02  # 2% relative
FUZZY_THRESHOLD = 85         # invoice number similarity score

def reconcile(source: list[InvoiceRecord], target: list[InvoiceRecord]) -> dict:
    matched = []
    mismatched = []
    target_pool = list(target)

    # Stage 1 — exact match on GSTIN + Invoice Number
    unmatched_after_s1 = []
    for s in source:
        found = next(
            (t for t in target_pool
             if t["gstin"] == s["gstin"]
             and t["invoice_no"] == s["invoice_no"]),
            None
        )
        if found:
            target_pool.remove(found)
            diffs = get_amount_diffs(s, found)
            if diffs:
                mismatched.append({"source": s, "target": found, "differences": diffs})
            else:
                matched.append({"source": s, "target": found})
        else:
            unmatched_after_s1.append(s)

    # Stage 2 — tolerance match (same GSTIN, amounts within ₹1 / 2%)
    unmatched_after_s2 = []
    for s in unmatched_after_s1:
        found = next(
            (t for t in target_pool
             if t["gstin"] == s["gstin"]
             and amounts_within_tolerance(s, t)),
            None
        )
        if found:
            target_pool.remove(found)
            matched.append({"source": s, "target": found})
        else:
            unmatched_after_s2.append(s)

    # Stage 3 — fuzzy match on invoice number
    final_unmatched_source = []
    for s in unmatched_after_s2:
        best_match = None
        best_score = 0
        for t in target_pool:
            if t["gstin"] != s["gstin"]:
                continue
            score = fuzz.ratio(s["invoice_no"], t["invoice_no"])
            if score >= FUZZY_THRESHOLD and score > best_score:
                best_match = t
                best_score = score
        if best_match:
            target_pool.remove(best_match)
            diffs = get_amount_diffs(s, best_match)
            mismatched.append({
                "source": s,
                "target": best_match,
                "differences": diffs,
                "match_note": f"Fuzzy invoice match (score {best_score})"
            })
        else:
            final_unmatched_source.append(s)  # truly unmatched

    return {
        "matched": matched,
        "mismatched": mismatched,
        "only_in_source": final_unmatched_source,
        "only_in_target": target_pool,
        "summary": {
            "total_source": len(source),
            "total_target": len(target),
            "matched_count": len(matched),
            "mismatch_count": len(mismatched),
            "unmatched_source": len(final_unmatched_source),
            "unmatched_target": len(target_pool),
        }
    }

def amounts_within_tolerance(a: InvoiceRecord, b: InvoiceRecord) -> bool:
    for field in ["taxable_value", "cgst", "sgst", "igst"]:
        diff = abs(a[field] - b[field])
        if diff == 0:
            continue
        avg = (a[field] + b[field]) / 2 or 1
        if diff > AMOUNT_TOLERANCE and (diff / avg) > AMOUNT_TOLERANCE_PCT:
            return False
    return True

def get_amount_diffs(a: InvoiceRecord, b: InvoiceRecord) -> list:
    diffs = []
    for field in ["taxable_value", "cgst", "sgst", "igst"]:
        diff = round(a[field] - b[field], 2)
        if abs(diff) > 0.01:
            diffs.append({
                "field": field,
                "source_value": a[field],
                "target_value": b[field],
                "diff": diff
            })
    return diffs