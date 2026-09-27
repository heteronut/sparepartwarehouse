"""
pages/dashboard.py — Beranda / Ringkasan Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_connection


def _kpi():
    conn = get_connection()
    r = {}
    r["total_parts"]   = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1").fetchone()[0]
    r["total_value"]   = conn.execute("SELECT COALESCE(SUM(current_stock*unit_price),0) FROM spare_parts WHERE is_active=1").fetchone()[0]
    r["low_stock"]     = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1 AND current_stock<=min_stock").fetchone()[0]
    r["out_of_stock"]  = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1 AND current_stock=0").fetchone()[0]
    r["total_in_30"]   = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_in WHERE transaction_date>=DATE('now','-30 days')").fetchone()[0]
    r["total_out_30"]  = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_out WHERE transaction_date>=DATE('now','-30 days')").fetchone()[0]
    r["open_wo"]       = conn.execute("SELECT COUNT(*) FROM maintenance_requests WHERE status IN ('Pending','In Progress')").fetchone()[0]
    r["suppliers"]     = conn.execute("SELECT COUNT(*) FROM suppliers WHERE is_active=1").fetchone()[0]
    conn.close()
    return r


def _recent_in(n=5):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT si.transaction_date, sp.name, si.quantity,
               su.name AS supplier, si.total_cost
        FROM stock_in si
        JOIN spare_parts sp ON sp.id=si.part_id
        LEFT JOIN suppliers su ON su.id=si.supplier_id
        ORDER BY si.id DESC LIMIT {n}
    """, conn)
    conn.close()
    return df


def _recent_out(n=5):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT so.transaction_date, sp.name, so.quantity,
               so.department, so.total_cost
        FROM stock_out so
        JOIN spare_parts sp ON sp.id=so.part_id
        ORDER BY so.id DESC LIMIT {n}
    """, conn)
    conn.close()
    return df


def _category_pie():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT c.name AS kategori,
               COALESCE(SUM(sp.current_stock*sp.unit_price),0) AS nilai
        FROM spare_parts sp
        JOIN categories c ON c.id=sp.category_id
        WHERE sp.is_active=1
        GROUP BY c.name HAVING nilai > 0
        ORDER BY nilai DESC
    """, conn)
    conn.close()
    return df


def _weekly_flow():
    conn = get_connection()
    df_in = pd.read_sql("""
        SELECT transaction_date AS tgl, SUM(total_cost) AS nilai_in
        FROM stock_in WHERE transaction_date>=DATE('now','-14 days')
        GROUP BY tgl ORDER BY tgl
    """, conn)
    df_out = pd.read_sql("""
        SELECT transaction_date AS tgl, SUM(total_cost) AS nilai_out
        FROM stock_out WHERE transaction_date>=DATE('now','-14 days')
        GROUP BY tgl ORDER BY tgl
    """, conn)
    conn.close()
    df = df_in.merge(df_out, on="tgl", how="outer").fillna(0).sort_values("tgl")
    return df


def render():
    st.header("🏠 Dashboard Gudang Sparepart")
    st.caption("Ringkasan kondisi gudang secara real-time")

    kpi = _kpi()

    # ── KPI row 1 ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔩 Total Sparepart", f"{kpi['total_parts']:,}")
    c2.metric("💰 Nilai Inventori",  f"Rp {kpi['total_value']:,.0f}")
    c3.metric("⚠️ Stok Kritis",      str(kpi["low_stock"]),
              delta=f"{kpi['out_of_stock']} HABIS", delta_color="inverse")
    c4.metric("🔧 WO Terbuka",       str(kpi["open_wo"]))

    # ── KPI row 2 ─────────────────────────────────────────
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("📥 Pembelian 30 Hari",  f"Rp {kpi['total_in_30']:,.0f}")
    c6.metric("📤 Pemakaian 30 Hari",  f"Rp {kpi['total_out_30']:,.0f}")
    net = kpi["total_in_30"] - kpi["total_out_30"]
    c7.metric("📊 Net Flow 30 Hari",   f"Rp {net:,.0f}",
              delta="▲ surplus" if net >= 0 else "▼ defisit",
              delta_color="normal" if net >= 0 else "inverse")
    c8.metric("🏭 Supplier Aktif",     str(kpi["suppliers"]))

    st.divider()

    # ── Charts ────────────────────────────────────────────
    col_l, col_r = st.columns([1.6, 1])

    with col_l:
        df_flow = _weekly_flow()
        if df_flow.empty:
            st.info("Belum ada data transaksi 14 hari terakhir.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_flow["tgl"], y=df_flow["nilai_in"],
                                     mode="lines+markers", name="Pembelian",
                                     line=dict(color="#3b82f6", width=2),
                                     fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"))
            fig.add_trace(go.Scatter(x=df_flow["tgl"], y=df_flow["nilai_out"],
                                     mode="lines+markers", name="Pemakaian",
                                     line=dict(color="#ef4444", width=2),
                                     fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"))
            fig.update_layout(
                title="Aliran Biaya 14 Hari Terakhir",
                xaxis_title="Tanggal", yaxis_title="Nilai (Rp)",
                height=300, margin=dict(l=0, r=0, t=40, b=0),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        df_cat = _category_pie()
        if not df_cat.empty:
            fig2 = px.pie(df_cat, names="kategori", values="nilai",
                          title="Nilai Stok per Kategori",
                          hole=0.45, height=300)
            fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0),
                                showlegend=True,
                                legend=dict(font=dict(size=10)))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Recent transactions ────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📥 Penerimaan Terbaru")
        df_in = _recent_in()
        if df_in.empty:
            st.info("Belum ada transaksi masuk.")
        else:
            st.dataframe(
                df_in.rename(columns={
                    "transaction_date":"Tanggal","name":"Sparepart",
                    "quantity":"Qty","supplier":"Supplier","total_cost":"Total (Rp)"
                }),
                use_container_width=True, hide_index=True
            )

    with col_b:
        st.subheader("📤 Pengeluaran Terbaru")
        df_out = _recent_out()
        if df_out.empty:
            st.info("Belum ada transaksi keluar.")
        else:
            st.dataframe(
                df_out.rename(columns={
                    "transaction_date":"Tanggal","name":"Sparepart",
                    "quantity":"Qty","department":"Dept","total_cost":"Total (Rp)"
                }),
                use_container_width=True, hide_index=True
            )

    # ── Low stock alert banner ─────────────────────────────
    if kpi["low_stock"] > 0 or kpi["out_of_stock"] > 0:
        st.divider()
        st.warning(
            f"⚠️ **Perhatian!** Terdapat **{kpi['out_of_stock']}** sparepart HABIS dan "
            f"**{kpi['low_stock']}** sparepart di bawah stok minimum. "
            f"Segera lakukan pemesanan ulang. → Lihat **Peringatan Stok**"
        )
