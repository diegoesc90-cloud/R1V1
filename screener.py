"""Screener diario R1_B_v2 (con detalle + regimen SPY)."""
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from r1_strategy import compute_features, check_signal_detailed, ATR_SL_MULT

DRIVE = Path("/content/drive/MyDrive/QuantTool_IBEX_NASDAQ")
DATA_DIRS = [DRIVE / "data_ohlcv", DRIVE / "data_sp500_eurostoxx"]
PCT = DRIVE / "model_frozen" / "percentiles_train_v2.json"
OUT = DRIVE / "model_frozen" / "last_screener_v2.json"


def load_ticker(t):
    for folder in DATA_DIRS:
        for name in [t.replace(".", "_"), t]:
            p = folder / f"{name}.parquet"
            if p.exists():
                try:
                    df = pd.read_parquet(p)
                    df.index = pd.to_datetime(df.index)
                    df.columns = [x.lower() for x in df.columns]
                    if "adj close" in df.columns and "close" not in df.columns:
                        df["close"] = df["adj close"]
                    cols = [x for x in ["open","high","low","close","volume"] if x in df.columns]
                    if len(cols) >= 4: return df[cols].sort_index()
                except: pass
    return None


def get_regime():
    try:
        import yfinance as yf
        spy = yf.download("SPY", period="2y", progress=False, auto_adjust=True)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)
        spy["ma200"] = spy["Close"].rolling(200).mean()
        last_close = float(spy["Close"].iloc[-1])
        last_ma = float(spy["ma200"].iloc[-1])
        return {
            "name": "BULL" if last_close > last_ma else "BEAR",
            "spy_price": round(last_close, 2),
            "spy_ma200": round(last_ma, 2),
        }
    except Exception:
        return None


def run():
    if not PCT.exists():
        raise FileNotFoundError(f"Falta {PCT}. Ejecuta build_percentiles.py antes.")
    with open(PCT) as f: pct = json.load(f)

    regime = get_regime()
    sigs = []
    for t, tp in pct.items():
        df = load_ticker(t)
        if df is None or len(df) < 300: continue
        try:
            feat = compute_features(df)
            last = feat.iloc[-1]
            is_sig, ns, conds = check_signal_detailed(last, tp)
            if is_sig:
                atr = float(last["atr_14"])
                sigs.append({
                    "ticker": t,
                    "date": feat.index[-1].strftime("%Y-%m-%d"),
                    "price": round(float(last["close"]), 2),
                    "stop_price": round(float(last["close"] - ATR_SL_MULT * atr), 2),
                    "n_strong": int(ns),
                    "conditions": [{
                        "name": c["name"],
                        "value": round(c["value"], 4),
                        "threshold": round(c["threshold"], 4),
                        "direction": c["direction"],
                        "ok": c["ok"],
                        "strong": c["strong"],
                    } for c in conds],
                })
        except: continue

    sigs.sort(key=lambda x: (-x["n_strong"], -abs(x["price"] - x["stop_price"])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({
            "ts": datetime.now().isoformat(),
            "regime": regime,
            "n_evaluated": len(pct),
            "n_signals": len(sigs),
            "signals": sigs,
        }, f, indent=2)

    print(f"OK {len(sigs)} senales -> {OUT}")
    if regime:
        print("Regimen: " + regime["name"])
    for s in sigs[:25]:
        print("  " + s["ticker"] + "  $" + str(s["price"]) + "  fuerza " + str(s["n_strong"]) + "/5")


if __name__ == "__main__":
    run()