"""
database.py — SQLite connection + schema initialization
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = "sparepart_warehouse.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database from schema.sql if tables don't exist yet."""
    conn = get_connection()
    with conn:
        if SCHEMA_PATH.exists():
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        else:
            _inline_schema(conn)
    conn.close()


def _inline_schema(conn: sqlite3.Connection):
    """Fallback: create schema inline when schema.sql is missing."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rack TEXT NOT NULL,
            shelf TEXT NOT NULL,
            bin TEXT,
            description TEXT,
            UNIQUE(rack, shelf, bin)
        );
        CREATE TABLE IF NOT EXISTS spare_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            category_id INTEGER REFERENCES categories(id),
            unit_id INTEGER REFERENCES units(id),
            location_id INTEGER REFERENCES locations(id),
            supplier_id INTEGER REFERENCES suppliers(id),
            brand TEXT,
            model TEXT,
            specification TEXT,
            unit_price REAL NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5,
            max_stock INTEGER NOT NULL DEFAULT 100,
            current_stock INTEGER NOT NULL DEFAULT 0,
            reorder_point INTEGER NOT NULL DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stock_in (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL REFERENCES spare_parts(id),
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_cost REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
            supplier_id INTEGER REFERENCES suppliers(id),
            po_number TEXT,
            invoice_number TEXT,
            received_by TEXT,
            notes TEXT,
            transaction_date DATE NOT NULL DEFAULT (DATE('now')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stock_out (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL REFERENCES spare_parts(id),
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_cost REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
            work_order TEXT,
            machine_name TEXT,
            department TEXT,
            requested_by TEXT,
            approved_by TEXT,
            purpose TEXT,
            notes TEXT,
            transaction_date DATE NOT NULL DEFAULT (DATE('now')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stock_opname (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL REFERENCES spare_parts(id),
            system_stock INTEGER NOT NULL,
            physical_stock INTEGER NOT NULL,
            difference INTEGER GENERATED ALWAYS AS (physical_stock - system_stock) STORED,
            reason TEXT,
            conducted_by TEXT,
            opname_date DATE NOT NULL DEFAULT (DATE('now')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_number TEXT NOT NULL UNIQUE,
            machine_name TEXT NOT NULL,
            department TEXT NOT NULL,
            issue_desc TEXT NOT NULL,
            priority TEXT CHECK(priority IN ('Low','Medium','High','Critical')) DEFAULT 'Medium',
            status TEXT CHECK(status IN ('Pending','In Progress','Completed','Cancelled')) DEFAULT 'Pending',
            requested_by TEXT,
            assigned_to TEXT,
            request_date DATE NOT NULL DEFAULT (DATE('now')),
            completion_date DATE,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        INSERT OR IGNORE INTO units(name, symbol) VALUES
            ('Pieces','pcs'),('Set','set'),('Meter','m'),
            ('Liter','L'),('Kilogram','kg'),('Box','box'),
            ('Roll','roll'),('Pair','pair');

        INSERT OR IGNORE INTO categories(name, description) VALUES
            ('Bearing','Bantalan/bearing untuk mesin berputar'),
            ('Belt & Chain','Sabuk dan rantai transmisi daya'),
            ('Electrical','Komponen listrik dan elektronika'),
            ('Hydraulic','Komponen sistem hidrolik'),
            ('Pneumatic','Komponen sistem pneumatik'),
            ('Lubricant','Pelumas, grease, dan oli mesin'),
            ('Seal & Gasket','Seal, gasket, dan packing'),
            ('Fastener','Baut, mur, dan pengikat'),
            ('Filter','Filter oli, udara, dan bahan bakar'),
            ('Pump & Valve','Pompa dan katup'),
            ('Sensor','Sensor dan instrumen pengukuran'),
            ('Safety','Alat keselamatan dan proteksi');

        INSERT OR IGNORE INTO suppliers(name, contact_name, phone, email, city) VALUES
            ('PT Maju Jaya Teknik','Budi Santoso','021-5551234','sales@majujaya.co.id','Jakarta'),
            ('CV Sumber Makmur','Dewi Rahayu','031-5556789','info@sumbermakmur.co.id','Surabaya'),
            ('UD Teknik Pratama','Ahmad Fauzi','022-5559012','order@teknikpratama.com','Bandung'),
            ('PT Indo Bearing Center','Siti Ningsih','021-5553456','bearing@ibc.co.id','Jakarta'),
            ('CV Global Sparepart','Rizky Firmansyah','024-5557890','global@sparepart.co.id','Semarang');

        INSERT OR IGNORE INTO locations(rack, shelf, bin, description) VALUES
            ('A','1','01','Bearing dan Seal'),
            ('A','1','02','Bearing besar'),
            ('A','2','01','Belt dan Chain'),
            ('B','1','01','Electrical komponen'),
            ('B','2','01','Sensor dan instrumen'),
            ('C','1','01','Hydraulic & Pneumatic'),
            ('C','2','01','Filter dan Pompa'),
            ('D','1','01','Lubricant dan Oli'),
            ('D','2','01','Fastener'),
            ('E','1','01','Sparepart Besar');
    """)
