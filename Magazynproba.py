import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI (WYSOKI KONTRAST) ---
st.set_page_config(page_title="System Magazynowy", layout="wide")

st.markdown("""
    <style>
    /* Ogólne tło i tekst */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Panele boczne i sekcje */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 2px solid #30363d; }
    
    /* INPUTY - Poprawa widoczności */
    input, select, textarea {
        background-color: #21262d !important;
        color: #ffffff !important;
        border: 1px solid #8b949e !important;
    }
    
    /* TABELE - Wyraźne krawędzie i tło */
    .stDataFrame, table { 
        border: 1px solid #30363d !important; 
        background-color: #161b22 !important;
    }

    /* PRZYCISKI - Mocny kontrast */
    .stButton>button {
        width: 100%; border-radius: 6px; 
        background-color: #21262d;
        color: #58a6ff !important; 
        border: 1px solid #58a6ff; 
        font-weight: bold;
        padding: 10px;
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: #58a6ff; 
        color: #ffffff !important; 
        border-color: #ffffff;
    }

    /* NAGŁÓWKI */
    h1, h2, h3 { color: #58a6ff !important; border-bottom: 1px solid #30363d; padding-bottom: 10px; }

    /* METRYKI */
    div[data-testid="stMetric"] { 
        background-color: #1c2128; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #444c56; 
    }
    
    /* ALERTY */
    .low-stock-box { 
        background-color: #381d1c; 
        border: 1px solid #f85149; 
        padding: 10px; 
        border-radius: 5px; 
        color: #ff7b72; 
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- AUTORYZACJA ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Logowanie")
    with st.container():
        u = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("Zaloguj do systemu"):
            if u == "admin" and p == "123":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Nieprawidłowe dane")
    st.stop()

# --- NAWIGACJA ---
if 'menu' not in st.session_state: st.session_state.menu = "Pulpit"

with st.sidebar:
    st.markdown("## 📦 MAGAZYN")
    if st.button("📊 Pulpit Manedżerski"): st.session_state.menu = "Pulpit"
    if st.button("📥 Przyjęcie (Dostawa)"): st.session_state.menu = "Dostawa"
    if st.button("📦 Zarządzanie i Rozchód"): st.session_state.menu = "Zarzadzanie"
    if st.button("⚙️ Konfiguracja Kategorii"): st.session_state.menu = "Kategorie"
    st.divider()
    if st.button("🔴 Wyloguj"):
        st.session_state.auth = False
        st.rerun()

# --- MODUŁY ---

if st.session_state.menu == "Pulpit":
    st.title("Pulpit Manedżerski")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Produkty (SKU)", len(df))
        c2.metric("Suma sztuk", int(df['ilosc'].sum()))
        c3.metric("Wartość Netto", f"{(df['ilosc']*df['cena']).sum():,.2f} PLN")
        
        low = df[df['ilosc'] < 5]
        if not low.empty:
            st.markdown(f'<div class="low-stock-box">⚠️ NISKI STAN: {len(low)} pozycji wymaga uzupełnienia!</div>', unsafe_allow_html=True)
        
        st.subheader("Aktualne stany")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else: st.info("Baza danych jest pusta. Dodaj pierwsze produkty w zakładce 'Dostawa'.")

elif st.session_state.menu == "Dostawa":
    st.title("📥 Przyjęcie Towaru")
    kats = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kats.empty: 
        st.warning("Brak zdefiniowanych kategorii. Przejdź do 'Konfiguracja Kategorii'.")
    else:
        with st.form("form_dostawa"):
            col1, col2 = st.columns(2)
            nazwa = col1.text_input("Nazwa artykułu")
            kat = col1.selectbox("Kategoria", kats['nazwa'])
            ilosc = col2.number_input("Ilość (szt.)", min_value=1, step=1)
            cena = col2.number_input("Cena jednostkowa (PLN)", min_value=0.01, step=0.1)
            if st.form_submit_button("Zatwierdź dostawę"):
                if nazwa:
                    kid = int(kats[kats['nazwa'] == kat]['id'].values[0])
                    conn = get_connection()
                    now = datetime.now().strftime("%d.%m.%Y %H:%M")
                    existing = conn.execute("SELECT id FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                    if existing:
                        conn.execute("UPDATE produkty SET ilosc = ilosc + ?, cena = ?, data_aktualizacji = ? WHERE id = ?", (ilosc, cena, now, existing[0]))
                    else:
                        conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)", (nazwa, ilosc, cena, kid, now))
                    conn.commit()
                    st.success(f"Dodano/Zaktualizowano: {nazwa}")
                else: st.error("Podaj nazwę produktu!")

elif st.session_state.menu == "Zarzadzanie":
    st.title("📦 Zarządzanie i Rozchód")
    df = pd.read_sql_query("SELECT p.id, p.nazwa, p.ilosc, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id", get_connection())
    
    if df.empty:
        st.info("Brak produktów do zarządzania.")
    else:
        tab_wydaj, tab_usun = st.tabs
