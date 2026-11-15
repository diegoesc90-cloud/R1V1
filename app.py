"""R1_B_v2 — Streamlit app."""
import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="R1 Screener", page_icon="chart_with_downwards_trend", layout="wide")


@st.cache_data(ttl=60)
def load_json(name):
    p = Path(__file__).parent / name
    if not p.exists(): return None
    with open(p) as f: return json.load(f)


data = load_json("last_screener_v2.json")
cfg = load_json("R1_B_v2_config.json")

if data is None:
    st.error("Falta last_screener_v2.json en el repo.")
    st.stop()

sigs = data.get("signals", [])
regime = data.get("regime") or {}
ts = data.get("ts", "")
n_eval = data.get("n_evaluated", 0)

st.title("R1_B_v2 Screener")
st.caption("Mean reversion en acciones castigadas con momentum mejorando")

if regime:
    name = regime.get("name", "?")
    spy = regime.get("spy_price", 0)
    ma = regime.get("spy_ma200", 0)
    if name == "BEAR":
        st.success("Regimen: BEAR (SPY $" + str(spy) + " < MA200 $" + str(ma) + ")")
    elif name == "BULL":
        st.info("Regimen: BULL (SPY $" + str(spy) + " > MA200 $" + str(ma) + ")")

c1, c2, c3 = st.columns(3)
c1.metric("Senales hoy", len(sigs))
c2.metric("Tickers evaluados", n_eval)
c3.metric("Actualizado", ts[:10] if ts else "?")

st.divider()

tab1, tab2, tab3 = st.tabs(["Senales", "Como funciona", "Paper trading"])

with tab1:
    if not sigs:
        st.info("Sin senales R1 hoy. Normal: requiere 5 condiciones extremas a la vez.")
    else:
        for s in sigs:
            ns = s.get("n_strong", 0)
            color = "#00C853" if ns >= 3 else ("#FFA726" if ns >= 2 else "#78909C")
            risk_pct = (s["stop_price"] / s["price"] - 1) * 100
            st.markdown(
                "<div style=\"background:#1E2530;padding:16px;border-radius:10px;margin:12px 0;border-left:5px solid " + color + ";\">"
                "<h3 style=\"margin:0 0 8px 0;color:#FAFAFA;\">" + s["ticker"] + "  $" + str(s["price"]) + "</h3>"
                "<p style=\"margin:4px 0;color:#B0BEC5;\">"
                "<b>Stop:</b> $" + str(s["stop_price"]) + " (" + ("%+.1f" % risk_pct) + "%)<br>"
                "<b>Fuerza:</b> " + str(ns) + "/5 condiciones extremas"
                "</p></div>",
                unsafe_allow_html=True
            )
            if "conditions" in s:
                with st.expander("Ver condiciones"):
                    for c in s["conditions"]:
                        icon = "OK" if c["ok"] else "NO"
                        strong = " [EXTREMA]" if c.get("strong") else ""
                        st.markdown(icon + " **" + c["name"] + "** = " + str(c["value"])
                                    + " (umbral " + c["direction"] + " " + str(c["threshold"]) + ")" + strong)

with tab2:
    st.markdown("### Regla R1_B_v2")
    st.markdown("**5 condiciones al cierre del dia t:**")
    st.markdown("1. ret_5 < P33 (caida corto plazo)")
    st.markdown("2. ret_252 < P33 (caida largo plazo)")
    st.markdown("3. macd_hist > P67 (momentum mejorando)")
    st.markdown("4. dist_ma_20 < P33 (bajo MA20)")
    st.markdown("5. atr_norm > P67 (volatilidad alta)")
    st.markdown("**Entrada:** open del dia t+1  |  **Salidas:** SL -1.5xATR, TP +5% -> trailing 5%, timeout 30d")
    if cfg:
        st.markdown("### Resultados historicos")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**FULL 2010-2026**")
            for k, v in cfg.get("results_full", {}).items():
                st.metric(k, str(v))
        with col2:
            st.markdown("**OOS 2022-2026**")
            for k, v in cfg.get("results_oos", {}).items():
                st.metric(k, str(v))
        st.markdown("### Advertencias")
        for w in cfg.get("warnings", []):
            st.warning(w)

with tab3:
    st.info("Registra trades en paper_trading.json del repo.")
    pt = load_json("paper_trading.json")
    if pt is None:
        st.markdown("Crea paper_trading.json con [] para empezar.")
    elif len(pt) == 0:
        st.info("Sin trades registrados aun.")
    else:
        st.dataframe(pd.DataFrame(pt), use_container_width=True)