"""
app.py — Main entry point for Spare Part Warehouse Management System
Run with: streamlit run app.py
"""
import streamlit as st
from database import init_db

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
page_key = st.session_state.get("active_page", "dashboard")

try:
    if page_key == "dashboard":
        from pages.dashboard    import render
    elif page_key == "spare_parts":
        from pages.spare_parts  import render
    elif page_key == "transactions":
        from pages.transactions import render
    elif page_key == "stock_alert":
        from pages.stock_alert  import render
    elif page_key == "analytics":
        from pages.analytics    import render
    elif page_key == "stock_opname":
        from pages.stock_opname import render
    elif page_key == "maintenance":
        from pages.maintenance  import render
    elif page_key == "suppliers":
        from pages.suppliers    import render
    elif page_key == "reports":
        from pages.reports      import render
    elif page_key == "chatbot":
        from pages.chatbot      import render
    else:
        from pages.dashboard    import render

    render()
except Exception as e:
    st.error(f"❌ Error memuat halaman: {e}")
    st.exception(e)
