# 🔩 SpareWare — Sistem Manajemen Gudang Sparepart

Aplikasi web manajemen gudang sparepart berbasis **Streamlit** + **SQLite** + **Gemini AI**.

## 🚀 Fitur Utama

| Modul | Deskripsi |
|---|---|
| 🏠 **Dashboard** | KPI real-time, grafik aliran biaya, transaksi terbaru |
| 🔩 **Master Sparepart** | CRUD sparepart dengan filter, highlight stok kritis |
| 📦 **Transaksi** | Stock In (penerimaan) & Stock Out (pengeluaran) dengan validasi stok |
| 🚨 **Peringatan Stok** | Alert stok habis / kritis / reorder dengan grafik visual |
| 📊 **Analitik & Biaya** | Tren bulanan, breakdown kategori, top pemakaian, stok idle |
| 🗂️ **Stock Opname** | Input hasil hitung fisik, penyesuaian stok otomatis |
| 🔧 **Maintenance / WO** | Buat & kelola Work Order perawatan mesin |
| 🏭 **Supplier** | Manajemen data supplier dengan histori pembelian |
| 📑 **Laporan & Ekspor** | Export ke CSV / Excel multi-sheet |
| 🤖 **Chatbot AI** | Asisten Gemini yang memahami data inventori Anda |

## 📦 Instalasi

```bash
# Clone / download project
cd sparepartwarehouse

# Install dependencies
pip install -r requirements.txt

# Jalankan aplikasi
streamlit run app.py
```

## ☁️ Deploy ke Streamlit Cloud

1. Push repository ke GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Klik **New app** → pilih repo ini
4. Main file: `app.py`
5. Klik **Deploy**

> **Catatan:** Database SQLite akan di-reset setiap kali app di-restart di Streamlit Cloud.  
> Untuk persistensi, gunakan [Streamlit Community Cloud Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) dengan database cloud (PostgreSQL, Supabase, dll).

## 🤖 Konfigurasi Gemini AI

1. Dapatkan API key gratis di [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Buka halaman **Chatbot AI** di aplikasi
3. Masukkan API key di kolom sidebar

## 📁 Struktur Proyek

```
sparepartwarehouse/
├── app.py                   # Entry point Streamlit
├── database.py              # Koneksi & inisialisasi SQLite
├── schema.sql               # Schema database lengkap
├── requirements.txt         # Dependencies Python
├── .streamlit/
│   └── config.toml          # Konfigurasi tema Streamlit
└── pages/
    ├── dashboard.py         # Halaman dashboard
    ├── spare_parts.py       # Master data sparepart
    ├── transactions.py      # Transaksi masuk/keluar
    ├── stock_alert.py       # Peringatan stok
    ├── analytics.py         # Analitik & laporan biaya
    ├── stock_opname.py      # Stock opname
    ├── maintenance.py       # Work order & maintenance
    ├── suppliers.py         # Manajemen supplier
    ├── reports.py           # Laporan & ekspor
    └── chatbot.py           # Chatbot Gemini AI
```

## 🗃️ Schema Database

- **spare_parts** — Master data sparepart (part number, nama, stok, harga, dll)
- **categories** — Kategori sparepart (bearing, electrical, dll)
- **suppliers** — Data vendor/supplier
- **units** — Satuan (pcs, set, liter, dll)
- **locations** — Lokasi rak penyimpanan
- **stock_in** — Transaksi penerimaan sparepart
- **stock_out** — Transaksi pengeluaran/pemakaian
- **stock_opname** — Hasil inventarisasi fisik
- **maintenance_requests** — Work order perawatan
- **chat_history** — Riwayat percakapan AI

## 📄 License

MIT License
