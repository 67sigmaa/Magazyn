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
    .stButton>button {
        width: 100%; border-radius: 6px; background-color: #21262d;
        color: #f0f6fc; border: 1px solid #8b949e; text-align: left;
        padding-left: 20px; font-weight: 500;
    }
    .stButton>button:hover { background-color: #30363d; border-color: #58a6ff; color: #58a6ff; }
    h1, h2, h3 { color: #58a6ff !important; margin-bottom: 20px; }
    div[data-testid="stMetric"] { background-color: #30363d; padding: 20px; border-radius: 10px; border: 2px solid #8b949e; }
    [data-testid="stMetricLabel"] { color: #c9d1d9 !important; font-size: 1.1rem !important; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold !important; }
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
    st.caption("Status: Zalogowany Online")

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
        
        st.subheader("Najwartościowsze zasoby (TOP 3)")
        top_3 = df.assign(val=df['ilosc']*df['cena']).nlargest(3, 'val')
        st.table(top_3[['nazwa', 'kategoria', 'val']].rename(columns={'val': 'Wartość Łączna'}))
        
        st.subheader("Pełne zestawienie")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Brak towarów.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Wyszukiwarka Zasobów")
    c1, c2 = st.columns([2, 1])
    qs = c1.text_input("Szukaj po nazwie...")
    min_p = c2.number_input("Cena min.", min_value=0.0)
    
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if qs: df = df[df['nazwa'].str.contains(qs, case=False)]
    df = df[df['cena'] >= min_p]
    st.dataframe(df, use_container_width=True, hide_index=True)

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Rejestracja Dostaw")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Brak kategorii.")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Nazwa artykułu")
            kat = c1.selectbox("Kategoria", kat_df['nazwa'])
            ilosc = c2.number_input("Ilość dostarczona", min_value=1, step=1)
            cena = c2.number_input("Nowa cena jednostkowa", min_value=0.01, step=0.01)
            
            if st.form_submit_button("Zatwierdź dokument"):
                if nazwa:
                    kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                    conn = get_connection()
                    existing = conn.execute("SELECT id, ilosc FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                    
                    if existing:
                        nowa_ilosc = existing[1] + ilosc
                        conn.execute("UPDATE produkty SET ilosc = ?, cena = ?, data_aktualizacji = ? WHERE id = ?", 
                                     (nowa_ilosc, cena, datetime.now().strftime("%d.%m.%Y %H:%M"), existing[0]))
                        st.success(f"Zaktualizowano stan produktu {nazwa}. Nowa ilość: {nowa_ilosc}")
                    else:
                        conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                    (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                        st.success(f"Dodano nowy produkt: {nazwa}")
                    conn.commit()
                    conn.close()

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, (p.ilosc * p.cena) as suma, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        total_val = df['suma'].sum()
        st.metric("Całkowita wycena netto", f"{total_val:,.2f} PLN")
        
        st.subheader("Struktura wartości według kategorii")
        kat_stats = df.groupby('kategoria')['suma'].agg(['sum', 'count']).rename(columns={'sum': 'Suma PLN', 'count': 'Liczba SKU'})
        
        # Obliczanie udziału i zaokrąglanie do liczby całkowitej (int)
        kat_stats['Udział %'] = (kat_stats['Suma PLN'] / total_val * 100).round(0).astype(int)
        
        # Formatowanie dla lepszego wyglądu tabeli
        kat_stats['Udział %'] = kat_stats['Udział %'].astype(str) + " %"
        st.table(kat_stats)
        
        st.subheader("Szczegóły inwentarza")
        st.dataframe(df[['nazwa', 'kategoria', 'ilosc', 'suma']], use_container_width=True)
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
                if check: st.error(f"Grupa '{nowa_kat}' już istnieje.")
                else:
                    conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    conn.commit()
                    st.success(f"Dodano: {nowa_kat}")
                conn.close()
    with col_tab:
        kats = pd.read_sql_query("SELECT nazwa as 'Zarejestrowane Kategorie' FROM kategorie", get_connection())
        st.table(kats)
