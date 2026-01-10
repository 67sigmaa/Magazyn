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
    
    /* Tło główne - bardzo ciemne dla kontrastu */
    .stApp { background-color: #0d1117; color: #ffffff; }
    
    /* Panel boczny - wyraźnie oddzielony */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Przyciski menu - jasne obramowanie, aby były widoczne */
    .stButton>button {
        width: 100%; border-radius: 6px; background-color: #21262d;
        color: #f0f6fc; border: 1px solid #8b949e; text-align: left;
        padding-left: 20px; font-weight: 500;
    }
    .stButton>button:hover { 
        background-color: #30363d; 
        border-color: #58a6ff; 
        color: #58a6ff; 
    }
    
    /* Nagłówki - jaskrawy błękit */
    h1, h2, h3 { color: #58a6ff !important; margin-bottom: 20px; }
    
    /* KARTY METRYK - teraz są jasnoszare, aby mocno kontrastowały z czarnym tłem */
    div[data-testid="stMetric"] { 
        background-color: #30363d; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #8b949e; /* Grubsza, jasna ramka */
    }
    
    /* Napisy w metrykach - białe i czytelne */
    [data-testid="stMetricLabel"] { color: #c9d1d9 !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold !important; }

    /* Tabele - jasne krawędzie */
    .stDataFrame, .stTable { 
        border: 1px solid #484f58;
    }
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
    st.markdown("<h2 style='text-align: center; color: #58a6ff;'>KONTROLA MAGAZYNU</h2>", unsafe_allow_html=True)
    if st.button("Pulpit Manedżerski"): st.session_state.menu = "Pulpit Manedżerski"
    if st.button("Wyszukiwarka Zasobów"): st.session_state.menu = "Wyszukiwarka Zasobów"
    if st.button("Rejestracja Dostaw"): st.session_state.menu = "Rejestracja Dostaw"
    if st.button("Raport Finansowy"): st.session_state.menu = "Raport Finansowy"
    if st.button("Konfiguracja Kategorii"): st.session_state.menu = "Konfiguracja Kategorii"
    st.divider()
    st.caption("Status: Tryb Wysokiego Kontrastu")

# --- LOGIKA MODUŁÓW ---

if st.session_state.menu == "Pulpit Manedżerski":
    st.title("Pulpit Manedżerski")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['ilosc'].sum()))
        c3.metric("Wycena inwentarza", f"{(df['ilosc'] * df['cena']).sum():,.2f} PLN")
        
        st.subheader("Bieżące zestawienie stanów")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Brak zarejestrowanych towarów.")

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
            cena = c2.number_input("Cena jednostkowa", min_value=0.0, step=0.01)
            if st.form_submit_button("Zapisz w systemie"):
                if nazwa:
                    kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    with get_connection() as conn:
                        conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                    (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                    st.success(f"Dodano produkt: {nazwa}")

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, (p.ilosc * p.cena) as suma, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        st.table(df)
        total_val = df['suma'].sum()
        st.metric("Całkowita wycena netto", f"{total_val:,.2f} PLN")
    else:
        st.warning("Brak danych.")

elif st.session_state.menu == "Konfiguracja Kategorii":
    st.title("Konfiguracja Systemu")
    col_in, col_tab = st.columns([1, 2])
    
    with col_in:
        nowa_kat = st.text_input("Nowa grupa")
        if st.button("Dodaj do bazy"):
            if nowa_kat:
                conn = get_connection()
                check = conn.execute("SELECT 1 FROM kategorie WHERE nazwa = ?", (nowa_kat,)).fetchone()
                if check:
                    st.error(f"Grupa '{nowa_kat}' już istnieje.")
                else:
                    conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    conn.commit()
                    st.success(f"Dodano grupę: {nowa_kat}")
                conn.close()
    
    with col_tab:
        kats = pd.read_sql_query("SELECT nazwa as 'Zarejestrowane Kategorie' FROM kategorie", get_connection())
        st.table(kats)
