"""
app.py — Main entry point for Spare Part Warehouse Management System
Run with: streamlit run app.py
"""
import streamlit as st
from database import init_db
import pages.dashboard    as _pg_dashboard
import pages.spare_parts  as _pg_spare_parts
import pages.transactions as _pg_transactions
import pages.stock_alert  as _pg_stock_alert
import pages.analytics    as _pg_analytics
import pages.stock_opname as _pg_stock_opname
import pages.maintenance  as _pg_maintenance
import pages.suppliers    as _pg_suppliers
import pages.reports      as _pg_reports
import pages.chatbot      as _pg_chatbot

# ── page config ────────────────────────────────────────────
st.set_page_config(
    page_title="Gudang Sparepart",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: #334155;
        border: 1px solid #475569;
        color: #e2e8f0 !important;
        width: 100%;
        text-align: left;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 2px 0;
        font-size: 14px;
        transition: background 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
    /* Active page button */
    .nav-active button {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
        font-weight: 600 !important;
    }
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
    }
    /* Header */
    h1, h2, h3 { color: #1e293b; }
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
    }
    /* Hide default Streamlit footer */
    footer { visibility: hidden; }
    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Init DB ────────────────────────────────────────────────
init_db()

# ── Navigation ─────────────────────────────────────────────
PAGES = {
    "🏠 Dashboard":         "dashboard",
    "🔩 Sparepart":         "spare_parts",
    "📦 Transaksi":         "transactions",
    "🚨 Peringatan Stok":   "stock_alert",
    "📊 Analitik":          "analytics",
    "🗂️ Stock Opname":      "stock_opname",
    "🔧 Maintenance / WO":  "maintenance",
    "🏭 Supplier":          "suppliers",
    "📑 Laporan & Ekspor":  "reports",
    "🤖 Chatbot AI":        "chatbot",
}

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding: 16px 0 8px 0;'>
            <span style='font-size:36px;'>🔩</span><br>
            <span style='font-size:18px; font-weight:700; color:#e2e8f0;'>SpareWare</span><br>
            <span style='font-size:11px; color:#94a3b8;'>Manajemen Gudang Sparepart</span>
        </div>
        <hr style='border-color:#334155; margin:8px 0;'>
    """, unsafe_allow_html=True)

    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "dashboard"

    for label, key in PAGES.items():
        is_active = st.session_state["active_page"] == key
        btn_container = st.container()
        if is_active:
            btn_container.markdown('<div class="nav-active">', unsafe_allow_html=True)
        if btn_container.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state["active_page"] = key
            st.rerun()
        if is_active:
            btn_container.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        <hr style='border-color:#334155; margin: 12px 0;'>
        <div style='text-align:center; font-size:11px; color:#64748b; padding-bottom:8px;'>
            SpareWare v1.0 · SQLite + Gemini AI<br>
            © 2024 Spare Part Warehouse
        </div>
    """, unsafe_allow_html=True)

# ── Route to page ───────────────────────────────────────────
_PAGE_MAP = {
    "dashboard":    _pg_dashboard,
    "spare_parts":  _pg_spare_parts,
    "transactions": _pg_transactions,
    "stock_alert":  _pg_stock_alert,
    "analytics":    _pg_analytics,
    "stock_opname": _pg_stock_opname,
    "maintenance":  _pg_maintenance,
    "suppliers":    _pg_suppliers,
    "reports":      _pg_reports,
    "chatbot":      _pg_chatbot,
}

page_key = st.session_state.get("active_page", "dashboard")
page_module = _PAGE_MAP.get(page_key, _pg_dashboard)

try:
    page_module.render()
except Exception as e:
    st.error(f"❌ Error memuat halaman: {e}")
    st.exception(e)
