"""
pages/suppliers.py — Manajemen Supplier
"""
import streamlit as st
import pandas as pd
from database import get_connection


def _load_suppliers():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT s.id, s.name, s.contact_name, s.phone, s.email,
               s.city, s.address,
               s.is_active,
               COUNT(DISTINCT sp.id) AS jumlah_part,
               COALESCE(SUM(si.total_cost),0) AS total_pembelian
        FROM suppliers s
        LEFT JOIN spare_parts sp ON sp.supplier_id = s.id AND sp.is_active=1
        LEFT JOIN stock_in si    ON si.supplier_id = s.id
        GROUP BY s.id
        ORDER BY s.name
    """, conn)
    conn.close()
    return df


def _insert_supplier(data):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO suppliers(name, contact_name, phone, email, address, city)
            VALUES(:name,:contact_name,:phone,:email,:address,:city)
        """, data)
    conn.close()


def _update_supplier(sid, data):
    conn = get_connection()
    data["id"] = sid
    with conn:
        conn.execute("""
            UPDATE suppliers SET name=:name, contact_name=:contact_name, phone=:phone,
                email=:email, address=:address, city=:city WHERE id=:id
        """, data)
    conn.close()


def _toggle_supplier(sid, active):
    conn = get_connection()
    with conn:
        conn.execute("UPDATE suppliers SET is_active=? WHERE id=?", (active, sid))
    conn.close()


def render():
    st.header("🏭 Manajemen Supplier")

    tab_list, tab_add, tab_edit = st.tabs(["📋 Daftar Supplier", "➕ Tambah Baru", "✏️ Edit"])

    # ── LIST ──────────────────────────────────────────────
    with tab_list:
        df = _load_suppliers()
        if df.empty:
            st.info("Belum ada data supplier.")
        else:
            st.caption(f"Total **{len(df)}** supplier")
            show = df.rename(columns={
                "name":"Nama","contact_name":"Kontak","phone":"Telepon",
                "email":"Email","city":"Kota","jumlah_part":"Part Terdaftar",
                "total_pembelian":"Total Pembelian (Rp)","is_active":"Aktif"
            })
            st.dataframe(show.drop(columns=["id","address"]), use_container_width=True)

    # ── ADD ───────────────────────────────────────────────
    with tab_add:
        st.subheader("Tambah Supplier Baru")
        with st.form("form_add_sup", clear_on_submit=True):
            c1, c2 = st.columns(2)
            s_name    = c1.text_input("Nama Supplier *")
            s_contact = c2.text_input("Nama Kontak")
            c3, c4 = st.columns(2)
            s_phone = c3.text_input("Telepon")
            s_email = c4.text_input("Email")
            c5, c6 = st.columns(2)
            s_city  = c5.text_input("Kota")
            s_addr  = c6.text_input("Alamat")

            if st.form_submit_button("💾 Simpan", type="primary"):
                if not s_name:
                    st.error("Nama supplier wajib diisi.")
                else:
                    try:
                        _insert_supplier({
                            "name": s_name, "contact_name": s_contact,
                            "phone": s_phone, "email": s_email,
                            "address": s_addr, "city": s_city
                        })
                        st.success(f"✅ Supplier **{s_name}** berhasil ditambahkan!")
                    except Exception as e:
                        st.error(f"Gagal: {e}")

    # ── EDIT ──────────────────────────────────────────────
    with tab_edit:
        df_e = _load_suppliers()
        if df_e.empty:
            st.info("Belum ada data.")
        else:
            sup_opts = {f"{r['name']} ({r['city']})": r["id"] for _, r in df_e.iterrows()}
            sel = st.selectbox("Pilih Supplier", list(sup_opts.keys()))
            sid = sup_opts[sel]
            row = df_e[df_e["id"] == sid].iloc[0]

            with st.form("form_edit_sup"):
                c1, c2 = st.columns(2)
                e_name    = c1.text_input("Nama",       value=row["name"])
                e_contact = c2.text_input("Kontak",     value=row["contact_name"] or "")
                c3, c4 = st.columns(2)
                e_phone   = c3.text_input("Telepon",    value=row["phone"] or "")
                e_email   = c4.text_input("Email",      value=row["email"] or "")
                c5, c6 = st.columns(2)
                e_city    = c5.text_input("Kota",       value=row["city"] or "")
                e_addr    = c6.text_input("Alamat",     value=row["address"] or "")

                col_s, col_t = st.columns(2)
                save_s   = col_s.form_submit_button("💾 Update", type="primary")
                toggle_s = col_t.form_submit_button(
                    "🚫 Nonaktifkan" if row["is_active"] else "✅ Aktifkan"
                )

                if save_s:
                    try:
                        _update_supplier(sid, {
                            "name": e_name, "contact_name": e_contact,
                            "phone": e_phone, "email": e_email,
                            "address": e_addr, "city": e_city
                        })
                        st.success("✅ Data supplier berhasil diupdate!")
                    except Exception as e:
                        st.error(f"Gagal: {e}")

                if toggle_s:
                    _toggle_supplier(sid, 0 if row["is_active"] else 1)
                    st.rerun()
