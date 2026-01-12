import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn Pro", layout="wide")

st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0d1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stButton>button {
        width: 100%; border-radius: 6px; background-color: #21262d;
        color: #f0f6fc; border: 1px solid #8b949e; text-align: left;
        padding-left: 20px; font-weight: 500;
    }
    .stButton>button:hover { border-color: #58a6ff; color: #58a6ff; }
    h1, h2, h3 { color: #58a6ff !important; }
    div[data-testid="stMetric"] { background-color: #30363d; padding: 20px; border-radius: 10px; border: 1px solid #8b949e; }
    .alert-box { background-color: #442726; border: 2px solid #f85149; padding: 15px; border-radius: 8px; color: #ff7b72; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGOWANIE ---
if 'auth' not in st.session_state: st.session_state.auth = False

def login():
    st.title("Autoryzacja")
    user = st.text_input("Użytkownik")
    password = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if user == "admin" and password == "123":
            st.session_state.auth = True
            st.rerun()

if not st.session_state.auth:
    login()
    st.stop()

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_finalny.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
        conn.execute('PRAGMA foreign_keys = ON;')
        conn.execute('CREATE TABLE IF NOT EXISTS kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
        conn.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, ilosc INTEGER, cena REAL, kategoria_id INTEGER,
                        data_aktualizacji TEXT,
                        FOREIGN KEY (kategoria_id) REFERENCES kategorie (id))''')
init_db()

# --- NAWIGACJA ---
if 'menu' not in st.session_state: st.session_state.menu = "Pulpit"

with st.sidebar:
    st.markdown("### PANEL STEROWANIA")
    if st.button("📊 Pulpit Manedżerski"): st.session_state.menu = "Pulpit"
    if st.button("🔍 Przegląd Zasobów"): st.session_state.menu = "Szukaj"
    if st.button("📥 Przyjęcie Towaru"): st.session_state.menu = "Dostawa"
    if st.button("📦 Operacje Magazynowe"): st.session_state.menu = "Operacje"
    if st.button("⚙️ Kategorie"): st.session_state.menu = "Kategorie"
    st.divider()
    if st.button("🔴 Wyloguj"):
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA MODUŁÓW ---

if st.session_state.menu == "Pulpit":
    st.title("Pulpit Manedżerski")
    df = pd.read_sql_query('SELECT p.nazwa, p.ilosc, p.cena FROM produkty p', get_connection())
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("SKU", len(df))
        c2.metric("Suma sztuk", int(df['ilosc'].sum()))
        c3.metric("Wycena", f"{(df['ilosc'] * df['cena']).sum():,.2f} PLN")
        
        low = df[df['ilosc'] < 5]
        if not low.empty:
            st.markdown(f'<div class="alert-box">⚠️ NISKI STAN: {len(low)} pozycji!</div>', unsafe_allow_html=True)
            st.table(low)
    else: st.info("Baza jest pusta.")

elif st.session_state.menu == "Szukaj":
    st.title("Przegląd Zasobów")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    st.dataframe(df, use_container_width=True)

elif st.session_state.menu == "Dostawa":
    st.title("📥 Przyjęcie (Dostawa)")
    kats = pd.read_sql_query("SELECT *
