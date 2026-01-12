import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="System Magazynowy", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stButton>button { width: 100%; border-radius: 6px; text-align: left; padding-left: 20px; }
    h1, h2, h3 { color: #58a6ff !important; }
    .alert-box { background-color: #442726; border: 1px solid #f85149; padding: 15px; border-radius: 8px; color: #ff7b72; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

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

# --- NAWIGACJA W BOCZNYM PANELU ---
with st.sidebar:
    st.title("📦 MAGAZYN")
    menu = st.radio("Menu główne:", 
        ["Pulpit Manedżerski", "Wyszukiwarka Zasobów", "Rejestracja Dostaw", "Raport Finansowy", "Konfiguracja Kategorii"])

# --- MODUŁY ---

if menu == "Pulpit Manedżerski":
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

elif menu == "Wyszukiwarka Zasobów":
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
            prod_to_del = st.selectbox("Wybierz produkt do usunięcia", df['nazwa'].tolist())
            if st.button("Potwierdź usunięcie"):
                conn = get_connection()
                conn.execute("DELETE FROM produkty WHERE nazwa = ?", (prod_to_del,))
                conn.commit()
                conn.close()
                st.success(f"Usunięto {prod_to_del}")
                st.rerun()

elif menu == "Rejestracja Dostaw":
    st.title("Przyjęcie Towaru")
    kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
    if kat_df.empty:
        st.error("Najpierw dodaj kategorie w zakładce 'Konfiguracja Kategorii'!")
    else:
        with st.form("delivery"):
            c1, c2 = st.columns(2)
            nazwa = c1.text_input("Nazwa artykułu")
            kat = c1.selectbox("Kategoria", kat_df['nazwa'])
            ilosc = c2.number_input("Ilość (szt)", min_value=1, step=1)
            cena = c2.number_input("Cena jedn. (PLN)", min_value=0.01, step=0.01)
            
            if st.form_submit_button("Dodaj do magazynu"):
                kid = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                conn = get_connection()
                existing = conn.execute("SELECT id, ilosc FROM produkty WHERE nazwa = ?", (nazwa,)).fetchone()
                
                if existing:
                    nowa_ilosc = existing[1] + ilosc
                    conn.execute("UPDATE produkty SET ilosc = ?, cena = ?, data_aktualizacji = ? WHERE id = ?", 
                                 (nowa_ilosc, cena, datetime.now().strftime("%d.%m.%Y %H:%M"), existing[0]))
                else:
                    conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                (nazwa, ilosc, cena, kid, datetime.now().strftime("%d.%m.%Y %H:%M")))
                conn.commit()
                conn.close()
                st.success(f"Zaktualizowano stan: {nazwa}")

elif menu == "Raport Finansowy":
    st.title("Raport Finansowy")
    df = pd.read_sql_query('''SELECT p.nazwa, p.ilosc, p.cena, (p.ilosc * p.cena) as suma, k.nazwa as kategoria FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id''', get_connection())
    if not df.empty:
        st.metric("Całkowita wartość netto", f"{df['suma'].sum():,.2f} PLN")
        kat_stats = df.groupby('kategoria')['suma'].agg(['sum', 'count']).rename(columns={'sum': 'Suma (PLN)', 'count': 'Liczba SKU'})
        st.table(kat_stats)
    else:
        st.info("Brak danych do raportu.")

elif menu == "Konfiguracja Kategorii":
    st.title("Kategorie")
    c1, c2 = st.columns(2)
    
    with c1:
        nowa_kat = st.text_input("Nowa kategoria")
        if st.button("➕ Dodaj"):
            if nowa_kat:
                conn = get_connection()
                try:
                    conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    conn.commit()
                    st.rerun()
                except: st.error("Kategoria już istnieje")
                finally: conn.close()

    with c2:
        kats_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if not kats_df.empty:
            kat_to_del = st.selectbox("Usuń kategorię", kats_df['nazwa'])
            if st.button("🗑️ Usuń"):
                conn = get_connection()
                kid = int(kats_df[kats_df['nazwa'] == kat_to_del]['id'].values[0])
                has_products = conn.execute("SELECT id FROM produkty WHERE kategoria_id = ?", (kid,)).fetchone()
                
                if has_products:
                    st.error("Kategoria zawiera produkty!")
                else:
                    conn.execute("DELETE FROM kategorie WHERE id = ?", (kid,))
                    conn.commit()
                    st.rerun()
                conn.close()
