"""
pages/transactions.py — Transaksi Masuk & Keluar Sparepart
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_connection


# ── helpers ────────────────────────────────────────────────
def _parts_options():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT id, part_number||' — '||name AS label, current_stock, unit_price FROM spare_parts WHERE is_active=1 ORDER BY name",
        conn
    )
    conn.close()
    return df


def _suppliers():
    conn = get_connection()
    df = pd.read_sql("SELECT id, name FROM suppliers WHERE is_active=1 ORDER BY name", conn)
    conn.close()
    return df


def _load_transactions(table: str, days: int = 30):
    conn = get_connection()
    if table == "stock_in":
        query = f"""
            SELECT si.id, sp.part_number, sp.name, si.quantity, si.unit_price, si.total_cost,
                   su.name AS supplier, si.po_number, si.invoice_number,
                   si.received_by, si.transaction_date, si.notes
            FROM stock_in si
            JOIN spare_parts sp ON sp.id = si.part_id
            LEFT JOIN suppliers su ON su.id = si.supplier_id
            WHERE si.transaction_date >= DATE('now','-{days} days')
            ORDER BY si.transaction_date DESC, si.id DESC
        """
    else:
        query = f"""
            SELECT so.id, sp.part_number, sp.name, so.quantity, so.unit_price, so.total_cost,
                   so.work_order, so.machine_name, so.department,
                   so.requested_by, so.approved_by, so.purpose,
                   so.transaction_date, so.notes
            FROM stock_out so
            JOIN spare_parts sp ON sp.id = so.part_id
            WHERE so.transaction_date >= DATE('now','-{days} days')
            ORDER BY so.transaction_date DESC, so.id DESC
        """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def _do_stock_in(data: dict):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO stock_in(part_id, quantity, unit_price, supplier_id,
                po_number, invoice_number, received_by, notes, transaction_date)
            VALUES(:part_id,:quantity,:unit_price,:supplier_id,
                :po_number,:invoice_number,:received_by,:notes,:transaction_date)
        """, data)
        conn.execute(
            "UPDATE spare_parts SET current_stock = current_stock + ?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (data["quantity"], data["part_id"])
        )
    conn.close()


def _do_stock_out(data: dict):
    conn = get_connection()
    # check stock
    row = conn.execute("SELECT current_stock, name FROM spare_parts WHERE id=?", (data["part_id"],)).fetchone()
    if row["current_stock"] < data["quantity"]:
        conn.close()
        raise ValueError(f"Stok '{row['name']}' tidak mencukupi. Tersisa: {row['current_stock']}")
    with conn:
        conn.execute("""
            INSERT INTO stock_out(part_id, quantity, unit_price, work_order, machine_name,
                department, requested_by, approved_by, purpose, notes, transaction_date)
            VALUES(:part_id,:quantity,:unit_price,:work_order,:machine_name,
                :department,:requested_by,:approved_by,:purpose,:notes,:transaction_date)
        """, data)
        conn.execute(
            "UPDATE spare_parts SET current_stock = current_stock - ?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (data["quantity"], data["part_id"])
        )
    conn.close()


# ── main page ───────────────────────────────────────────────
def render():
    st.header("📦 Transaksi Sparepart")

    parts_df  = _parts_options()
    supps_df  = _suppliers()

    part_map  = dict(zip(parts_df["label"], parts_df["id"]))
    part_info = {row["id"]: row for _, row in parts_df.iterrows()}
    supp_map  = dict(zip(supps_df["name"], supps_df["id"]))

    tab_in, tab_out, tab_history = st.tabs(
        ["📥 Penerimaan (Stock In)", "📤 Pengeluaran (Stock Out)", "📜 Riwayat Transaksi"]
    )

    # ── STOCK IN ──────────────────────────────────────────
    with tab_in:
        st.subheader("Penerimaan Sparepart")
        with st.form("form_stock_in", clear_on_submit=True):
            part_label = st.selectbox("Sparepart *", ["— pilih —"] + list(part_map.keys()))
            if part_label != "— pilih —":
                pid = part_map[part_label]
                st.info(f"📊 Stok saat ini: **{part_info[pid]['current_stock']}**  |  "
                        f"Harga terakhir: **Rp {part_info[pid]['unit_price']:,.0f}**")

            c1, c2 = st.columns(2)
            qty        = c1.number_input("Jumlah *", min_value=1, step=1)
            unit_price = c2.number_input("Harga Satuan (Rp) *", min_value=0.0, step=500.0)
            st.info(f"💰 Total: **Rp {qty * unit_price:,.0f}**")

            c3, c4 = st.columns(2)
            supplier    = c3.selectbox("Supplier", ["— pilih —"] + list(supp_map.keys()))
            recv_date   = c4.date_input("Tanggal Terima", value=date.today())

            c5, c6 = st.columns(2)
            po_number   = c5.text_input("Nomor PO")
            inv_number  = c6.text_input("Nomor Invoice")
            received_by = st.text_input("Diterima Oleh")
            notes       = st.text_area("Catatan")

            submitted = st.form_submit_button("✅ Simpan Penerimaan", type="primary")
            if submitted:
                if part_label == "— pilih —":
                    st.error("Pilih sparepart terlebih dahulu.")
                else:
                    try:
                        _do_stock_in({
                            "part_id":        part_map[part_label],
                            "quantity":       int(qty),
                            "unit_price":     unit_price,
                            "supplier_id":    supp_map.get(supplier),
                            "po_number":      po_number,
                            "invoice_number": inv_number,
                            "received_by":    received_by,
                            "notes":          notes,
                            "transaction_date": str(recv_date),
                        })
                        st.success(f"✅ Penerimaan **{qty}** unit berhasil dicatat!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Gagal: {ex}")

    # ── STOCK OUT ─────────────────────────────────────────
    with tab_out:
        st.subheader("Pengeluaran / Pemakaian Sparepart")
        with st.form("form_stock_out", clear_on_submit=True):
            part_label_o = st.selectbox("Sparepart *", ["— pilih —"] + list(part_map.keys()))
            if part_label_o != "— pilih —":
                pid_o = part_map[part_label_o]
                stok_o = part_info[pid_o]['current_stock']
                harga_o = part_info[pid_o]['unit_price']
                badge = "🔴" if stok_o <= 5 else ("🟡" if stok_o <= 10 else "🟢")
                st.info(f"{badge} Stok saat ini: **{stok_o}**  |  "
                        f"Harga satuan: **Rp {harga_o:,.0f}**")

            c1, c2 = st.columns(2)
            qty_o       = c1.number_input("Jumlah *", min_value=1, step=1)
            price_o     = c2.number_input("Harga Satuan (Rp)", min_value=0.0, step=500.0,
                                          value=float(part_info[part_map[part_label_o]]["unit_price"])
                                          if part_label_o != "— pilih —" else 0.0)
            st.info(f"💰 Total Biaya: **Rp {qty_o * price_o:,.0f}**")

            c3, c4 = st.columns(2)
            out_date    = c3.date_input("Tanggal Pengeluaran", value=date.today())
            work_order  = c4.text_input("Work Order / No. Kerja")

            c5, c6 = st.columns(2)
            machine     = c5.text_input("Nama Mesin / Peralatan")
            department  = c6.text_input("Departemen")

            c7, c8 = st.columns(2)
            req_by      = c7.text_input("Diminta Oleh")
            appr_by     = c8.text_input("Disetujui Oleh")

            purpose     = st.text_input("Tujuan / Keperluan", placeholder="e.g. Penggantian bearing conveyor")
            notes_o     = st.text_area("Catatan")

            submitted_o = st.form_submit_button("✅ Simpan Pengeluaran", type="primary")
            if submitted_o:
                if part_label_o == "— pilih —":
                    st.error("Pilih sparepart terlebih dahulu.")
                else:
                    try:
                        _do_stock_out({
                            "part_id":        part_map[part_label_o],
                            "quantity":       int(qty_o),
                            "unit_price":     price_o,
                            "work_order":     work_order,
                            "machine_name":   machine,
                            "department":     department,
                            "requested_by":   req_by,
                            "approved_by":    appr_by,
                            "purpose":        purpose,
                            "notes":          notes_o,
                            "transaction_date": str(out_date),
                        })
                        st.success(f"✅ Pengeluaran **{qty_o}** unit berhasil dicatat!")
                        st.rerun()
                    except ValueError as ve:
                        st.error(str(ve))
                    except Exception as ex:
                        st.error(f"Gagal: {ex}")

    # ── HISTORY ───────────────────────────────────────────
    with tab_history:
        st.subheader("Riwayat Transaksi")
        c1, c2 = st.columns(2)
        trx_type = c1.radio("Jenis", ["Stock In (Masuk)", "Stock Out (Keluar)"], horizontal=True)
        days     = c2.selectbox("Periode", [7, 14, 30, 60, 90, 180, 365], index=2, format_func=lambda d: f"{d} hari terakhir")

        table = "stock_in" if "In" in trx_type else "stock_out"
        df_h  = _load_transactions(table, days)

        if df_h.empty:
            st.info("Tidak ada transaksi dalam periode ini.")
        else:
            total = df_h["total_cost"].sum()
            st.metric("Total Nilai Transaksi", f"Rp {total:,.0f}", f"{len(df_h)} transaksi")

            rename = {
                "part_number":"Part #","name":"Nama","quantity":"Qty",
                "unit_price":"Harga Satuan","total_cost":"Total",
                "transaction_date":"Tanggal"
            }
            st.dataframe(
                df_h.rename(columns=rename),
                use_container_width=True, height=400
            )

            # export
            csv = df_h.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv,
                               file_name=f"transaksi_{table}_{days}hari.csv",
                               mime="text/csv")
