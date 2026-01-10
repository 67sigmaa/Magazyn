import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn", layout="wide")

st.markdown("""
    <style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stButton>button {
        width: 100%; border-radius: 4px; background-color: #1f2937;
        color: #d1d5db; border: 1px solid #374151; text-align: left;
        padding-left: 20px; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #374151; border-color: #00d4ff; color: #00d4ff; }
    h1, h2, h3 { color: #00d4ff !important; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 8px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

def get_connection():
    return sqlite3.connect('magazyn_finalny.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
        cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, ilosc INTEGER, cena REAL, kategoria_id INTEGER,
                        data_aktualizacji TEXT,
                        FOREIGN KEY (kategoria_id) REFERENCES kategorie (id))''')
init_db()

if 'menu' not in st.session_state:
    st.session_state.menu = "Pulpit Manedżerski"

with st.sidebar:
    st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>KONTROLA MAGAZYNU</h2>", unsafe_allow_html=True)
    if st.button("Pulpit Manedżerski"): st.session_state.menu = "Pulpit Manedżerski"
    if st.button("Wyszukiwarka Zasobów"): st.session_state.menu = "Wyszukiwarka Zasobów"
    if st.button("Rejestracja Dostaw"): st.session_state.menu = "Rejestracja Dostaw"
    if st.button("Raport Finansowy"): st.session_state.menu = "Raport Finansowy"
    if st.button("Konfiguracja Kategorii"): st.session_state.menu = "Konfiguracja Kategorii"
    st.divider()
    st.caption("System: Magazyn v2.2")

# --- LOGIKA MODUŁÓW ---

if st.session_state.menu == "Pulpit Manedżerski":
    st.title("Pulpit Manedżerski")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Łączna liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['ilosc'].sum()))
        c3.metric("Wartość inwentarza", f"{(df['ilosc'] * df['cena']).sum():,.2f} PLN")
        st.bar_chart(df.set_index('nazwa')['ilosc'])
    else:
        st.info("Brak towarów.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Wyszukiwarka Zasobów")
    qs = st.text_input("Szukaj towaru...")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if qs: df = df[df['nazwa'].str.contains(qs, case=False)]
    st.dataframe(df, use_container_width=True, hide_index=True)

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Rejestracja Dostaw")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Zdefiniuj kategorie w module Konfiguracja.")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Nazwa artykułu")
            kat = c1.selectbox("Kategoria", kat_df['nazwa'])
            ilosc = c2.number_input("Ilość", min_value=0, step=1)
            cena = c2.number_input("Cena", min_value=0.0, step=0.01)
            if st.form_submit_button("Zapisz"):
                if nazwa:
                    kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    with get_connection() as conn:
                        conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                    (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                    st.success(f"Dodano: {nazwa}")

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, (p.ilosc * p.cena) as suma, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        st.area_chart(df.groupby('kategoria')['suma'].sum())
        st.table(df)

elif st.session_state.menu == "Konfiguracja Kategorii":
    st.title("Konfiguracja Systemu")
    col_in, col_tab = st.columns(2)
    
    with col_in:
        nowa_kat = st.text_input("Nowa kategoria")
        if st.button("Dodaj kategorię"):
            if nowa_kat:
                conn = get_connection()
                # Sprawdzenie czy istnieje, aby uniknąć błędów SQLite przed próbą zapisu
                check = conn.execute("SELECT 1 FROM kategorie WHERE nazwa = ?", (nowa_kat,)).fetchone()
                if check:
                    st.error(f"Kategoria '{nowa_kat}' już znajduje się w systemie.")
                else:
                    conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    conn.commit()
                    st.success(f"Pomyślnie dodano kategorię: {nowa_kat}")
                conn.close()
    
    with col_tab:
        kats = pd.read_sql_query("SELECT nazwa FROM kategorie", get_connection())
        st.table(kats)
