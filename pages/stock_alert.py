"""
pages/stock_alert.py — Peringatan Stok & Reorder
"""
import streamlit as st
import pandas as pd
from database import get_connection


def _load_alerts():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            sp.id, sp.part_number, sp.name, sp.brand,
            c.name AS kategori,
            sp.current_stock, sp.min_stock, sp.reorder_point, sp.max_stock,
            sp.unit_price,
            COALESCE(s.name,'—') AS supplier,
            COALESCE(s.phone,'—') AS supplier_phone,
            CASE
                WHEN sp.current_stock = 0               THEN 'HABIS'
                WHEN sp.current_stock <= sp.min_stock   THEN 'KRITIS'
                WHEN sp.current_stock <= sp.reorder_point THEN 'REORDER'
                ELSE 'OK'
            END AS status
        FROM spare_parts sp
        LEFT JOIN categories c ON c.id = sp.category_id
        LEFT JOIN suppliers  s ON s.id = sp.supplier_id
        WHERE sp.is_active = 1
          AND sp.current_stock <= sp.reorder_point
        ORDER BY sp.current_stock ASC
    """, conn)
    conn.close()
    return df


def _load_all_stock():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT sp.part_number, sp.name, sp.brand,
               c.name AS kategori,
               sp.current_stock, sp.min_stock, sp.reorder_point, sp.max_stock,
               sp.unit_price,
               ROUND(CAST(sp.current_stock AS REAL) / NULLIF(sp.max_stock, 0) * 100, 1) AS pct_stok
        FROM spare_parts sp
        LEFT JOIN categories c ON c.id = sp.category_id
        WHERE sp.is_active = 1
        ORDER BY pct_stok ASC
    """, conn)
    conn.close()
    return df


def render():
    st.header("🚨 Peringatan Stok & Reorder")

    df_alert = _load_alerts()

    # summary badges
    if df_alert.empty:
        st.success("✅ Semua stok dalam kondisi aman. Tidak ada peringatan saat ini.")
    else:
        habis   = len(df_alert[df_alert["status"] == "HABIS"])
        kritis  = len(df_alert[df_alert["status"] == "KRITIS"])
        reorder = len(df_alert[df_alert["status"] == "REORDER"])

        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 HABIS",   habis,  delta=None)
        c2.metric("🟠 KRITIS",  kritis, delta=None)
        c3.metric("🟡 REORDER", reorder, delta=None)

        st.divider()

        # colour by status
        STATUS_COLOR = {"HABIS": "#ff4b4b", "KRITIS": "#ff9d00", "REORDER": "#ffe066"}

        def row_style(row):
            color = STATUS_COLOR.get(row["status"], "")
            if color:
                return [f"background-color: {color}20; color: #1f2328"] * len(row)
            return [""] * len(row)

        rename = {
            "part_number":"Part #","name":"Nama","brand":"Brand",
            "kategori":"Kategori","current_stock":"Stok",
            "min_stock":"Min","reorder_point":"Reorder","max_stock":"Max",
            "unit_price":"Harga Satuan","supplier":"Supplier",
            "supplier_phone":"Telp Supplier","status":"Status"
        }
        styled = df_alert.rename(columns=rename).style\
            .apply(row_style, axis=1)\
            .format({"Harga Satuan": "Rp {:,.0f}"})

        st.dataframe(styled, use_container_width=True, height=450)

        # download
        csv = df_alert.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Daftar Reorder (CSV)", csv,
                           file_name="reorder_list.csv", mime="text/csv")

    st.divider()
    st.subheader("📊 Status Keseluruhan Stok")

    df_all = _load_all_stock()
    if df_all.empty:
        st.info("Belum ada data sparepart.")
    else:
        import plotly.express as px
        top20 = df_all.head(20)
        colors = []
        for _, r in top20.iterrows():
            if r["current_stock"] == 0:
                colors.append("#ef4444")
            elif r["current_stock"] <= r["min_stock"]:
                colors.append("#f97316")
            elif r["current_stock"] <= r["reorder_point"]:
                colors.append("#eab308")
            else:
                colors.append("#22c55e")

        fig = px.bar(
            top20, x="name", y="current_stock",
            title="Level Stok 20 Part Terendah",
            labels={"current_stock": "Stok", "name": "Sparepart"},
        )
        fig.update_traces(marker_color=colors)
        fig.add_hline(y=top20["min_stock"].mean(), line_dash="dash",
                      line_color="red", annotation_text="Avg Min Stock")
        st.plotly_chart(fig, use_container_width=True)
