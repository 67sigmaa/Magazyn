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
    
    /* Główne tło i kolory tekstu */
    .stApp { background-color: #0d1117; color: #ffffff; }
    
    /* Pasek boczny */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Wszystkie napisy, etykiety i podpisy na biało */
    label, p, span, .stMarkdown, [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    
    /* Przyciski */
    .stButton>button {
        width: 100%; border-radius: 6px; background-color: #21262d;
        color: #f0f6fc !important; border: 1px solid #8b949e; text-align: left;
        padding-left: 20px; font-weight: 500;
    }
    .stButton>button:hover { background-color: #30363d; border-color: #58a6ff; color: #58a6ff !important; }
    
    /* Nagłówki */
    h1, h2, h3 { color: #58a6ff !important; margin-bottom: 20px; }
    
    /* Metryki */
    div[data-testid="stMetric"] { background-color: #30363d; padding: 20px; border-radius: 10px; border: 2px solid #8b949e; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold !important; }
    
    /* Tabela - wymuszenie białego tekstu w komórkach */
    .stTable, table, th, td {
        color: #ffffff !important;
    }
    thead tr th {
        background-color: #21262d !important;
        color: #58a6ff !important;
    }
    
    /* Inputy (pola tekstowe) */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        color: #ffffff !important;
        background-color: #0d1117 !important;
    }

    /* Alerty */
    .alert-box { background-color: #442726; border: 2px solid #f85149; padding: 15px; border-radius: 8px; color: #ff7b72; margin-bottom: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGOWANIE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

def login():
    st.title("Autoryzacja Systemu")
    with st.container():
        st.markdown('<div style="background-color: #30363d; padding: 30px; border-radius: 10px; border: 1px solid #8b949e;">', unsafe_allow_html=True)
        user = st.text_input("Użytkownik")
        password = st.text_input("Hasło", type="password")
        if st.button("Zaloguj do Magazynu"):
            if user == "admin" and password == "123":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Nieprawidłowe dane")
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.auth:
    login()
    st.stop()

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_finalny.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('PRAGMA foreign_keys = ON;')
        cur.execute('CREATE TABLE IF NOT EXISTS kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
        cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, ilosc INTEGER, cena REAL, kategoria_id INTEGER,
                        data_aktualizacji TEXT,
                        FOREIGN KEY (kategoria_id) REFERENCES kategorie (id))''')
init_db()

# --- NAWIGACJA ---
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
    if st.button("🔴 Wyloguj"):
        st.session_state.auth = False
        st.rerun()

# --- MODUŁY ---

if st.session_state.menu == "Pulpit Manedżerski":
    st.title("Pulpit Manedżerski")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        low_stock = df[df['ilosc'] < 5]
        if not low_stock.empty:
            st.markdown(f'<div class="alert-box">⚠️ ALARM: {len(low_stock)} produkty wymagają domówienia!</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['ilosc'].sum()))
        c3.metric("Wycena inwentarza", f"{(df['ilosc'] * df['cena']).sum():,.2f} PLN")
    else:
        st.info("Brak towarów w bazie.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Wyszukiwarka i Usuwanie")
    df = pd.read_sql_query('''SELECT p.id, p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    
    tab1, tab2 = st.tabs(["🔎 Szukaj", "🗑️ Usuń Produkt"])
    
    with tab1:
        c1, c2 = st.columns([2, 1])
        qs = c1.text_input("Wyszukaj po nazwie...")
        min_p = c2.number_input("Cena od...", min_value=0.0)
        
        filtered_df = df.copy()
        if qs: filtered_df = filtered_df[filtered_df['nazwa'].str.contains(qs, case=False)]
        filtered_df = filtered_df[filtered_df['cena'] >= min_p]
        st.dataframe(filtered_df.drop(columns=['id']), use_container_width=True, hide_index=True)

    with tab2:
        if not df.empty:
            st.warning("Uwaga: Usunięcie produktu jest nieodwracalne.")
            prod_to_del = st.selectbox("Wybierz produkt do usunięcia", df['nazwa'].tolist())
            if st.button("Potwierdź usunięcie produktu"):
                conn = get_connection()
                conn.execute("DELETE FROM produkty WHERE nazwa = ?", (prod_to_del,))
                conn.commit()
                conn.close()
                st.success(f"Usunięto {prod_to_del}")
                st.rerun()
        else:
            st.info("Brak produktów do usunięcia.")

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Przyjęcie Towaru")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Najpierw dodaj kategorie w zakładce 'Konfiguracja Kategorii'!")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Artykuł")
            kat = c1.selectbox("Grupa", kat_df['nazwa'])
            ilosc = c2.number_input("Sztuki", min_value=1, step=1)
            cena = c2.number_input("Cena", min_value=0.01, step=0.01)
            if st.form_submit_button("Zatwierdź"):
                if nazwa:
                    kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    conn = get_connection()
                    existing = conn.execute("SELECT id, ilosc FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                    if existing:
                        nowa_ilosc = existing[1] + ilosc
                        conn.execute("UPDATE produkty SET ilosc = ?, cena = ?, data_aktualizacji = ? WHERE id = ?", 
                                     (nowa_ilosc, cena, datetime.now().strftime("%d.%m.%Y %H:%M"), existing[0]))
