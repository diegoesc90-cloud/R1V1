"""R1_B_v2 — core strategy (with detail for UI)."""
import pandas as pd

FEATURES = ["ret_5", "ret_252", "macd_hist", "dist_ma_20", "atr_norm"]
ATR_SL_MULT = 1.5
TP_ACTIVATION = 0.05
TRAIL_PCT = 0.05
TIMEOUT_DAYS = 30
POSITION_SIZE = 5000
MAX_POSITIONS = 20
COSTE_RT = 0.0036
TRAIN_START, TRAIN_END = "2010-01-01", "2021-12-31"


def compute_features(df):
    d = df.copy()
    c = d["close"]
    d["ret_5"] = c.pct_change(5)
    d["ret_252"] = c.pct_change(252)
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    d["macd_hist"] = (e12 - e26) - (e12 - e26).ewm(span=9, adjust=False).mean()
    ma20 = c.rolling(20).mean()
    d["dist_ma_20"] = (c - ma20) / ma20
    tr = pd.concat([d["high"] - d["low"], (d["high"] - c.shift()).abs(), (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
    d["atr_14"] = tr.rolling(14).mean()
    d["atr_norm"] = d["atr_14"] / c
    return d


def compute_percentiles(df_train):
    feat = compute_features(df_train)
    pct = {}
    for f in FEATURES:
        v = feat[f].dropna()
        if len(v) < 100: continue
        pct[f] = {"p20": float(v.quantile(0.20)), "p33": float(v.quantile(0.33)),
                  "p67": float(v.quantile(0.67)), "p80": float(v.quantile(0.80))}
    return pct if len(pct) == len(FEATURES) else None


def check_signal_detailed(row, pct):
    """Devuelve (is_signal, n_strong, conditions_lista)."""
    if any(pd.isna(row[f]) for f in FEATURES):
        return False, 0, []
    conditions = []
    for f in FEATURES:
        is_low = f in ("ret_5", "ret_252", "dist_ma_20")
        if is_low:
            thr, thr_strong = pct[f]["p33"], pct[f]["p20"]
            ok = bool(row[f] < thr)
            strong = bool(row[f] < thr_strong)
        else:
            thr, thr_strong = pct[f]["p67"], pct[f]["p80"]
            ok = bool(row[f] > thr)
            strong = bool(row[f] > thr_strong)
        conditions.append({
            "name": f,
            "value": float(row[f]),
            "threshold": float(thr),
            "direction": "low" if is_low else "high",
            "ok": ok,
            "strong": strong,
        })
    is_signal = all(c["ok"] for c in conditions)
    n_strong = sum(c["strong"] for c in conditions)
    return is_signal, n_strong, conditions


def check_signal(row, pct):
    is_s, ns, _ = check_signal_detailed(row, pct)
    return is_s, ns