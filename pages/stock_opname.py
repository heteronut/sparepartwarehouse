"""
pages/stock_opname.py — Stock Opname / Inventarisasi Fisik
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_connection


def _load_parts():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT id, part_number||' — '||name AS label, current_stock FROM spare_parts WHERE is_active=1 ORDER BY name",
        conn
    )
    conn.close()
    return df


def _save_opname(data):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO stock_opname(part_id, system_stock, physical_stock, reason, conducted_by, opname_date)
            VALUES(:part_id,:system_stock,:physical_stock,:reason,:conducted_by,:opname_date)
        """, data)
        # adjust current_stock to physical count
        conn.execute(
            "UPDATE spare_parts SET current_stock=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (data["physical_stock"], data["part_id"])
        )
    conn.close()


def _load_history(days=90):
    conn = get_connection()
    df = pd.read_sql(f"""
        SELECT so.id, sp.part_number, sp.name,
               so.system_stock, so.physical_stock, so.difference,
               so.reason, so.conducted_by, so.opname_date
        FROM stock_opname so
        JOIN spare_parts sp ON sp.id = so.part_id
        WHERE so.opname_date >= DATE('now','-{days} days')
        ORDER BY so.opname_date DESC, so.id DESC
    """, conn)
    conn.close()
    return df


def render():
    st.header("🗂️ Stock Opname")

    parts_df = _load_parts()
    part_map  = dict(zip(parts_df["label"], parts_df["id"]))
    part_stok = dict(zip(parts_df["label"], parts_df["current_stock"]))

    tab_input, tab_hist = st.tabs(["📝 Input Opname", "📋 Riwayat Opname"])

    with tab_input:
        st.subheader("Input Hasil Stock Opname")
        st.info("Masukkan hasil hitungan fisik stok. Sistem akan menyesuaikan stok otomatis.")

        with st.form("form_opname", clear_on_submit=True):
            part_label = st.selectbox("Sparepart *", ["— pilih —"] + list(part_map.keys()))

            sys_stok = 0
            if part_label != "— pilih —":
                sys_stok = int(part_stok.get(part_label, 0))
                st.info(f"📦 Stok sistem saat ini: **{sys_stok}**")

            c1, c2 = st.columns(2)
            physical_stock = c1.number_input("Stok Fisik (hasil hitung) *", min_value=0, step=1)
            opname_date    = c2.date_input("Tanggal Opname", value=date.today())

            if part_label != "— pilih —":
                diff = physical_stock - sys_stok
                if diff > 0:
                    st.success(f"📈 Selisih: +{diff} (lebih dari sistem)")
                elif diff < 0:
                    st.error(f"📉 Selisih: {diff} (kurang dari sistem)")
                else:
                    st.success("✅ Stok sama dengan sistem.")

            c3, c4 = st.columns(2)
            reason       = c3.text_input("Alasan Selisih (jika ada)")
            conducted_by = c4.text_input("Dilakukan Oleh")

            if st.form_submit_button("💾 Simpan Opname", type="primary"):
                if part_label == "— pilih —":
                    st.error("Pilih sparepart terlebih dahulu.")
                else:
                    try:
                        _save_opname({
                            "part_id":       part_map[part_label],
                            "system_stock":  sys_stok,
                            "physical_stock": int(physical_stock),
                            "reason":        reason,
                            "conducted_by":  conducted_by,
                            "opname_date":   str(opname_date),
                        })
                        st.success("✅ Opname berhasil disimpan dan stok diperbarui!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal: {e}")

    with tab_hist:
        st.subheader("Riwayat Stock Opname")
        days = st.selectbox("Periode", [30, 60, 90, 180, 365], index=2,
                            format_func=lambda d: f"{d} hari terakhir")
        df_h = _load_history(days)
        if df_h.empty:
            st.info("Belum ada riwayat opname.")
        else:
            # highlight rows with difference
            def color_diff(val):
                if val > 0:  return "background-color: #d1fae5"
                if val < 0:  return "background-color: #fee2e2"
                return ""

            st.dataframe(
                df_h.rename(columns={
                    "part_number":"Part #","name":"Nama",
                    "system_stock":"Stok Sistem","physical_stock":"Stok Fisik",
                    "difference":"Selisih","reason":"Alasan",
                    "conducted_by":"Petugas","opname_date":"Tanggal"
                }).style.applymap(color_diff, subset=["Selisih"]),
                use_container_width=True
            )
            csv = df_h.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "stock_opname.csv", "text/csv")
