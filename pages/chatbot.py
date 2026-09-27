"""
pages/chatbot.py — Gemini AI Chatbot Integration
"""
import streamlit as st
import pandas as pd
from database import get_connection


# ── context builder ─────────────────────────────────────────
def _build_context() -> str:
    conn = get_connection()
    total_parts   = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1").fetchone()[0]
    total_value   = conn.execute("SELECT COALESCE(SUM(current_stock*unit_price),0) FROM spare_parts WHERE is_active=1").fetchone()[0]
    low_stock     = conn.execute("SELECT COUNT(*) FROM spare_parts WHERE is_active=1 AND current_stock<=min_stock").fetchone()[0]
    total_in      = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_in").fetchone()[0]
    total_out     = conn.execute("SELECT COALESCE(SUM(total_cost),0) FROM stock_out").fetchone()[0]
    open_wo       = conn.execute("SELECT COUNT(*) FROM maintenance_requests WHERE status IN ('Pending','In Progress')").fetchone()[0]

    cats = pd.read_sql("""
        SELECT c.name AS kategori, COUNT(sp.id) AS jumlah,
               COALESCE(SUM(sp.current_stock*sp.unit_price),0) AS nilai
        FROM spare_parts sp JOIN categories c ON c.id=sp.category_id
        WHERE sp.is_active=1 GROUP BY c.name ORDER BY nilai DESC LIMIT 5
    """, conn)

    top_out = pd.read_sql("""
        SELECT sp.name, SUM(so.quantity) AS qty, SUM(so.total_cost) AS biaya
        FROM stock_out so JOIN spare_parts sp ON sp.id=so.part_id
        WHERE so.transaction_date >= DATE('now','-30 days')
        GROUP BY sp.id ORDER BY biaya DESC LIMIT 5
    """, conn)
    conn.close()

    ctx = f"""
Kamu adalah asisten AI gudang sparepart yang cerdas dan membantu.
Berikut adalah data terkini dari sistem gudang:

📦 INVENTORI:
- Total sparepart aktif: {total_parts}
- Nilai total inventori: Rp {total_value:,.0f}
- Part dengan stok kritis/habis: {low_stock}

💰 KEUANGAN (ALL TIME):
- Total pembelian (stock in): Rp {total_in:,.0f}
- Total pemakaian (stock out): Rp {total_out:,.0f}
- Net: Rp {total_in - total_out:,.0f}

🔧 MAINTENANCE:
- Work order terbuka: {open_wo}

🏷️ TOP KATEGORI (berdasarkan nilai stok):
{cats.to_string(index=False) if not cats.empty else 'Tidak ada data'}

📤 TOP PENGELUARAN 30 HARI TERAKHIR:
{top_out.to_string(index=False) if not top_out.empty else 'Tidak ada data'}

Jawablah pertanyaan pengguna secara sopan, profesional, dan dalam Bahasa Indonesia.
Berikan saran dan analisis yang relevan berdasarkan data di atas.
"""
    return ctx


def _save_chat(role: str, message: str):
    conn = get_connection()
    with conn:
        conn.execute("INSERT INTO chat_history(role, message) VALUES(?,?)", (role, message))
    conn.close()


def _load_chat_history():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT role, message FROM chat_history ORDER BY id DESC LIMIT 50", conn
    )
    conn.close()
    return df.iloc[::-1]  # reverse to chronological


def _clear_chat_history():
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM chat_history")
    conn.close()


# ── Gemini call ─────────────────────────────────────────────
def _call_gemini(api_key: str, messages: list, system_prompt: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt
        )
        # build history for multi-turn
        history = []
        for m in messages[:-1]:   # all except the latest user message
            history.append({
                "role": "user" if m["role"] == "user" else "model",
                "parts": [m["content"]]
            })
        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        return response.text
    except ImportError:
        return "⚠️ Library `google-generativeai` belum terinstall. Jalankan: `pip install google-generativeai`"
    except Exception as e:
        return f"❌ Error Gemini API: {str(e)}"


# ── main page ───────────────────────────────────────────────
def render():
    st.header("🤖 Chatbot AI — Asisten Gudang Sparepart")

    # ── API Key sidebar config ─────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("🔑 Konfigurasi Gemini API")
        api_key = st.text_input(
            "Masukkan Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Dapatkan API key gratis di https://aistudio.google.com/app/apikey",
            key="gemini_api_key"
        )
        if api_key:
            st.success("API Key tersimpan ✅")
        else:
            st.warning("Masukkan API key untuk mengaktifkan chatbot")

        if st.button("🗑️ Hapus Riwayat Chat"):
            _clear_chat_history()
            if "chat_messages" in st.session_state:
                del st.session_state["chat_messages"]
            st.rerun()

    # ── initialize session chat ────────────────────────────
    if "chat_messages" not in st.session_state:
        # Load from DB
        df_hist = _load_chat_history()
        st.session_state["chat_messages"] = [
            {"role": r["role"], "content": r["message"]}
            for _, r in df_hist.iterrows()
        ] if not df_hist.empty else []

    # ── info banner ────────────────────────────────────────
    st.markdown("""
    > 💡 **Asisten AI ini mengetahui data inventori Anda secara real-time.**  
    > Tanyakan tentang stok, biaya, reorder, analisis, atau saran pengelolaan gudang.
    """)

    if not api_key:
        st.info("🔑 Masukkan Gemini API Key di sidebar untuk memulai percakapan.")

    # ── suggestion prompts ─────────────────────────────────
    st.subheader("💬 Pertanyaan Cepat")
    suggestions = [
        "Bagaimana kondisi inventori gudang saat ini?",
        "Sparepart apa yang perlu segera direorder?",
        "Bagaimana tren biaya sparepart bulan ini?",
        "Berikan rekomendasi untuk optimasi inventori.",
        "Sparepart apa yang paling sering digunakan?",
        "Apakah ada potensi penghematan biaya yang bisa dilakukan?",
    ]
    cols = st.columns(3)
    for i, sug in enumerate(suggestions):
        if cols[i % 3].button(sug, key=f"sug_{i}", use_container_width=True):
            if api_key:
                st.session_state["pending_prompt"] = sug
            else:
                st.warning("Masukkan API key terlebih dahulu.")

    st.divider()

    # ── chat display ───────────────────────────────────────
    chat_container = st.container(height=450)
    with chat_container:
        if not st.session_state["chat_messages"]:
            st.markdown("*Belum ada percakapan. Mulai bertanya!* 👇")
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"],
                                 avatar="🧑" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])

    # ── input ──────────────────────────────────────────────
    prompt = st.chat_input("Tanyakan sesuatu tentang gudang sparepart Anda...",
                           disabled=not api_key)

    # handle suggestion click
    if "pending_prompt" in st.session_state and st.session_state["pending_prompt"]:
        prompt = st.session_state.pop("pending_prompt")

    if prompt and api_key:
        # add user message
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        _save_chat("user", prompt)

        with st.spinner("🤖 AI sedang berpikir..."):
            system_ctx = _build_context()
            response = _call_gemini(
                api_key=api_key,
                messages=st.session_state["chat_messages"],
                system_prompt=system_ctx
            )

        st.session_state["chat_messages"].append({"role": "assistant", "content": response})
        _save_chat("assistant", response)
        st.rerun()

    elif prompt and not api_key:
        st.error("Masukkan Gemini API Key di sidebar terlebih dahulu.")
