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
    .stApp { background-color: #0d1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    label, p, span, .stMarkdown, [data-testid="stWidgetLabel"] p, .stTable, table, td, th {
        color: #ffffff !important;
    }
    .stButton>button {
        width: 100%; border-radius: 6px; background-color: #21262d;
        color: #f0f6fc !important; border: 1px solid #8b949e; text-align: left;
        padding-left: 20px; font-weight: 500;
    }
    .stButton>button:hover { background-color: #30363d; border-color: #58a6ff; color: #58a6ff !important; }
    h1, h2, h3 { color: #58a6ff !important; margin-bottom: 20px; }
    div[data-testid="stMetric"] { background-color: #30363d; padding: 20px; border-radius: 10px; border: 2px solid #8b949e; }
    [data-testid="stMetricLabel"] { color: #ffffff !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold !important; }
    .alert-box { background-color: #442726; border: 2px solid #f85149; padding: 15px; border-radius: 8px; color: #ff7b72; margin-bottom: 20px; font-weight: bold; }
    thead tr th { background-color: #21262d !important; color: #58a6ff !important; }
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

# --- BAZA DANYCH (ZGODNA ZE SCHEMATEM) ---
def get_connection():
    return sqlite3.connect('magazyn_finalny.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('PRAGMA foreign_keys = ON;')
        # Tabela Kategorie wg schematu (id, nazwa, opis)
        cur.execute('''CREATE TABLE IF NOT EXISTS kategorie (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT UNIQUE, 
                        opis TEXT)''')
        # Tabela Produkty wg schematu (id, nazwa, liczba, cena, kategoria_id)
        cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, 
                        liczba INTEGER, 
                        cena REAL, 
                        kategoria_id INTEGER,
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
    df = pd.read_sql_query('''SELECT p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        low_stock = df[df['liczba'] < 5]
        if not low_stock.empty:
            st.markdown(f'<div class="alert-box">⚠️ ALARM: {len(low_stock)} produkty wymagają domówienia!</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['liczba'].sum()))
        c3.metric("Wycena inwentarza", f"{(df['liczba'] * df['cena']).sum():,.2f} PLN")
    else:
        st.info("Brak towarów w bazie.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Zarządzanie Zasobami")
    df = pd.read_sql_query('''SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    
    tab1, tab2, tab3 = st.tabs(["🔎 Szukaj", "📤 Wydawanie Towaru", "🗑️ Usuń Produkt"])
    
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
            st.subheader("Wydaj towar z magazynu")
            wybrany_produkt = st.selectbox("Wybierz produkt do wydania", df['nazwa'].tolist())
            dostepna_ilosc = df[df['nazwa'] == wybrany_produkt]['liczba'].values[0]
            st.info(f"Aktualny stan dla **{wybrany_produkt}**: {dostepna_ilosc} szt.")
            
            ilosc_wydania = st.number_input("Ilość do wydania", min_value=1, max_value=int(dostepna_ilosc) if dostepna_ilosc > 0 else 1, step=1)
            if st.button("Zatwierdź Wydanie"):
                conn = get_connection()
                nowa_ilosc = int(dostepna_ilosc - ilosc_wydania)
                conn.execute("UPDATE produkty SET liczba = ?, data_aktualizacji = ? WHERE nazwa = ?", 
                             (nowa_ilosc, datetime.now().strftime("%d.%m.%Y %H:%M"), wybrany_produkt))
                conn.commit()
                conn.close()
                st.success(f"Wydano {ilosc_wydania} szt.")
                st.rerun()
        else:
            st.info("Magazyn jest pusty.")

    with tab3:
        if not df.empty:
            st.warning("Uwaga: Usunięcie produktu jest nieodwracalne.")
            prod_to_del = st.selectbox("Wybierz produkt do usunięcia", df['nazwa'].tolist())
            if st.button("Potwierdź usunięcie"):
                conn = get_connection()
                conn.execute("DELETE FROM produkty WHERE nazwa = ?", (prod_to_del,))
                conn.commit()
                conn.close()
                st.success(f"Usunięto {prod_to_del}")
                st.rerun()

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Przyjęcie Towaru")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Najpierw dodaj kategorie!")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Artykuł")
            kat = c1.selectbox("Grupa", kat_df['nazwa'])
            ilosc = c2.number_input("Sztuki (liczba)", min_value=1, step=1)
            cena = c2.number_input("Cena", min_value=0.01, step=0.01)
            if st.form_submit_button("Zatwierdź"):
                if nazwa:
                    kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    conn = get_connection()
                    existing = conn.execute("SELECT id, liczba FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                    if existing:
                        nowa_ilosc = existing[1] + ilosc
                        conn.execute("UPDATE produkty SET liczba = ?, cena = ?, data_aktualizacji = ? WHERE id = ?", 
                                     (nowa_ilosc, cena, datetime.now().strftime("%d.%m.%Y %H:%M"), existing[0]))
                    else:
                        conn.execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                    (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                    conn.commit()
                    conn.close()
                    st.success(f"Zapisano: {nazwa}")

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.liczba, p.cena, (p.liczba * p.cena) as suma, k.nazwa as kategoria 
                              FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        st.metric("Całkowita wycena netto", f"{df['suma'].sum():,.2f} PLN")
        kat_stats = df.groupby('kategoria')['suma'].agg(['sum', 'count']).rename(columns={'sum': 'Suma PLN', 'count': 'Liczba SKU'})
        st.table(kat_stats)

elif st.session_state.menu == "Konfiguracja Kategorii":
    st.title("Zarządzanie Kategoriami")
    col_add, col_del = st.columns(2)
    with col_add:
        st.subheader("Dodaj nową")
        nowa_kat = st.text_input("Nazwa grupy")
        opis_kat = st.text_area("Opis grupy (opis)")
        if st.button("➕ Dodaj grupę"):
            if nowa_kat:
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO kategorie (nazwa, opis) VALUES (?,?)", (nowa_kat, opis_kat))
                    conn.commit()
                    st.success("Dodano kategorię")
                    st.rerun()
                except: st.error("Kategoria już istnieje")
                finally: conn.close()

    with col_del:
        st.subheader("Usuń istniejącą")
        kats_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if not kats_df.empty:
            kat_to_del = st.selectbox("Wybierz grupę", kats_df['nazwa'])
            if st.button("🗑️ Usuń grupę"):
                conn = get_connection()
                kid = int(kats_df[kats_df['nazwa'] == kat_to_del]['id'].values[0])
                if conn.execute("SELECT id FROM produkty WHERE kategoria_id = ?", (kid,)).fetchone():
                    st.error("Kategoria zawiera produkty!")
                else:
                    conn.execute("DELETE FROM kategorie WHERE id = ?", (kid,))
                    conn.commit()
                    st.rerun()
                conn.close()
    
    st.divider()
    st.subheader("Aktualna lista kategorii")
    st.table(pd.read_sql_query("SELECT nazwa, opis FROM kategorie", get_connection()))
