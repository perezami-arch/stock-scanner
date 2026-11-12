"""Daily check: tracker positions vs the simulated-account book (real, and trial only when the tracker has a trial book).

Not the paper ledger. A missing account file is a blocker, not a silent pass and not a comparison against paper trades.
Both files need ticker, entry_session, status. Direction is used when both have it. Optional exit_date, exit_price.
Account rows may carry book=real|trial (or group). Tracker rows may carry is_trial.
'closed'/'stopped' are closed. A closed row also mismatches when the exit prices disagree.
Usage: python ops/status_mismatch.py TRACKER_CSV ACCOUNT_CSV
"""
import os, sys
import pandas as pd

CLOSED = {"closed", "stopped", "stop", "סטופ", "סגור"}
PRICE_TOL = 0.01
ACCOUNT_COLUMNS = "ticker, direction, entry_session, status, exit_date, exit_price, book (real|trial)"


def _paper(df, path=""):
    name = os.path.basename(str(path)).lower()
    if "paper" in name:
        return True
    if "is_paper" in df.columns and df["is_paper"].astype(str).str.lower().isin(["true", "1", "yes"]).any():
        return True
    return "paper_id" in df.columns


def _price(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:
        return None
    return x


def prices_disagree(a, b, tol=PRICE_TOL):
    fa, fb = _price(a), _price(b)
    if fa is None and fb is None:
        return str(a).strip() not in ("", "None", "nan") and str(a).strip() != str(b).strip()
    if fa is None or fb is None:
        return True
    return abs(fa - fb) > tol


def norm(df):
    df = df.copy()
    df["is_closed"] = df["status"].astype(str).str.strip().str.lower().isin(CLOSED)
    for c in ("exit_date", "exit_price"):
        if c not in df:
            df[c] = None
    cols = ["ticker", "entry_session", "is_closed", "exit_date", "exit_price"]
    if "direction" in df.columns:
        df["direction"] = df["direction"].astype(str).str.strip().str.upper()
        cols.insert(1, "direction")
    if "book" in df.columns:
        df["book"] = df["book"].astype(str).str.strip().str.lower()
        cols.append("book")
    elif "group" in df.columns:
        df["book"] = df["group"].astype(str).str.strip().str.lower()
        cols.append("book")
    if "is_trial" in df.columns:
        df["is_trial"] = df["is_trial"].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])
        cols.append("is_trial")
    return df[cols]


def _keys(t, p):
    keys = ["ticker", "entry_session"]
    if "direction" in t.columns and "direction" in p.columns:
        keys = ["ticker", "direction", "entry_session"]
    return keys


def _bad_mask(m):
    closed_both = m.is_closed_tracker.fillna(False) & m.is_closed_account.fillna(False)
    price_bad = closed_both & m.apply(lambda r: prices_disagree(r.exit_price_tracker, r.exit_price_account), axis=1)
    return (m._merge != "both") | (m.is_closed_tracker != m.is_closed_account) | (
        m.is_closed_tracker.fillna(False) & (m.exit_date_tracker.astype(str) != m.exit_date_account.astype(str))
    ) | price_bad


def mismatch_frame(tracker, account):
    """Rows that disagree. Trial account rows are ignored when the tracker has no trial book."""
    t, p = norm(tracker), norm(account)
    t["_book"] = t["is_trial"].map(lambda v: "trial" if v else "real") if "is_trial" in t.columns else "real"
    p["_book"] = p["book"] if "book" in p.columns else "real"
    tracker_books = set(t["_book"])
    frames = []
    for book in ("real", "trial"):
        if book == "trial" and "trial" not in tracker_books:
            continue
        tb, pb = t[t._book == book], p[p._book == book]
        if tb.empty and pb.empty:
            continue
        keys = _keys(tb, pb)
        m = tb.drop(columns=["_book"]).merge(pb.drop(columns=["_book"]), on=keys, how="outer", suffixes=("_tracker", "_account"), indicator=True)
        bad = m[_bad_mask(m)]
        if len(bad):
            bad = bad.copy()
            bad["book"] = book
            frames.append(bad)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def daily_check(tracker_path, account_path):
    """Compare the two position books. Never substitutes the paper ledger."""
    if not account_path or not os.path.exists(account_path):
        return {"ok": False, "compared": False, "code": None, "mismatches": [],
                "blocker": (f"account position ledger missing ({account_path}). "
                            f"Expected columns: {ACCOUNT_COLUMNS}. "
                            "Refusing to compare the paper-only ledger to the real+trial account.")}
    account = pd.read_csv(account_path, dtype=object)
    tracker = pd.read_csv(tracker_path, dtype=object) if tracker_path and os.path.exists(tracker_path) else pd.DataFrame()
    if _paper(account, account_path) or _paper(tracker, tracker_path):
        return {"ok": False, "compared": False, "code": None, "mismatches": [],
                "blocker": "refusing to compare a paper-only ledger. The check is tracker positions vs the simulated account (real, plus trial only if the tracker has trial rows)."}
    if tracker.empty:
        return {"ok": False, "compared": False, "code": None, "mismatches": [],
                "blocker": f"tracker position ledger missing ({tracker_path})."}
    bad = mismatch_frame(tracker, account)
    rows = bad.to_dict("records")
    return {"ok": len(rows) == 0, "compared": True, "code": 0 if len(rows) == 0 else 1, "mismatches": rows, "blocker": None}


def main(a, b):
    result = daily_check(a, b)
    if result.get("blocker"):
        print("STATUS MISMATCH BLOCKER:", result["blocker"])
        return 1
    if not result["ok"]:
        print(f"STATUS MISMATCH: {len(result['mismatches'])} position(s)")
        print(pd.DataFrame(result["mismatches"]).to_string(index=False))
        return 1
    print("status OK: tracker and account agree")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
