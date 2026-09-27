"""
pages/maintenance.py — Manajemen Permintaan Perawatan / Work Order
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import get_connection


PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical"]
STATUS_OPTIONS   = ["Pending", "In Progress", "Completed", "Cancelled"]

PRIORITY_ICON = {"Low":"🟢","Medium":"🟡","High":"🟠","Critical":"🔴"}
STATUS_ICON   = {"Pending":"⏳","In Progress":"🔧","Completed":"✅","Cancelled":"❌"}


def _gen_request_number():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM maintenance_requests").fetchone()
    conn.close()
    seq = (row[0] or 0) + 1
    return f"MR-{date.today().strftime('%Y%m')}-{seq:04d}"


def _insert_mr(data):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO maintenance_requests
                (request_number, machine_name, department, issue_desc, priority,
                 status, requested_by, assigned_to, request_date, notes)
            VALUES(:request_number,:machine_name,:department,:issue_desc,:priority,
                   :status,:requested_by,:assigned_to,:request_date,:notes)
        """, data)
    conn.close()


def _update_mr_status(mr_id, status, assigned_to, completion_date, notes):
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE maintenance_requests
            SET status=?, assigned_to=?, completion_date=?, notes=?
            WHERE id=?
        """, (status, assigned_to, str(completion_date) if completion_date else None, notes, mr_id))
    conn.close()


def _load_mrs(status_filter=None, days=90):
    conn = get_connection()
    q = f"""
        SELECT id, request_number, machine_name, department, issue_desc,
               priority, status, requested_by, assigned_to,
               request_date, completion_date, notes
        FROM maintenance_requests
        WHERE request_date >= DATE('now','-{days} days')
    """
    if status_filter and status_filter != "Semua":
        q += f" AND status = '{status_filter}'"
    q += " ORDER BY request_date DESC"
    df = pd.read_sql(q, conn)
    conn.close()
    return df


def render():
    st.header("🔧 Work Order & Maintenance Request")

    tab_list, tab_add, tab_update = st.tabs(
        ["📋 Daftar WO", "➕ Buat WO Baru", "🔄 Update Status"]
    )

    # ── LIST ──────────────────────────────────────────────
    with tab_list:
        c1, c2 = st.columns(2)
        status_f = c1.selectbox("Filter Status", ["Semua"] + STATUS_OPTIONS)
        days_f   = c2.selectbox("Periode", [7, 30, 60, 90, 180], index=2,
                                format_func=lambda d: f"{d} hari terakhir")

        df = _load_mrs(status_f, days_f)

        if df.empty:
            st.info("Tidak ada work order ditemukan.")
        else:
            # summary
            c3, c4, c5, c6 = st.columns(4)
            for status in ["Pending","In Progress","Completed","Cancelled"]:
                cnt = len(df[df["status"] == status])
                icon = STATUS_ICON[status]
            c3.metric(f"{STATUS_ICON['Pending']} Pending",     len(df[df["status"]=="Pending"]))
            c4.metric(f"{STATUS_ICON['In Progress']} Berjalan",len(df[df["status"]=="In Progress"]))
            c5.metric(f"{STATUS_ICON['Completed']} Selesai",   len(df[df["status"]=="Completed"]))
            c6.metric(f"{STATUS_ICON['Cancelled']} Batal",     len(df[df["status"]=="Cancelled"]))

            def style_row(row):
                if row["status"] == "Pending"     and row["priority"] == "Critical":
                    return ["background-color: #fee2e2"] * len(row)
                if row["status"] == "Pending"     and row["priority"] == "High":
                    return ["background-color: #fef3c7"] * len(row)
                if row["status"] == "Completed":
                    return ["background-color: #d1fae5"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.drop(columns=["id"]).rename(columns={
                    "request_number":"No. WO","machine_name":"Mesin","department":"Dept",
                    "issue_desc":"Masalah","priority":"Prioritas","status":"Status",
                    "requested_by":"Diminta","assigned_to":"Teknisi",
                    "request_date":"Tgl Buat","completion_date":"Tgl Selesai","notes":"Catatan"
                }).style.apply(style_row, axis=1),
                use_container_width=True, height=400
            )

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "work_orders.csv", "text/csv")

    # ── ADD ───────────────────────────────────────────────
    with tab_add:
        st.subheader("Buat Work Order Baru")
        auto_no = _gen_request_number()
        st.caption(f"Nomor WO otomatis: **{auto_no}**")

        with st.form("form_add_mr", clear_on_submit=True):
            c1, c2 = st.columns(2)
            machine = c1.text_input("Nama Mesin / Peralatan *")
            dept    = c2.text_input("Departemen *")

            issue   = st.text_area("Deskripsi Masalah / Kerusakan *")

            c3, c4 = st.columns(2)
            priority   = c3.selectbox("Prioritas", PRIORITY_OPTIONS, index=1)
            req_by     = c4.text_input("Diminta Oleh")
            req_date   = c3.date_input("Tanggal", value=date.today())
            assigned   = c4.text_input("Teknisi / Ditugaskan Ke")
            notes      = st.text_area("Catatan Tambahan")

            if st.form_submit_button("✅ Buat WO", type="primary"):
                errors = []
                if not machine: errors.append("Nama mesin wajib diisi.")
                if not dept:    errors.append("Departemen wajib diisi.")
                if not issue:   errors.append("Deskripsi masalah wajib diisi.")
                if errors:
                    for e in errors: st.error(e)
                else:
                    try:
                        _insert_mr({
                            "request_number": auto_no,
                            "machine_name":   machine,
                            "department":     dept,
                            "issue_desc":     issue,
                            "priority":       priority,
                            "status":         "Pending",
                            "requested_by":   req_by,
                            "assigned_to":    assigned,
                            "request_date":   str(req_date),
                            "notes":          notes,
                        })
                        st.success(f"✅ WO **{auto_no}** berhasil dibuat!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal: {e}")

    # ── UPDATE STATUS ─────────────────────────────────────
    with tab_update:
        st.subheader("Update Status Work Order")
        df_u = _load_mrs(days=365)
        if df_u.empty:
            st.info("Tidak ada WO.")
        else:
            open_wo = df_u[df_u["status"].isin(["Pending","In Progress"])]
            if open_wo.empty:
                st.success("Semua WO sudah selesai atau dibatalkan. 🎉")
            else:
                wo_opts = {f"{r['request_number']} | {r['machine_name']} [{r['status']}]": r["id"]
                           for _, r in open_wo.iterrows()}
                sel = st.selectbox("Pilih WO", list(wo_opts.keys()))
                wid = wo_opts[sel]
                wr  = open_wo[open_wo["id"] == wid].iloc[0]

                with st.form("form_update_mr"):
                    c1, c2 = st.columns(2)
                    new_status  = c1.selectbox("Status Baru", STATUS_OPTIONS,
                                               index=STATUS_OPTIONS.index(wr["status"]))
                    assigned_to = c2.text_input("Teknisi", value=wr["assigned_to"] or "")
                    comp_date   = c1.date_input("Tanggal Selesai",
                                                value=date.today() if new_status=="Completed" else None)
                    notes_u     = st.text_area("Catatan Update", value=wr["notes"] or "")

                    if st.form_submit_button("🔄 Update", type="primary"):
                        try:
                            _update_mr_status(wid, new_status, assigned_to,
                                             comp_date if new_status == "Completed" else None,
                                             notes_u)
                            st.success("✅ Status WO berhasil diupdate!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal: {e}")
