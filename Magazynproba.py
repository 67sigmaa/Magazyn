import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn", layout="wide", page_icon="📦")

# Stylizacja Dark Nexus
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { 
        background-color: #1f2937; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #00d4ff;
    }
    .status-card { 
        background-color: #1f2937; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }
    h1, h2, h3 { color: #00d4ff !format; }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_nowy.db', check_same_thread=False)

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
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00d4ff;'>SYSTEM MAGAZYN</h2>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("MODUŁY OPERACYJNE:", ["🛰️ Monitor Systemu", "📥 Zarządzanie Towarem", "⚙️ Konfiguracja Bazowa"])
    st.divider()
    st.caption(f"Status: Połączono | {datetime.now().strftime('%d.%m.%Y')}")

# --- MODUŁ 1: MONITOR (DASHBOARD) ---
if menu == "🛰️ Monitor Systemu":
    st.title("🛰️ Panel Monitorowania Magazynu")
    
    query = '''SELECT p.nazwa, p.ilosc, p.cena, k.nazwa as kategoria 
               FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id'''
    try:
        df = pd.read_sql_query(query, get_connection())
    except:
        df = pd.DataFrame()

    if not df.empty:
        df['Wartość'] = df['ilosc'] * df['cena']
        
        # Statystyki w kartach
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SKU w Bazie", len(df))
        c2.metric("Suma Jednostek", int(df['ilosc'].sum()))
        c3.metric("Wycena Netto", f"{df['Wartość'].sum():,.2f} zł")
        c4.metric("Średnia Cena", f"{df['cena'].mean():,.2f} zł")
        
        st.divider()
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("📋 Inwentaryzacja Bieżąca")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("💾 Eksportuj dane do CSV", csv, "magazyn_raport.csv", "text/csv")
            
        with col_right:
            st.subheader("📊 Rozkład Ilościowy")
            st.bar_chart(df.set_index('nazwa')['ilosc'])
    else:
        st.warning("⚠️ Brak danych. Skonfiguruj kategorie i dodaj pierwsze towary.")

# --- MODUŁ 2: ZARZĄDZANIE TOWAREM ---
elif menu == "📥 Zarządzanie Towarem":
    st.title("📥 Operacje Towarowe")
    
    tab_view, tab_add = st.tabs(["🔍 Przegląd i Usuwanie", "✨ Nowa Dostawa"])
    
    with tab_add:
        kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if kat_df.empty:
            st.error("Wymagana konfiguracja kategorii przed przyjęciem towaru!")
        else:
            with st.form("add_product_nexus"):
                st.subheader("Rejestracja Produktu")
                c1, c2 = st.columns(2)
                nazwa = c1.text_input("Nazwa artykułu")
                kat = c1.selectbox("Kategoria docelowa", kat_df['nazwa'])
                ilosc = c2.number_input("Ilość (szt.)", min_value=0, step=1)
                cena = c2.number_input("Cena jednostkowa (zł)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("ZATWIERDŹ PRZYJĘCIE"):
                    if nazwa:
                        kat_id = int(kat_df[kat_df['nazwa'] == kat]['id'].values[0])
                        with get_connection() as conn:
                            conn.execute("INSERT INTO produkty (nazwa, ilosc, cena, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                        (nazwa, ilosc, cena, kat_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
                        st.success(f"Produkt {nazwa} wprowadzony do systemu.")
                        st.rerun()

    with tab_view:
        inv = pd.read_sql_query("SELECT nazwa, ilosc FROM produkty", get_connection())
        if not inv.empty:
            st.subheader("Usuwanie z ewidencji")
            item_to_del = st.selectbox("Wybierz pozycję:", inv['nazwa'])
            if st.button("USUŃ POZYCJĘ", type="primary"):
                with get_connection() as conn:
                    conn.execute("DELETE FROM produkty WHERE nazwa = ?", (item_to_del,))
                st.rerun()
            
            st.divider()
            st.subheader("Monitor Stanów Niskich")
            for _, row in inv.iterrows():
                if row['ilosc'] < 5:
                    st.markdown(f"<div class='status-card' style='border-left: 5px solid #ff4b4b;'>⚠️ <b>{row['nazwa']}</b> - Niski stan: {row['ilosc']} szt.</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='status-card'>✅ {row['nazwa']} - Stan: {row['ilosc']} szt.</div>", unsafe_allow_html=True)
        else:
            st.info("Brak towarów w ewidencji.")

# --- MODUŁ 3: KONFIGURACJA ---
elif menu == "⚙️ Konfiguracja Bazowa":
    st.title("⚙️ Parametry Systemu")
    
    l, r = st.columns(2)
    with l:
        st.subheader("Definiowanie Kategorii")
        n_kat = st.text_input("Nazwa nowej grupy")
        if st.button("DODAJ GRUPĘ"):
            if n_kat:
                try:
                    with get_connection() as conn:
                        conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (n_kat,))
                    st.success(f"Dodano: {n_kat}")
                    st.rerun()
                except:
                    st.error("Kategoria już istnieje.")
    
    with r:
        st.subheader("Aktywne Grupy")
        kats = pd.read_sql_query("SELECT nazwa FROM kategorie", get_connection())
        st.table(kats)
