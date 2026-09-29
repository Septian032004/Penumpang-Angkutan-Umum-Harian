import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

st.set_page_config(
    page_title="Dashboard Penumpang DKI Jakarta",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_FILE = Path(__file__).parent / "Jumlah Penumpang.json"

# ---------- STYLE ----------
st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container {padding-top:1.1rem; padding-bottom:2rem; max-width:1600px;}
html, body, [class*="css"] {font-family:Arial, sans-serif;}
.stApp {background:#f8fbff; color:#0b2b66;}
.hero {
    padding:18px 24px; border:1px solid #d8e6f7; border-radius:16px;
    background:linear-gradient(120deg,#ffffff 0%,#f2f8ff 70%,#e8f3ff 100%);
    margin-bottom:14px;
}
.hero h1 {font-size:32px; margin:0; color:#0b3478; font-weight:800;}
.hero h2 {font-size:19px; margin:5px 0 4px; color:#183f7a; font-weight:500;}
.hero p {font-size:13px; margin:0; color:#31527d;}
.section-title {font-size:20px; font-weight:800; color:#0b3478; margin:2px 0 10px;}
.kpi {
    min-height:142px; border:1px solid #d8e6f7; border-radius:14px;
    padding:16px 18px; background:#fff;
}
.kpi.total {background:linear-gradient(135deg,#edf6ff,#fff);}
.kpi.blue {background:linear-gradient(135deg,#eef6ff,#fff);}
.kpi.green {background:linear-gradient(135deg,#edf9f3,#fff);}
.kpi.orange {background:linear-gradient(135deg,#fff5e9,#fff);}
.kpi.red {background:linear-gradient(135deg,#fff0f1,#fff);}
.kpi .label {font-size:15px; font-weight:700; color:#173b72;}
.kpi .value {font-size:28px; font-weight:800; color:#0b3478; margin-top:6px;}
.kpi .share {font-size:15px; font-weight:700; margin-top:5px;}
.kpi .small {font-size:11px; color:#536b8d; margin-top:4px;}
[data-testid="stDateInput"], [data-testid="stSelectbox"] {
    background:white; border-radius:12px;
}
div[data-testid="stDataFrame"] {border:1px solid #d8e6f7; border-radius:12px;}
hr {border:none; border-top:1px solid #dbe7f5;}
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def format_int(x):
    return f"{int(round(x)):,}".replace(",", ".")

def format_pct(x):
    return f"{x:.2f}".replace(".", ",") + "%"

def normalize_mode(x):
    return str(x).strip().upper()

@st.cache_data
def load_data(path):
    df = pd.read_json(path)
    df.columns = df.columns.str.strip()
    required = {"Tanggal", "Jenis Transportasi", "Jumlah Penumpang Per-hari"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(sorted(missing)))
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True, errors="coerce")
    df["Jenis Transportasi"] = df["Jenis Transportasi"].map(normalize_mode)
    df["Jumlah Penumpang Per-hari"] = pd.to_numeric(
        df["Jumlah Penumpang Per-hari"], errors="coerce"
    )
    df = df.dropna(subset=["Tanggal", "Jenis Transportasi", "Jumlah Penumpang Per-hari"])
    df = df[df["Jumlah Penumpang Per-hari"] >= 0].copy()
    df["Tahun"] = df["Tanggal"].dt.year.astype(int)
    return df.sort_values("Tanggal").reset_index(drop=True)

def mode_total(data, mode):
    return data.loc[data["Jenis Transportasi"].eq(mode), "Jumlah Penumpang Per-hari"].sum()

def draw_kpi(container, label, value, share=None, css="blue", icon="●"):
    with container:
        share_html = "" if share is None else f'<div class="share">{format_pct(share)}</div><div class="small">dari total penumpang</div>'
        st.markdown(
            f"""<div class="kpi {css}">
            <div class="label">{icon}&nbsp;&nbsp;{label}</div>
            <div class="value">{format_int(value)}</div>
            {share_html}
            </div>""", unsafe_allow_html=True
        )

# ---------- LOAD ----------
try:
    df = load_data(DATA_FILE)
except Exception as e:
    st.error(f"Gagal membaca dataset: {e}")
    st.stop()

# ---------- HEADER ----------
st.markdown("""
<div class="hero">
  <h1>Jumlah Penumpang Angkutan Umum yang Terlayani per Hari</h1>
  <h2>Provinsi DKI Jakarta</h2>
  <p>Sumber: Satu Data Jakarta &nbsp;|&nbsp; Dataset: Jumlah Penumpang Angkutan Umum yang Terlayani per Hari</p>
</div>
""", unsafe_allow_html=True)

# ---------- FILTERS ----------
years = sorted(df["Tahun"].unique().tolist(), reverse=True)
f1, f2, f3 = st.columns([1.55, 1.15, .7])

with f3:
    selected_year = st.selectbox("Tahun", years, index=0)

year_df = df[df["Tahun"].eq(selected_year)].copy()
min_date, max_date = year_df["Tanggal"].min().date(), year_df["Tanggal"].max().date()

with f1:
    selected_dates = st.date_input(
        "Tanggal",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )

with f2:
    mode_options = ["Semua"] + sorted(year_df["Jenis Transportasi"].unique().tolist())
    selected_mode = st.selectbox("Jenis Transportasi", mode_options)

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

filtered = year_df[
    (year_df["Tanggal"].dt.date >= start_date) &
    (year_df["Tanggal"].dt.date <= end_date)
].copy()

if selected_mode != "Semua":
    filtered = filtered[filtered["Jenis Transportasi"].eq(selected_mode)].copy()

if filtered.empty:
    st.warning("Tidak terdapat data untuk kombinasi filter yang dipilih.")
    st.stop()

# ---------- KPI ----------
total = filtered["Jumlah Penumpang Per-hari"].sum()
preferred = ["TRANSJAKARTA", "KRL", "MRT", "KAPAL"]
available = filtered["Jenis Transportasi"].unique().tolist()
display_modes = [m for m in preferred if m in available]
for m in sorted(available, key=lambda x: mode_total(filtered, x), reverse=True):
    if m not in display_modes and len(display_modes) < 4:
        display_modes.append(m)

kcols = st.columns(5)
draw_kpi(kcols[0], "Total Penumpang", total, None, "total", "👥")
styles = ["green", "orange", "blue", "red"]
icons = {"TRANSJAKARTA":"🚌", "KRL":"🚆", "MRT":"🚇", "KAPAL":"⛴️", "LRT":"🚈", "MIKROTRANS":"🚐"}
for i in range(4):
    if i < len(display_modes):
        m = display_modes[i]
        val = mode_total(filtered, m)
        share = (val / total * 100) if total else 0
        draw_kpi(kcols[i+1], m.title() if m != "KRL" and m != "MRT" else m,
                 val, share, styles[i], icons.get(m, "●"))
    else:
        draw_kpi(kcols[i+1], "Tidak tersedia", 0, 0, styles[i], "●")

st.write("")

# ---------- CHART DATA ----------
daily = (filtered.groupby(["Tanggal","Jenis Transportasi"], as_index=False)
         ["Jumlah Penumpang Per-hari"].sum())
by_mode = (filtered.groupby("Jenis Transportasi", as_index=False)
           ["Jumlah Penumpang Per-hari"].sum()
           .sort_values("Jumlah Penumpang Per-hari", ascending=False))

# ---------- ROW 1 ----------
left, right = st.columns([1.05, .95], gap="large")

with left:
    st.markdown('<div class="section-title">Tren Jumlah Penumpang per Hari</div>', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    for mode, g in daily.groupby("Jenis Transportasi"):
        ax.plot(g["Tanggal"], g["Jumlah Penumpang Per-hari"], marker="o",
                markersize=2.8, linewidth=1.6, label=mode.title())
    ax.set_ylabel("Jumlah Penumpang")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=.22)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_int(x)))
    ax.tick_params(axis="x", rotation=35)
    if daily["Jenis Transportasi"].nunique() <= 8:
        ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

with right:
    st.markdown('<div class="section-title">Total Penumpang per Jenis Transportasi</div>', unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bars = ax.bar(by_mode["Jenis Transportasi"], by_mode["Jumlah Penumpang Per-hari"])
    ax.set_ylabel("Total Penumpang")
    ax.grid(axis="y", alpha=.22)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: format_int(x)))
    ax.tick_params(axis="x", rotation=35)
    ymax = by_mode["Jumlah Penumpang Per-hari"].max()
    for bar, val in zip(bars, by_mode["Jumlah Penumpang Per-hari"]):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+ymax*.015,
                format_int(val), ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.margins(y=.15)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# ---------- ROW 2 ----------
left2, right2 = st.columns([1.05, .95], gap="large")

with left2:
    st.markdown('<div class="section-title">Data Jumlah Penumpang per Hari</div>', unsafe_allow_html=True)
    table = filtered[["Tanggal","Jenis Transportasi","Jumlah Penumpang Per-hari"]].copy()
    table["Tanggal"] = table["Tanggal"].dt.strftime("%d/%m/%Y")
    table["Jumlah Penumpang Per-hari"] = table["Jumlah Penumpang Per-hari"].map(format_int)
    st.dataframe(table, use_container_width=True, hide_index=True, height=410)

with right2:
    st.markdown('<div class="section-title">Proporsi Penumpang per Jenis Transportasi</div>', unsafe_allow_html=True)
    pie = by_mode[by_mode["Jumlah Penumpang Per-hari"] > 0].copy()
    fig, ax = plt.subplots(figsize=(7.5, 5.1))
    wedges, _ = ax.pie(
        pie["Jumlah Penumpang Per-hari"],
        startangle=90,
        wedgeprops=dict(width=.38, edgecolor="white")
    )
    ax.text(0, .05, format_int(total), ha="center", va="center",
            fontsize=17, fontweight="bold")
    ax.text(0, -.12, "Total Penumpang", ha="center", va="center", fontsize=9)
    labels = []
    for _, row in pie.iterrows():
        pct = row["Jumlah Penumpang Per-hari"] / total * 100 if total else 0
        labels.append(f'{row["Jenis Transportasi"].title()}  {format_pct(pct)}')
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0,.5),
              frameon=False, fontsize=8)
    ax.set_aspect("equal")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

st.caption(
    f"Periode ditampilkan: {start_date.strftime('%d/%m/%Y')} – "
    f"{end_date.strftime('%d/%m/%Y')} | Tahun {selected_year}"
)
