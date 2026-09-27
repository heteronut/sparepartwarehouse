"""
pages/reports.py — Laporan & Ekspor Data
"""
import streamlit as st
import pandas as pd
import io
from database import get_connection


def _report_inventory():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT sp.part_number, sp.name, sp.brand, sp.model,
               c.name AS kategori,
               u.symbol AS satuan,
               l.rack||'-'||l.shelf||'-'||COALESCE(l.bin,'') AS lokasi,
               s.name AS supplier,
               sp.unit_price, sp.current_stock, sp.min_stock, sp.max_stock,
               sp.reorder_point,
               sp.current_stock * sp.unit_price AS nilai_stok,
               CASE
                   WHEN sp.current_stock = 0                THEN 'HABIS'
                   WHEN sp.current_stock <= sp.min_stock    THEN 'KRITIS'
                   WHEN sp.current_stock <= sp.reorder_point THEN 'REORDER'
                   ELSE 'OK'
               END AS status_stok
        FROM spare_parts sp
        LEFT JOIN categories c ON c.id = sp.category_id
        LEFT JOIN units      u ON u.id = sp.unit_id
        LEFT JOIN locations  l ON l.id = sp.location_id
        LEFT JOIN suppliers  s ON s.id = sp.supplier_id
        WHERE sp.is_active = 1
        ORDER BY sp.name
    """, conn)
    conn.close()
    return df


def _report_transactions(start_date, end_date):
    conn = get_connection()
    df_in = pd.read_sql("""
        SELECT 'MASUK' AS jenis, si.transaction_date,
               sp.part_number, sp.name, si.quantity, si.unit_price, si.total_cost,
               su.name AS supplier, si.po_number, si.invoice_number,
               si.received_by, NULL AS work_order, NULL AS department
        FROM stock_in si
        JOIN spare_parts sp ON sp.id = si.part_id
        LEFT JOIN suppliers su ON su.id = si.supplier_id
        WHERE si.transaction_date BETWEEN ? AND ?
    """, conn, params=(str(start_date), str(end_date)))

    df_out = pd.read_sql("""
        SELECT 'KELUAR' AS jenis, so.transaction_date,
               sp.part_number, sp.name, so.quantity, so.unit_price, so.total_cost,
               NULL AS supplier, NULL AS po_number, NULL AS invoice_number,
               so.requested_by, so.work_order, so.department
        FROM stock_out so
        JOIN spare_parts sp ON sp.id = so.part_id
        WHERE so.transaction_date BETWEEN ? AND ?
    """, conn, params=(str(start_date), str(end_date)))
    conn.close()
    df = pd.concat([df_in, df_out]).sort_values(["transaction_date","jenis"])
    return df


def _report_opname(start_date, end_date):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT so.opname_date, sp.part_number, sp.name,
               so.system_stock, so.physical_stock, so.difference,
               so.reason, so.conducted_by
        FROM stock_opname so
        JOIN spare_parts sp ON sp.id = so.part_id
        WHERE so.opname_date BETWEEN ? AND ?
        ORDER BY so.opname_date DESC
    """, conn, params=(str(start_date), str(end_date)))
    conn.close()
    return df


def _report_maintenance(start_date, end_date):
    conn = get_connection()
    df = pd.read_sql("""
        SELECT request_number, machine_name, department, issue_desc,
               priority, status, requested_by, assigned_to,
               request_date, completion_date, notes
        FROM maintenance_requests
        WHERE request_date BETWEEN ? AND ?
        ORDER BY request_date DESC
    """, conn, params=(str(start_date), str(end_date)))
    conn.close()
    return df


def _to_excel(dfs: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()


def render():
    st.header("📑 Laporan & Ekspor Data")

    tab_inv, tab_trx, tab_all = st.tabs([
        "📦 Inventori", "💹 Transaksi", "📥 Ekspor Lengkap"
    ])

    # ── INVENTORY REPORT ──────────────────────────────────
    with tab_inv:
        st.subheader("Laporan Inventori Sparepart")
        df_inv = _report_inventory()

        if df_inv.empty:
            st.info("Belum ada data.")
        else:
            total_val = df_inv["nilai_stok"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Part", len(df_inv))
            c2.metric("Total Nilai Stok", f"Rp {total_val:,.0f}")
            c3.metric("Part Butuh Reorder",
                      len(df_inv[df_inv["status_stok"].isin(["HABIS","KRITIS","REORDER"])]))

            # filter
            status_f = st.multiselect("Filter Status Stok",
                                      ["OK","REORDER","KRITIS","HABIS"],
                                      default=["OK","REORDER","KRITIS","HABIS"])
            df_show = df_inv[df_inv["status_stok"].isin(status_f)] if status_f else df_inv

            st.dataframe(
                df_show.rename(columns={
                    "part_number":"Part #","name":"Nama","brand":"Brand","model":"Model",
                    "kategori":"Kategori","satuan":"Satuan","lokasi":"Lokasi",
                    "supplier":"Supplier","unit_price":"Harga Satuan",
                    "current_stock":"Stok","min_stock":"Min","max_stock":"Max",
                    "reorder_point":"Reorder","nilai_stok":"Nilai Stok","status_stok":"Status"
                }),
                use_container_width=True, height=450
            )

            # Export
            c_csv, c_xlsx = st.columns(2)
            csv = df_show.to_csv(index=False).encode("utf-8")
            c_csv.download_button("⬇️ Download CSV", csv, "laporan_inventori.csv", "text/csv")
            xlsx = _to_excel({"Inventori": df_show})
            c_xlsx.download_button("⬇️ Download Excel", xlsx,
                                   "laporan_inventori.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── TRANSACTION REPORT ────────────────────────────────
    with tab_trx:
        st.subheader("Laporan Transaksi")
        c1, c2 = st.columns(2)
        start = c1.date_input("Dari Tanggal", value=pd.Timestamp.now() - pd.Timedelta(days=30))
        end   = c2.date_input("Sampai Tanggal")

        df_trx = _report_transactions(start, end)
        if df_trx.empty:
            st.info("Tidak ada transaksi dalam periode ini.")
        else:
            total_in  = df_trx[df_trx["jenis"]=="MASUK"]["total_cost"].sum()
            total_out = df_trx[df_trx["jenis"]=="KELUAR"]["total_cost"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Pembelian",  f"Rp {total_in:,.0f}")
            c2.metric("Total Pemakaian",  f"Rp {total_out:,.0f}")
            c3.metric("Net Investasi",    f"Rp {total_in - total_out:,.0f}")

            st.dataframe(df_trx.rename(columns={
                "jenis":"Jenis","transaction_date":"Tanggal",
                "part_number":"Part #","name":"Nama",
                "quantity":"Qty","unit_price":"Harga Satuan","total_cost":"Total",
                "supplier":"Supplier","work_order":"WO","department":"Dept"
            }), use_container_width=True, height=400)

            c_csv, c_xlsx = st.columns(2)
            csv = df_trx.to_csv(index=False).encode("utf-8")
            c_csv.download_button("⬇️ CSV", csv, "laporan_transaksi.csv", "text/csv")
            xlsx = _to_excel({"Transaksi": df_trx})
            c_xlsx.download_button("⬇️ Excel", xlsx, "laporan_transaksi.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── FULL EXPORT ───────────────────────────────────────
    with tab_all:
        st.subheader("Ekspor Lengkap ke Excel")
        st.info("Ekspor semua data ke dalam satu file Excel multi-sheet.")
        c1, c2 = st.columns(2)
        start_a = c1.date_input("Dari", value=pd.Timestamp.now() - pd.Timedelta(days=90), key="all_start")
        end_a   = c2.date_input("Sampai", key="all_end")

        if st.button("📦 Generate & Download Excel", type="primary"):
            df_i = _report_inventory()
            df_t = _report_transactions(start_a, end_a)
            df_o = _report_opname(start_a, end_a)
            df_m = _report_maintenance(start_a, end_a)

            xlsx = _to_excel({
                "Inventori":    df_i,
                "Transaksi":    df_t,
                "Stock Opname": df_o,
                "Maintenance":  df_m,
            })
            st.download_button(
                "⬇️ Download File Excel Lengkap", xlsx,
                f"laporan_gudang_{start_a}_{end_a}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("✅ File siap didownload!")
