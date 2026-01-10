import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn Strategiczny", layout="wide")

# Zaawansowana stylizacja Dark Industrial + Ukrycie nagłówka
st.markdown("""
    <style>
    /* Ukrywanie białego paska na górze i menu */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    [data-testid="stSidebar"] { 
        background-color: #161b22; 
        min-width: 300px; 
    }
    
    /* Stylizacja przycisków menu bocznego */
    .stButton>button {
        width: 100%;
        border-radius: 4px;
        background-color: #1f2937;
        color: #d1d5db;
        border: 1px solid #374151;
        text-align: left;
        padding-left: 20px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #374151;
        border-color: #00d4ff;
        color: #00d4ff;
    }
    
    /* Nagłówki i teksty */
    h1, h2, h3 { color: #00d4ff !important; font-family: 'Segoe UI', sans-serif; }
    .stMetric { 
        background-color: #1f2937; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #374151;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_finalny.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
        cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, 
                        ilosc INTEGER, 
                        cena REAL, 
                        kategoria_id INTEGER,
                        data_aktualizacji TEXT,
                        FOREIGN KEY (kategoria_id) REFERENCES kategorie (id))''')

init_db()

# --- NAWIGACJA BOCZNA ---
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
    st.caption(f"Status: Autoryzowany")
    st.caption(f"System: Magazyn v2.1")

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
        st.subheader("Aktualne poziomy zapasów")
        st.bar_chart(df.set_index('nazwa')['ilosc'])
    else:
        st.info("System gotowy do pracy. Brak zarejestrowanych towarów.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Wyszukiwarka Zasobów")
    query_search = st.text_input("Szukaj towaru po nazwie...")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria, p.data_aktualizacji 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if query_search:
        df = df[df['nazwa'].str.contains(query_search, case=False)]
    st.dataframe(df, use_container_width=True, hide_index=True)

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Rejestracja Dostaw")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Zdefiniuj kategorie przed rejestracją towaru.")
    else:
        with st.form("delivery_form"):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa artykułu")
            kat = col1.selectbox("Kategoria", kat_df['nazwa'])
            ilosc = col2.number_input("Ilość", min_value=0, step=1)
            cena = col2.number_input("Cena jednostkowa", min_value=0.0, step=0.01)
            if st.form_submit_button("Zapisz w systemie"):
                if nazwa:
                    kat_id = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    with get_connection() as conn:
                        conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                    (nazwa, ilosc, cena, kat_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    st.success(f"Dodano: {nazwa}")
                    st.rerun()

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, (p.ilosc * p.cena) as suma, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        st.subheader("Udział grup towarowych w kapitale")
        st.area_chart(df.groupby('kategoria')['suma'].sum())
        st.subheader("Zestawienie analityczne")
        st.table(df)
    else:
        st.warning("Brak danych do analizy.")

elif st.session_state.menu == "Konfiguracja Kategorii":
    st.title("Konfiguracja Systemu")
    col_input, col_table = st.columns(2)
    with col_input:
        nowa_kat = st.text_input("Nowa kategoria towarowa")
        if st.button("Dodaj kategorię"):
            if nowa_kat:
                try:
                    with get_connection() as conn:
                        conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    st.success("Kategoria dodana.")
                    st.rerun()
                except:
                    st.error("Dana grupa już istnieje.")
    with col_table:
        kats = pd.read_sql_query("SELECT nazwa FROM kategorie", get_connection())
        st.table(kats)
