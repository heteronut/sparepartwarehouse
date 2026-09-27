"""
pages/analytics.py — Analitik & Laporan Biaya Sparepart
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import get_connection


def _summary_metrics():
    conn = get_connection()
    total_parts   = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1").fetchone()[0]
    total_value   = conn.execute("SELECT SUM(current_stock * unit_price) FROM spare_parts WHERE is_active=1").fetchone()[0] or 0
    low_stock     = conn.execute(
        "SELECT COUNT(*) FROM spare_parts WHERE is_active=1 AND current_stock <= min_stock"
    ).fetchone()[0]
    total_in_val  = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_in").fetchone()[0]
    total_out_val = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_out").fetchone()[0]
    conn.close()
    return total_parts, total_value, low_stock, total_in_val, total_out_val


def _monthly_trend(months: int = 12):
    conn = get_connection()
    df_in = pd.read_sql(f"""
        SELECT strftime('%Y-%m', transaction_date) AS month,
               SUM(total_cost) AS nilai_masuk
        FROM stock_in
        WHERE transaction_date >= DATE('now', '-{months} months')
        GROUP BY 1 ORDER BY 1
    """, conn)
    df_out = pd.read_sql(f"""
        SELECT strftime('%Y-%m', transaction_date) AS month,
               SUM(total_cost) AS nilai_keluar
        FROM stock_out
        WHERE transaction_date >= DATE('now', '-{months} months')
        GROUP BY 1 ORDER BY 1
    """, conn)
    conn.close()
    df = df_in.merge(df_out, on="month", how="outer").fillna(0).sort_values("month")
    return df


def _category_breakdown():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT c.name AS kategori,
               COUNT(sp.id) AS jumlah_part,
               COALESCE(SUM(sp.current_stock * sp.unit_price),0) AS nilai_stok
        FROM spare_parts sp
        JOIN categories c ON c.id = sp.category_id
        WHERE sp.is_active = 1
        GROUP BY c.name ORDER BY nilai_stok DESC
    """, conn)
    conn.close()
    return df


def _top_consumed(n=10, days=90):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT sp.part_number, sp.name,
               SUM(so.quantity) AS total_qty,
               SUM(so.total_cost) AS total_biaya
        FROM stock_out so
        JOIN spare_parts sp ON sp.id = so.part_id
        WHERE so.transaction_date >= DATE('now', '-{days} days')
        GROUP BY sp.id ORDER BY total_biaya DESC LIMIT {n}
    """, conn)
    conn.close()
    return df


def _supplier_spend(days=90):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT COALESCE(s.name,'(Tanpa Supplier)') AS supplier,
               SUM(si.total_cost) AS total_pembelian,
               COUNT(*) AS jumlah_transaksi
        FROM stock_in si
        LEFT JOIN suppliers s ON s.id = si.supplier_id
        WHERE si.transaction_date >= DATE('now', '-{days} days')
        GROUP BY s.id ORDER BY total_pembelian DESC
    """, conn)
    conn.close()
    return df


def _dept_spend(days=90):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT COALESCE(department,'(Tidak Diisi)') AS departemen,
               SUM(total_cost) AS total_pemakaian,
               COUNT(*) AS jumlah_transaksi
        FROM stock_out
        WHERE transaction_date >= DATE('now', '-{days} days')
        GROUP BY department ORDER BY total_pemakaian DESC
    """, conn)
    conn.close()
    return df


def _stock_age():
    """Parts with no outgoing movement in last 90 days."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT sp.part_number, sp.name, sp.current_stock, sp.unit_price,
               sp.current_stock * sp.unit_price AS nilai,
               MAX(so.transaction_date) AS last_used
        FROM spare_parts sp
        LEFT JOIN stock_out so ON so.part_id = sp.id
        WHERE sp.is_active = 1 AND sp.current_stock > 0
        GROUP BY sp.id
        HAVING last_used IS NULL OR last_used < DATE('now','-90 days')
        ORDER BY nilai DESC LIMIT 20
    """, conn)
    conn.close()
    return df


# ── main page ───────────────────────────────────────────────
def render():
    st.header("📊 Analitik & Laporan Biaya")

    total_parts, total_value, low_stock, total_in, total_out = _summary_metrics()

    # KPI cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Sparepart Aktif", f"{total_parts:,}")
    c2.metric("Nilai Inventori", f"Rp {total_value:,.0f}")
    c3.metric("Stok Kritis ⚠️", str(low_stock), delta=None)
    c4.metric("Total Pembelian", f"Rp {total_in:,.0f}")
    c5.metric("Total Pemakaian", f"Rp {total_out:,.0f}")

    st.divider()

    days_opt = st.selectbox("📅 Periode Analisis",
                            [30, 60, 90, 180, 365],
                            index=2,
                            format_func=lambda d: f"{d} hari terakhir")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Tren Biaya", "🏷️ Kategori", "🔝 Top Pemakaian",
        "🏭 Supplier", "💤 Stok Tidak Aktif"
    ])

    # ── TREND ─────────────────────────────────────────────
    with tab1:
        months = max(1, days_opt // 30)
        df_trend = _monthly_trend(months)
        if df_trend.empty:
            st.info("Belum ada data transaksi.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Pembelian (Masuk)", x=df_trend["month"],
                                 y=df_trend["nilai_masuk"], marker_color="#3b82f6"))
            fig.add_trace(go.Bar(name="Pemakaian (Keluar)", x=df_trend["month"],
                                 y=df_trend["nilai_keluar"], marker_color="#ef4444"))
            fig.update_layout(
                barmode="group", title="Tren Biaya Bulanan",
                xaxis_title="Bulan", yaxis_title="Nilai (Rp)",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Net flow
            df_trend["net_flow"] = df_trend["nilai_masuk"] - df_trend["nilai_keluar"]
            fig2 = px.line(df_trend, x="month", y="net_flow",
                           title="Net Flow Biaya (Masuk - Keluar)",
                           labels={"month":"Bulan","net_flow":"Net (Rp)"},
                           markers=True)
            fig2.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig2, use_container_width=True)

    # ── CATEGORY ──────────────────────────────────────────
    with tab2:
        df_cat = _category_breakdown()
        if df_cat.empty:
            st.info("Belum ada data.")
        else:
            col_a, col_b = st.columns(2)
            fig_pie = px.pie(df_cat, names="kategori", values="nilai_stok",
                             title="Distribusi Nilai Stok per Kategori",
                             hole=0.4)
            col_a.plotly_chart(fig_pie, use_container_width=True)

            fig_bar = px.bar(df_cat.sort_values("jumlah_part", ascending=True),
                             x="jumlah_part", y="kategori", orientation="h",
                             title="Jumlah Part per Kategori",
                             labels={"jumlah_part":"Jumlah Part","kategori":"Kategori"},
                             color="nilai_stok", color_continuous_scale="Blues")
            col_b.plotly_chart(fig_bar, use_container_width=True)

            st.dataframe(
                df_cat.rename(columns={"kategori":"Kategori","jumlah_part":"Jumlah Part",
                                       "nilai_stok":"Nilai Stok (Rp)"}),
                use_container_width=True
            )

    # ── TOP CONSUMPTION ───────────────────────────────────
    with tab3:
        df_top = _top_consumed(days=days_opt)
        if df_top.empty:
            st.info("Belum ada data pengeluaran.")
        else:
            fig = px.bar(df_top.sort_values("total_biaya"),
                         x="total_biaya", y="name", orientation="h",
                         title=f"Top 10 Sparepart Paling Banyak Dipakai ({days_opt} Hari)",
                         labels={"total_biaya":"Total Biaya (Rp)","name":"Sparepart"},
                         color="total_biaya", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                df_top.rename(columns={"part_number":"Part #","name":"Nama",
                                       "total_qty":"Total Qty","total_biaya":"Total Biaya (Rp)"}),
                use_container_width=True
            )

    # ── SUPPLIER ──────────────────────────────────────────
    with tab4:
        df_sup = _supplier_spend(days=days_opt)
        if df_sup.empty:
            st.info("Belum ada pembelian.")
        else:
            fig = px.bar(df_sup, x="supplier", y="total_pembelian",
                         title=f"Total Pembelian per Supplier ({days_opt} Hari)",
                         labels={"total_pembelian":"Total (Rp)","supplier":"Supplier"},
                         color="total_pembelian", color_continuous_scale="Greens",
                         text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

            df_dept = _dept_spend(days=days_opt)
            if not df_dept.empty:
                fig2 = px.pie(df_dept, names="departemen", values="total_pemakaian",
                              title=f"Pemakaian per Departemen ({days_opt} Hari)", hole=0.35)
                st.plotly_chart(fig2, use_container_width=True)

    # ── SLOW MOVING ───────────────────────────────────────
    with tab5:
        st.subheader("💤 Stok Tidak Bergerak (> 90 hari)")
        df_age = _stock_age()
        if df_age.empty:
            st.success("Tidak ada stok tidak bergerak. Inventori dalam kondisi baik! 🎉")
        else:
            total_idle = df_age["nilai"].sum()
            st.warning(f"Terdapat **{len(df_age)}** part senilai **Rp {total_idle:,.0f}** yang tidak bergerak.")
            st.dataframe(
                df_age.rename(columns={
                    "part_number":"Part #","name":"Nama","current_stock":"Stok",
                    "unit_price":"Harga Satuan","nilai":"Nilai (Rp)","last_used":"Terakhir Dipakai"
                }),
                use_container_width=True
            )
