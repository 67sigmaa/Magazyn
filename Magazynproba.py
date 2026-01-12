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
    div[data-testid="stMetric"] { background-color: #30363d; padding: 20px; border-radius: 10px; border: 2px solid #8b949e; }
    .alert-box { background-color: #442726; border: 2px solid #f85149; padding: 15px; border-radius: 8px; color: #ff7b72; font-weight: bold; margin-bottom: 20px; }
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

# --- LOGOWANIE ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("Autoryzacja Systemu")
    u = st.text_input("Użytkownik")
    p = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if u == "admin" and p == "123":
            st.session_state.auth = True
            st.rerun()
        else: st.error("Błąd logowania")
    st.stop()

# --- NAWIGACJA ---
if 'menu' not in st.session_state: st.session_state.menu = "Pulpit"

with st.sidebar:
    st.markdown("<h3 style='color: #58a6ff;'>MENU GŁÓWNE</h3>", unsafe_allow_html=True)
    if st.button("📊 Pulpit"): st.session_state.menu = "Pulpit"
    if st.button("📥 Przyjęcie Towaru"): st.session_state.menu = "Dostawa"
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
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['ilosc'].sum()))
        c3.metric("Wycena", f"{(df['ilosc']*df['cena']).sum():,.2f} PLN")
        
        low = df[df['ilosc'] < 5]
        if not low.empty:
            st.markdown(f'<div class="alert-box">⚠️ NISKIE STANY ({len(low)}): {", ".join(low["nazwa"].tolist())}</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else: st.info("Baza jest pusta.")

elif st.session_state.menu == "Dostawa":
    st.title("📥 Przyjęcie Towaru (Dostawa)")
    kats = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kats.empty: st.warning("Najpierw dodaj kategorie!")
    else:
        with st.form("dostawa"):
            nazwa = st.text_input("Nazwa artykułu")
            kat = st.selectbox("Kategoria", kats['nazwa'])
            ilosc = st.number_input("Ilość", min_value=1)
            cena = st.number_input("Cena (PLN)", min_value=0.01)
            if st.form_submit_button("Zapisz w bazie"):
                kid = int(kats[kats['nazwa'] == kat]['id'].values[0])
                conn = get_connection()
                existing = conn.execute("SELECT id, ilosc FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                now = datetime.now().strftime("%d.%m.%Y %H:%M")
                if existing:
                    conn.execute("UPDATE produkty SET ilosc = ilosc + ?, cena = ?, data_aktualizacji = ? WHERE id = ?", (ilosc, cena, now, existing[0]))
                else:
                    conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)", (nazwa, ilosc, cena, kid, now))
                conn.commit()
                st.success(f"Przyjęto: {nazwa}")

elif st.session_state.menu == "Zarzadzanie":
    st.title("📦 Zarządzanie i Rozchód")
    df = pd.read_sql_query("SELECT * FROM produkty", get_connection())
    
    if df.empty:
        st.info("Brak produktów w bazie.")
    else:
        tab1, tab2 = st.tabs(["📤 Wydanie z Magazynu", "🗑️ Usuwanie Produktów"])
        
        with tab1:
            st.subheader("Wydaj towar klientowi/do produkcji")
            wybor = st.selectbox("Wybierz produkt", df['nazwa'].tolist(), key="wyd_sel")
            dane_prod = df[df['nazwa'] == wybor].iloc[0]
            st.info(f"Aktualny stan: **{dane_prod['ilosc']}** szt.")
            
            ile_wydac = st.number_input("Ilość do wydania", min_value=1, max_value=int(dane_prod['ilosc']))
            if st.button("Zatwierdź wydanie"):
                conn = get_connection()
                conn.execute("UPDATE produkty SET ilosc = ilosc - ? WHERE nazwa = ?", (ile_wydac, wybor))
                conn.commit()
                st.success(f"Wydano {ile_wydac} szt. produktu {wybor}")
                st.rerun()

        with tab2:
            st.subheader("Całkowite usunięcie z ewidencji")
            prod_del = st.selectbox("Wybierz produkt do usunięcia", df['nazwa'].tolist(), key="del_sel")
            if st.button("Usuń bezpowrotnie"):
                conn = get_connection()
                conn.execute("DELETE FROM produkty WHERE nazwa = ?", (prod_del,))
                conn.commit()
                st.warning(f"Produkt {prod_del} został usunięty z bazy.")
                st.rerun()

elif st.session_state.menu == "Kategorie":
    st.title("⚙️ Konfiguracja Kategorii")
    c1, c2 = st.columns(2)
    
    with c1:
        new_k = st.text_input("Nowa nazwa grupy")
        if st.button("Dodaj kategorię"):
            if new_k:
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (new_k,))
                    conn.commit()
                    st.success("Dodano!")
                    st.rerun()
                except: st.error("Już istnieje!")

    with c2:
        kats = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if not kats.empty:
            kat_del = st.selectbox("Usuń kategorię", kats['nazwa'])
            if st.button("Usuń grupę"):
                conn = get_connection()
                kid = int(kats[kats['nazwa'] == kat_del]['id'].values[0])
                # Sprawdzenie czy są produkty
                check = conn.execute("SELECT id FROM produkty WHERE kategoria_id = ?", (kid,)).fetchone()
                if check:
                    st.error("Nie możesz usunąć kategorii, która zawiera produkty!")
                else:
                    conn.execute("DELETE FROM kategorie WHERE id = ?", (kid,))
                    conn.commit()
                    st.success("Usunięto!")
                    st.rerun()
