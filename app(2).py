import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Hotel Booking Dashboard", page_icon="🏨", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.3rem;padding-bottom:2rem}
[data-testid="stMetric"]{background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.18);padding:14px 16px;border-radius:14px}
</style>""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    base = Path(__file__).resolve().parent
    path = base / "hotel_bookings_dashboard.csv.gz"
    if not path.exists():
        return None, base

    df = pd.read_csv(path, compression="gzip")

    nums = ["is_canceled","lead_time","arrival_date_day_of_month",
            "stays_in_weekend_nights","stays_in_week_nights",
            "adults","adr","total_of_special_requests"]
    for c in nums:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # arrival_date_year pada data asli berbentuk "01/01/2015"
    ydate = pd.to_datetime(df["arrival_date_year"], errors="coerce", dayfirst=True)
    df["arrival_year"] = ydate.dt.year.fillna(
        pd.to_numeric(df["arrival_date_year"], errors="coerce")
    )

    months = {
        "January":1,"February":2,"March":3,"April":4,
        "May":5,"June":6,"July":7,"August":8,
        "September":9,"October":10,"November":11,"December":12
    }
    df["month_num"] = df["arrival_date_month"].map(months)

    df["arrival_date"] = pd.to_datetime(
        dict(
            year=df["arrival_year"],
            month=df["month_num"],
            day=df["arrival_date_day_of_month"]
        ),
        errors="coerce"
    )

    df["total_nights"] = (
        df["stays_in_weekend_nights"].fillna(0)
        + df["stays_in_week_nights"].fillna(0)
    )

    df["booking_value_est"] = df["adr"].fillna(0) * df["total_nights"]

    df["lead_time_group"] = pd.cut(
        df["lead_time"],
        [-1,7,30,90,180,np.inf],
        labels=["0–7","8–30","31–90","91–180",">180"],
        ordered=True
    )
    return df, base

df, base = load_data()
st.title("🏨 Hotel Booking Performance Dashboard")
if df is None:
    st.error("File `hotel_bookings_dashboard.csv.gz` tidak ditemukan. Letakkan di folder yang sama dengan `app.py`.")
    st.code("repository/\n├── app.py\n├── hotel_bookings_dashboard.csv.gz\n└── requirements.txt")
    st.stop()

valid = df["arrival_date"].dropna()
dmin,dmax = valid.min().date(),valid.max().date()
st.caption(f"Booking, cancellation, ADR, lead time, customer & channel • {dmin:%d %b %Y} – {dmax:%d %b %Y}")

st.sidebar.header("Filter Dashboard")
dr=st.sidebar.date_input("Tanggal kedatangan",(dmin,dmax),min_value=dmin,max_value=dmax)
start,end=(dr if isinstance(dr,(tuple,list)) and len(dr)==2 else (dmin,dmax))

def ms(label,col,top=None):
    s=df[col].dropna().astype(str)
    vals=(s.value_counts().head(top).index.tolist() if top else sorted(s.unique().tolist()))
    return st.sidebar.multiselect(label,vals)

filters=[
("hotel",ms("Hotel","hotel")),
("market_segment",ms("Market Segment","market_segment")),
("distribution_channel",ms("Distribution Channel","distribution_channel")),
("customer_type",ms("Customer Type","customer_type")),
("deposit_type",ms("Deposit Type","deposit_type")),
("reservation_status",ms("Reservation Status","reservation_status")),
("country",ms("Country (Top 30)","country",30))
]
f=df[(df["arrival_date"].dt.date>=start)&(df["arrival_date"].dt.date<=end)].copy()
for col,vals in filters:
    if vals: f=f[f[col].astype(str).isin(vals)]
if f.empty:
    st.warning("Tidak ada data untuk filter yang dipilih."); st.stop()

n=len(f); cancel=int(f["is_canceled"].eq(1).sum()); ok=int(f["is_canceled"].eq(0).sum())
rate=cancel/n*100
k=st.columns(6)
k[0].metric("Total Bookings",f"{n:,}")
k[1].metric("Canceled",f"{cancel:,}")
k[2].metric("Cancellation Rate",f"{rate:.2f}%")
k[3].metric("Non-Canceled",f"{ok:,}")
k[4].metric("Average ADR",f"{f['adr'].mean():,.2f}")
k[5].metric("Avg. Lead Time",f"{f['lead_time'].mean():,.1f} hari")
st.divider()

monthly=(f.dropna(subset=["arrival_date"]).assign(month=lambda x:x["arrival_date"].dt.to_period("M").dt.to_timestamp())
         .groupby("month",as_index=False).agg(Bookings=("is_canceled","size"),Canceled=("is_canceled","sum"),ADR=("adr","mean")))
monthly["Cancellation Rate"]=monthly["Canceled"]/monthly["Bookings"]*100
a,b=st.columns(2)
with a:
    st.subheader("Booking Trend")
    fig=px.line(monthly,x="month",y="Bookings",markers=True,labels={"month":"Month"})
    fig.update_layout(height=380,hovermode="x unified"); st.plotly_chart(fig,use_container_width=True)
with b:
    st.subheader("Cancellation Rate Trend")
    fig=px.line(monthly,x="month",y="Cancellation Rate",markers=True,
                labels={"month":"Month","Cancellation Rate":"Cancellation Rate (%)"})
    fig.update_layout(height=380,hovermode="x unified"); st.plotly_chart(fig,use_container_width=True)

def perf(col):
    z=f.groupby(col,dropna=False,as_index=False).agg(Bookings=("is_canceled","size"),Canceled=("is_canceled","sum"))
    z["Cancellation Rate"]=z["Canceled"]/z["Bookings"]*100
    return z

st.subheader("Hotel Performance")
hp=perf("hotel").merge(f.groupby("hotel",as_index=False)["adr"].mean(),on="hotel")
a,b=st.columns(2)
with a:
    st.plotly_chart(px.bar(hp,x="hotel",y="Bookings",text_auto=",",title="Total Bookings by Hotel"),use_container_width=True)
with b:
    st.plotly_chart(px.bar(hp,x="hotel",y="Cancellation Rate",text_auto=".1f",
                           title="Cancellation Rate by Hotel"),use_container_width=True)

st.subheader("Cancellation Drivers")
sp,cp=perf("market_segment"),perf("distribution_channel")
a,b=st.columns(2)
with a:
    st.plotly_chart(px.bar(sp.sort_values("Cancellation Rate"),x="Cancellation Rate",y="market_segment",
                           orientation="h",text_auto=".1f",title="By Market Segment"),use_container_width=True)
with b:
    st.plotly_chart(px.bar(cp.sort_values("Cancellation Rate"),x="Cancellation Rate",y="distribution_channel",
                           orientation="h",text_auto=".1f",title="By Distribution Channel"),use_container_width=True)

lead=(f.groupby("lead_time_group",observed=False,as_index=False)
      .agg(Bookings=("is_canceled","size"),Canceled=("is_canceled","sum")))
lead["Cancellation Rate"]=np.where(lead["Bookings"]>0,lead["Canceled"]/lead["Bookings"]*100,np.nan)
dep=perf("deposit_type")
a,b=st.columns(2)
with a:
    st.plotly_chart(px.bar(lead,x="lead_time_group",y="Cancellation Rate",text_auto=".1f",
                           title="Cancellation Rate by Lead Time"),use_container_width=True)
with b:
    st.plotly_chart(px.bar(dep,x="deposit_type",y="Cancellation Rate",text_auto=".1f",
                           title="Cancellation Rate by Deposit Type"),use_container_width=True)

st.subheader("Customer & Market Profile")
cust=perf("customer_type")
country=(f.groupby("country",as_index=False).size().rename(columns={"size":"Bookings"}).nlargest(10,"Bookings").sort_values("Bookings"))
a,b=st.columns(2)
with a:
    st.plotly_chart(px.bar(cust,x="customer_type",y="Bookings",text_auto=",",title="Bookings by Customer Type"),use_container_width=True)
with b:
    st.plotly_chart(px.bar(country,x="Bookings",y="country",orientation="h",text_auto=",",title="Top 10 Countries"),use_container_width=True)

st.subheader("Price & Stay Analysis")
a,b=st.columns(2)
with a:
    st.plotly_chart(px.line(monthly,x="month",y="ADR",markers=True,title="Average ADR by Month"),use_container_width=True)
with b:
    stay=f.groupby("hotel",as_index=False).agg(Average_Nights=("total_nights","mean"))
    st.plotly_chart(px.bar(stay,x="hotel",y="Average_Nights",text_auto=".2f",title="Average Length of Stay"),use_container_width=True)

st.subheader("💡 Automatic Insights")
hr=hp.loc[hp["Cancellation Rate"].idxmax()]
sr=sp.loc[sp["Cancellation Rate"].idxmax()]
cr=cp.loc[cp["Cancellation Rate"].idxmax()]
x,y,z=st.columns(3)
x.info(f"**Highest hotel cancellation rate**\n\n{hr['hotel']}: **{hr['Cancellation Rate']:.2f}%**.")
y.info(f"**Highest-risk market segment**\n\n{sr['market_segment']}: **{sr['Cancellation Rate']:.2f}%**.")
z.info(f"**Highest-risk channel**\n\n{cr['distribution_channel']}: **{cr['Cancellation Rate']:.2f}%**.")

with st.expander("📋 View Filtered Data"):
    cols=["arrival_date","hotel","is_canceled","lead_time","total_nights","country","market_segment",
          "distribution_channel","deposit_type","customer_type","adr","total_of_special_requests","reservation_status"]
    show=f[cols].copy(); show["arrival_date"]=show["arrival_date"].dt.strftime("%d-%m-%Y")
    st.dataframe(show,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download Filtered Data",show.to_csv(index=False).encode("utf-8"),
                       "hotel_booking_filtered.csv","text/csv")

st.caption("Cancellation rate = canceled bookings / total bookings pada filter aktif. ADR ditampilkan sebagai nilai rata-rata.")
