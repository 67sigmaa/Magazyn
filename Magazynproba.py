import streamlit as st
import pandas as pd
import psycopg2 # Zmienione z sqlite3
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

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

# --- BAZA DANYCH (SUPABASE) ---
def get_connection():
    # Pobiera URL z st.secrets (zgodnie z Twoją prośbą o secrets)
    return psycopg2.connect(st.secrets["database"]["url"])

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # W PostgreSQL używamy SERIAL zamiast AUTOINCREMENT
            cur.execute('''CREATE TABLE IF NOT EXISTS kategorie (
                            id SERIAL PRIMARY KEY, 
                            nazwa TEXT UNIQUE, 
                            opis TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                            id SERIAL PRIMARY KEY, 
                            nazwa TEXT, 
                            liczba INTEGER, 
                            cena REAL, 
                            kategoria_id INTEGER REFERENCES kategorie(id),
                            data_aktualizacji TEXT)''')
        conn.commit()

init_db()

# --- NAWIGACJA ---
if 'menu' not in st.session_state:
    st.session_state.menu = "Wyszukiwarka Zasobów"

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #58a6ff;'>KONTROLA MAGAZYNU</h2>", unsafe_allow_html=True)
    if st.button("Pulpit Manedżerski"): st.session_state.menu = "Pulpit Manedżerski"
    if st.button("Wyszukiwarka Zasobów"): st.session_state.menu = "Wyszukiwarka Zasobów"
    if st.button("Rejestracja Dostaw"): st.session_state.menu = "Rejestracja Dostaw"
    if st.button("Raport Finansowy"): st.session_state.menu = "Raport Finansowy"
    if st.button("Konfiguracja Kategorii"): st.session_state.menu = "Konfiguracja Kategorii"

# --- MODUŁY ---

if st.session_state.menu == "Pulpit Manedżerski":
    st.title("Pulpit Manedżerski")
    with get_connection() as conn:
        df = pd.read_sql_query('''SELECT p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
                                  FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', conn)
    if not df.empty:
        low_stock = df[df['liczba'] < 5]
        if not low_stock.empty:
            st.markdown(f'<div class="alert-box">⚠️ ALARM: {len(low_stock)} produkty wymagają domówienia!</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['liczba'].sum()))
        c3.metric("Wycena inwentarza", f"{(df['liczba'] * df['cena']).sum():,.2f} PLN")
        
        st.subheader("Szybki podgląd stanów")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Brak towarów w bazie Supabase.")

elif st.session_state.menu == "Wyszukiwarka Zasobów":
    st.title("Zarządzanie Zasobami")
    with get_connection() as conn:
        df = pd.read_sql_query('''SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa as kategoria 
                                  FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', conn)
    
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
            wybrany_produkt = st.selectbox("Wybierz produkt", df['nazwa'].tolist())
            dostepna_ilosc = df[df['nazwa'] == wybrany_produkt]['liczba'].values[0]
            st.info(f"Stan: {dostepna_ilosc} szt.")
            ilosc_wydania = st.number_input("Ilość", min_value=1, max_value=int(dostepna_ilosc) if dostepna_ilosc > 0 else 1)
            if st.button("Zatwierdź Wydanie"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        # W PostgreSQL używamy %s zamiast ?
                        cur.execute("UPDATE produkty SET liczba = %s, data_aktualizacji = %s WHERE nazwa = %s", 
                                   (int(dostepna_ilosc - ilosc_wydania), datetime.now().strftime("%d.%m.%Y %H:%M"), wybrany_produkt))
                    conn.commit()
                st.success("Wydano towar!")
                st.rerun()

    with tab3:
        if not df.empty:
            prod_to_del = st.selectbox("Usuń produkt", df['nazwa'].tolist())
            if st.button("Potwierdź"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM produkty WHERE nazwa = %s", (prod_to_del,))
                    conn.commit()
                st.rerun()

elif st.session_state.menu == "Rejestracja Dostaw":
    st.title("Przyjęcie Towaru")
    with get_connection() as conn:
        kat_df = pd.read_sql_query("SELECT * FROM kategorie", conn)
    
    if kat_df.empty:
        st.error("Najpierw dodaj kategorie!")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Artykuł")
            kat = c1.selectbox("Grupa", kat_df['nazwa'])
            ilosc = c2.number_input("Sztuki", min_value=1)
            cena = c2.number_input("Cena", min_value=0.01)
            if st.form_submit_button("Zatwierdź"):
                kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT id, liczba FROM produkty WHERE nazwa = %s", (nazwa,))
                        existing = cur.fetchone()
                        if existing:
                            cur.execute("UPDATE produkty SET liczba = %s, cena = %s, data_aktualizacji = %s WHERE id = %s", 
                                       (existing[1] + ilosc, cena, datetime.now().strftime("%d.%m.%Y %H:%M"), existing[0]))
                        else:
                            cur.execute("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id, data_aktualizacji) VALUES (%s,%s,%s,%s,%s)",
                                       (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                    conn.commit()
                st.rerun()

elif st.session_state.menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    with get_connection() as conn:
        df = pd.read_sql_query('''SELECT p.nazwa, p.liczba, p.cena, (p.liczba * p.cena) as suma, k.nazwa as kategoria 
                                  FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', conn)
    if not df.empty:
        st.metric("Wycena (Supabase)", f"{df['suma'].sum():,.2f} PLN")
        st.table(df.groupby('kategoria')['suma'].agg(['sum', 'count']))

elif st.session_state.menu == "Konfiguracja Kategorii":
    st.title("Zarządzanie Kategoriami")
    col_add, col_del = st.columns(2)
    with col_add:
        nowa_kat = st.text_input("Nazwa grupy")
        opis_kat = st.text_area("Opis")
        if st.button("➕ Dodaj"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO kategorie (nazwa, opis) VALUES (%s,%s)", (nowa_kat, opis_kat))
                conn.commit()
            st.rerun()

    with col_del:
        with get_connection() as conn:
            kats_df = pd.read_sql_query("SELECT * FROM kategorie", conn)
        if not kats_df.empty:
            kat_to_del = st.selectbox("Usuń grupę", kats_df['nazwa'])
            if st.button("🗑️ Usuń"):
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM kategorie WHERE nazwa = %s", (kat_to_del,))
                    conn.commit()
                st.rerun()
