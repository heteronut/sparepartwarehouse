"""
pages/spare_parts.py — Master Data Sparepart (CRUD)
"""
import streamlit as st
import pandas as pd
from database import get_connection


# ── helpers ────────────────────────────────────────────────
def _load_lookups():
    conn = get_connection()
    cats = pd.read_sql("SELECT id, name FROM categories ORDER BY name", conn)
    units = pd.read_sql("SELECT id, name, symbol FROM units ORDER BY name", conn)
    locs = pd.read_sql(
        "SELECT id, rack||'-'||shelf||'-'||COALESCE(bin,'') AS label FROM locations ORDER BY rack,shelf,bin",
        conn
    )
    supps = pd.read_sql("SELECT id, name FROM suppliers WHERE is_active=1 ORDER BY name", conn)
    conn.close()
    return cats, units, locs, supps


def _load_parts(search="", active_only=True):
    conn = get_connection()
    query = """
        SELECT
            sp.id, sp.part_number, sp.name, sp.brand, sp.model,
            c.name  AS category,
            u.symbol AS unit,
            l.rack||'-'||l.shelf||'-'||COALESCE(l.bin,'') AS location,
            s.name  AS supplier,
            sp.unit_price, sp.current_stock, sp.min_stock,
            sp.max_stock, sp.reorder_point, sp.is_active,
            sp.specification
        FROM spare_parts sp
        LEFT JOIN categories c  ON c.id = sp.category_id
        LEFT JOIN units      u  ON u.id = sp.unit_id
        LEFT JOIN locations  l  ON l.id = sp.location_id
        LEFT JOIN suppliers  s  ON s.id = sp.supplier_id
        WHERE 1=1
    """
    params = []
    if active_only:
        query += " AND sp.is_active = 1"
    if search:
        query += " AND (sp.name LIKE ? OR sp.part_number LIKE ? OR sp.brand LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    query += " ORDER BY sp.name"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def _insert_part(data: dict):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO spare_parts
                (part_number, name, description, category_id, unit_id, location_id,
                 supplier_id, brand, model, specification, unit_price,
                 min_stock, max_stock, current_stock, reorder_point)
            VALUES
                (:part_number,:name,:description,:category_id,:unit_id,:location_id,
                 :supplier_id,:brand,:model,:specification,:unit_price,
                 :min_stock,:max_stock,:current_stock,:reorder_point)
        """, data)
    conn.close()


def _update_part(part_id: int, data: dict):
    conn = get_connection()
    data["id"] = part_id
    with conn:
        conn.execute("""
            UPDATE spare_parts SET
                part_number=:part_number, name=:name, description=:description,
                category_id=:category_id, unit_id=:unit_id, location_id=:location_id,
                supplier_id=:supplier_id, brand=:brand, model=:model,
                specification=:specification, unit_price=:unit_price,
                min_stock=:min_stock, max_stock=:max_stock,
                reorder_point=:reorder_point,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=:id
        """, data)
    conn.close()


def _deactivate_part(part_id: int):
    conn = get_connection()
    with conn:
        conn.execute("UPDATE spare_parts SET is_active=0 WHERE id=?", (part_id,))
    conn.close()


def _restore_part(part_id: int):
    conn = get_connection()
    with conn:
        conn.execute("UPDATE spare_parts SET is_active=1 WHERE id=?", (part_id,))
    conn.close()


# ── main page ───────────────────────────────────────────────
def render():
    st.header("🔩 Master Data Sparepart")

    cats, units, locs, supps = _load_lookups()

    cat_map   = dict(zip(cats["name"],   cats["id"]))
    unit_map  = dict(zip(units["name"],  units["id"]))
    loc_map   = dict(zip(locs["label"],  locs["id"]))
    supp_map  = dict(zip(supps["name"],  supps["id"]))

    tab_list, tab_add, tab_edit = st.tabs(["📋 Daftar Sparepart", "➕ Tambah Baru", "✏️ Edit / Nonaktifkan"])

    # ── TAB LIST ──────────────────────────────────────────
    with tab_list:
        col1, col2 = st.columns([3, 1])
        search = col1.text_input("🔍 Cari (nama / part number / brand)", placeholder="ketik untuk mencari...")
        show_inactive = col2.checkbox("Tampilkan nonaktif")

        df = _load_parts(search=search, active_only=not show_inactive)

        if df.empty:
            st.info("Belum ada data sparepart.")
        else:
            st.caption(f"Menampilkan **{len(df)}** sparepart")
            # colour low-stock rows
            def highlight_stock(row):
                if row["current_stock"] <= row["min_stock"]:
                    return ["background-color: #ffe0e0"] * len(row)
                elif row["current_stock"] <= row["reorder_point"]:
                    return ["background-color: #fff3cd"] * len(row)
                return [""] * len(row)

            display_cols = ["part_number","name","brand","category","unit",
                            "location","current_stock","min_stock","reorder_point",
                            "unit_price","supplier"]
            styled = df[display_cols].rename(columns={
                "part_number":"Part #","name":"Nama","brand":"Brand",
                "category":"Kategori","unit":"Satuan","location":"Lokasi",
                "current_stock":"Stok","min_stock":"Min","reorder_point":"Reorder",
                "unit_price":"Harga Satuan","supplier":"Supplier"
            }).style.apply(
                lambda row: highlight_stock(df.loc[row.name]), axis=1
            ).format({"Harga Satuan": "Rp {:,.0f}"})
            st.dataframe(styled, use_container_width=True, height=420)
            st.caption("🔴 Merah = stok di bawah minimum &nbsp;|&nbsp; 🟡 Kuning = perlu reorder")

    # ── TAB ADD ───────────────────────────────────────────
    with tab_add:
        st.subheader("Tambah Sparepart Baru")
        with st.form("form_add_part", clear_on_submit=True):
            c1, c2 = st.columns(2)
            part_number   = c1.text_input("Part Number *", placeholder="e.g. BRG-6205-2RS")
            name          = c2.text_input("Nama Sparepart *")
            brand         = c1.text_input("Brand / Merk")
            model         = c2.text_input("Model / Tipe")
            description   = st.text_area("Deskripsi")
            specification = st.text_area("Spesifikasi Teknis")

            c3, c4 = st.columns(2)
            category = c3.selectbox("Kategori", options=["— pilih —"] + list(cat_map.keys()))
            unit     = c4.selectbox("Satuan", options=["— pilih —"] + list(unit_map.keys()))

            c5, c6 = st.columns(2)
            location = c5.selectbox("Lokasi Penyimpanan", options=["— pilih —"] + list(loc_map.keys()))
            supplier = c6.selectbox("Supplier Utama", options=["— pilih —"] + list(supp_map.keys()))

            c7, c8, c9, c10, c11 = st.columns(5)
            unit_price    = c7.number_input("Harga Satuan (Rp)", min_value=0.0, step=1000.0)
            current_stock = c8.number_input("Stok Awal", min_value=0, step=1)
            min_stock     = c9.number_input("Stok Minimum", min_value=0, step=1, value=5)
            max_stock     = c10.number_input("Stok Maksimum", min_value=0, step=1, value=100)
            reorder_point = c11.number_input("Reorder Point", min_value=0, step=1, value=10)

            submitted = st.form_submit_button("💾 Simpan", type="primary")
            if submitted:
                errors = []
                if not part_number: errors.append("Part Number wajib diisi.")
                if not name:        errors.append("Nama Sparepart wajib diisi.")
                if errors:
                    for e in errors: st.error(e)
                else:
                    try:
                        _insert_part({
                            "part_number":   part_number,
                            "name":          name,
                            "description":   description,
                            "category_id":   cat_map.get(category),
                            "unit_id":       unit_map.get(unit),
                            "location_id":   loc_map.get(location),
                            "supplier_id":   supp_map.get(supplier),
                            "brand":         brand,
                            "model":         model,
                            "specification": specification,
                            "unit_price":    unit_price,
                            "min_stock":     min_stock,
                            "max_stock":     max_stock,
                            "current_stock": current_stock,
                            "reorder_point": reorder_point,
                        })
                        st.success(f"✅ Sparepart **{name}** berhasil ditambahkan!")
                    except Exception as ex:
                        st.error(f"Gagal menyimpan: {ex}")

    # ── TAB EDIT ──────────────────────────────────────────
    with tab_edit:
        st.subheader("Edit atau Nonaktifkan Sparepart")
        df_all = _load_parts(active_only=False)
        if df_all.empty:
            st.info("Belum ada data.")
        else:
            part_options = {f"{r['part_number']} — {r['name']}": r["id"] for _, r in df_all.iterrows()}
            selected_label = st.selectbox("Pilih Sparepart", list(part_options.keys()))
            selected_id = part_options[selected_label]
            row = df_all[df_all["id"] == selected_id].iloc[0]

            with st.form("form_edit_part"):
                c1, c2 = st.columns(2)
                e_pn    = c1.text_input("Part Number", value=row["part_number"])
                e_name  = c2.text_input("Nama Sparepart", value=row["name"] if row["name"] else "")
                e_brand = c1.text_input("Brand", value=row["brand"] if row["brand"] else "")
                e_model = c2.text_input("Model", value=row["model"] if row["model"] else "")

                cat_list  = ["— pilih —"] + list(cat_map.keys())
                unit_list = ["— pilih —"] + list(unit_map.keys())
                loc_list  = ["— pilih —"] + list(loc_map.keys())
                sup_list  = ["— pilih —"] + list(supp_map.keys())

                # reverse lookup current values
                rev_cat  = {v: k for k, v in cat_map.items()}
                rev_unit = {v: k for k, v in unit_map.items()}

                # get category/unit/location/supplier ids from names stored in row
                conn = get_connection()
                cur_row = conn.execute("SELECT * FROM spare_parts WHERE id=?", (selected_id,)).fetchone()
                conn.close()

                c3, c4 = st.columns(2)
                e_cat  = c3.selectbox("Kategori", cat_list,
                    index=cat_list.index(rev_cat.get(cur_row["category_id"],"— pilih —"))
                    if cur_row["category_id"] in rev_cat else 0)
                e_unit = c4.selectbox("Satuan", unit_list,
                    index=unit_list.index(rev_unit.get(cur_row["unit_id"],"— pilih —"))
                    if cur_row["unit_id"] in rev_unit else 0)

                c7, c8, c9, c10 = st.columns(4)
                e_price  = c7.number_input("Harga Satuan (Rp)", value=float(cur_row["unit_price"]), step=1000.0)
                e_min    = c8.number_input("Stok Min",     value=int(cur_row["min_stock"]),     step=1)
                e_max    = c9.number_input("Stok Max",     value=int(cur_row["max_stock"]),     step=1)
                e_reord  = c10.number_input("Reorder Point", value=int(cur_row["reorder_point"]), step=1)
                e_spec   = st.text_area("Spesifikasi", value=cur_row["specification"] if cur_row["specification"] else "")
                e_desc   = st.text_area("Deskripsi",  value=cur_row["description"] if cur_row["description"] else "")

                col_save, col_deact = st.columns(2)
                save_btn   = col_save.form_submit_button("💾 Update", type="primary")
                deact_btn  = col_deact.form_submit_button("🚫 Nonaktifkan" if row["is_active"] else "✅ Aktifkan")

                if save_btn:
                    try:
                        _update_part(selected_id, {
                            "part_number":   e_pn,
                            "name":          e_name,
                            "description":   e_desc,
                            "category_id":   cat_map.get(e_cat),
                            "unit_id":       unit_map.get(e_unit),
                            "location_id":   cur_row["location_id"],
                            "supplier_id":   cur_row["supplier_id"],
                            "brand":         e_brand,
                            "model":         e_model,
                            "specification": e_spec,
                            "unit_price":    e_price,
                            "min_stock":     e_min,
                            "max_stock":     e_max,
                            "reorder_point": e_reord,
                        })
                        st.success("✅ Data berhasil diupdate!")
                    except Exception as ex:
                        st.error(f"Gagal: {ex}")

                if deact_btn:
                    if row["is_active"]:
                        _deactivate_part(selected_id)
                        st.warning("Sparepart dinonaktifkan.")
                    else:
                        _restore_part(selected_id)
                        st.success("Sparepart diaktifkan kembali.")
                    st.rerun()
