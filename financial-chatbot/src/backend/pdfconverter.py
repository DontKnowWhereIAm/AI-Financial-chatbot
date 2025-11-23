import re
import pdfplumber
import pandas as pd
import numpy as np

def _norm(s: str) -> str:
    """normalize header text: lowercase, collapse spaces, remove dots"""
    return re.sub(r'\s+', '_', re.sub(r'[^\w\s]', '', s.strip().lower()))

def _parse_money(series) -> pd.Series:
    """Parse currency-like strings -> float. Handles $, commas, spaces, and (negatives)."""
    if series is None:
        return pd.Series(dtype='float64')
    s = series.astype(str).str.strip()
    neg = s.str.contains(r'^\(.*\)$')
    # remove $, commas, parentheses, spaces
    s = s.str.replace(r'[\$,]', '', regex=True).str.replace(r'[\(\)]', '', regex=True).str.replace(' ', '')
    out = pd.to_numeric(s, errors='coerce')
    out[neg] = -out[neg]
    return out

def _first_match(cols, *needles):
    """Return first column name in cols whose normalized name contains any needle."""
    for n in needles:
        for c in cols:
            if n in c:
                return c
    return None

def load_transactions_from_file(path: str, keep_extra=False) -> pd.DataFrame:
    """
    Load and standardize transaction data from a file path.

    Args:
        path: Path to the transaction file (.csv, .xlsx, or .pdf)
        keep_extra: Whether to keep extra columns like reference and balance

    Returns:
        Standardized DataFrame with transaction data
    """
    print(f"✅ Processing: {path}")

    p = path.lower()
    # --- Load file ---
    if p.endswith(".csv"):
        t = pd.read_csv(path, dtype=str)  # read as str, parse later
    elif p.endswith((".xls", ".xlsx")):
        # read as str to preserve formatting; many bank sheets have blank/extra columns
        t = pd.read_excel(path, dtype=str)
    elif p.endswith(".pdf"):
        rows = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue
                headers = [ _norm(h) for h in table[0] ]
                for r in table[1:]:
                    rows.append(dict(zip(headers, r)))
        t = pd.DataFrame(rows)
    else:
        raise ValueError("Unsupported file type")

    # Drop fully-empty columns
    t = t.dropna(axis=1, how="all")

    # Normalize headers
    t.columns = [_norm(c) for c in t.columns]

    # --- Identify relevant columns (handle misspellings & variants) ---
    date_col      = _first_match(t.columns, "date")
    desc_col      = _first_match(t.columns, "description", "desc")
    ref_col       = _first_match(t.columns, "ref")
    withdraw_col  = _first_match(t.columns, "withdrawls", "withdrawals", "withdrawl", "withdraw", "debit")
    deposit_col   = _first_match(t.columns, "deposits", "deposit", "credit")
    balance_col   = _first_match(t.columns, "balance", "bal")

    # --- Build canonical columns ---
    out = pd.DataFrame()

    if date_col is None:
        raise ValueError("Couldn't find a Date column.")
    out["transaction_date"] = pd.to_datetime(t[date_col], errors="coerce")

    if desc_col is None:
        # Create a placeholder if description truly missing
        out["transaction_description"] = ""
    else:
        out["transaction_description"] = t[desc_col].astype(str).fillna("")

    if ref_col is not None:
        out["reference"] = t[ref_col].astype(str)

    wd = _parse_money(t[withdraw_col]) if withdraw_col else pd.Series(0, index=t.index, dtype="float64")
    dp = _parse_money(t[deposit_col])  if deposit_col  else pd.Series(0, index=t.index, dtype="float64")

    out["transaction_amount"] = (dp.fillna(0) - wd.fillna(0)).astype("float64")

    if balance_col is not None:
        out["running_balance"] = _parse_money(t[balance_col])

    # Clean rows: drop where date is NaT and amount is NaN
    out = out.dropna(subset=["transaction_date"])
    # Some banks include a "Previous balance" row with amount empty; keep it but set amount=0 if NaN
    out["transaction_amount"] = out["transaction_amount"].fillna(0.0)

    # Return only core columns unless user wants extras
    core_cols = ["transaction_date", "transaction_description", "transaction_amount"]
    optional  = [c for c in ["reference", "running_balance"] if c in out.columns]
    final_cols = core_cols + (optional if keep_extra else [])
    out = out[final_cols].reset_index(drop=True)

    print("✅ Loaded and standardized.")
    print("• Detected columns:", {"date": date_col, "description": desc_col,
                                     "withdrawals": withdraw_col, "deposits": deposit_col,
                                     "balance": balance_col, "ref": ref_col})
    return out

def load_transactions_interactive(keep_extra=False) -> pd.DataFrame:
    """
    Legacy function for backward compatibility.
    In web environment, use load_transactions_from_file() instead.
    """
    raise NotImplementedError("Interactive upload not available in web environment. Use load_transactions_from_file() instead.")