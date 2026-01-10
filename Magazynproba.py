import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Magazyn",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 2px 2px 10px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_final.db', check_same_thread=False)

def inicjalizuj_baze():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS kategorie (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT UNIQUE)')
        cur.execute('''CREATE TABLE IF NOT EXISTS produkty (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nazwa TEXT, 
                        ilosc INTEGER, 
                        cena_netto REAL, 
                        kategoria_id INTEGER,
                        data_aktualizacji TEXT,
                        FOREIGN KEY (kategoria_id) REFERENCES kategorie (id))''')

inicjalizuj_baze()

# --- PANEL BOCZNY ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>📦 Magazyn</h1>", unsafe_allow_html=True)
    st.divider()
    menu = st.selectbox(
        "Nawigacja:",
        ["📈 Podsumowanie", "📑 Lista Towarów", "🛠️ Zarządzanie Kategoriami"]
    )
    st.divider()
    st.caption(f"Data: {datetime.now().strftime('%d.%m.%Y')}")

# --- MODUŁ 1: PODSUMOWANIE ---
if menu == "📈 Podsumowanie":
    st.title("📈 Podsumowanie magazynu")
    
    query = '''SELECT p.nazwa, p.ilosc, p.cena_netto, k.nazwa as kategoria 
               FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id'''
    try:
        df = pd.read_sql_query(query, get_connection())
    except:
        df = pd.DataFrame()

    if not df.empty:
        df['Wartość'] = df['ilosc'] * df['cena_netto']
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Liczba produktów", len(df))
        m2.metric("Suma sztuk", int(df['ilosc'].sum()))
        m3.metric("Wartość netto", f"{df['Wartość'].sum():,.2f} zł")
        m4.metric("Średnia cena", f"{df['cena_netto'].mean():,.2f} zł")
        
        st.divider()
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.subheader("📋 Tabela produktów")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📂 Pobierz raport CSV", csv, "raport_magazyn.csv", "text/csv")
            
        with c2:
            st.subheader("📊 Ilość towarów")
            st.bar_chart(df.set_index('nazwa')['ilosc'])
    else:
        st.info("Baza danych jest pusta. Zacznij od dodania kategorii w menu bocznym.")

# --- MODUŁ 2: LISTA TOWARÓW ---
elif menu == "📑 Lista Towarów":
    st.title("📑 Ewidencja towarów")
    
    tab1, tab2 = st.tabs(["🔎 Podgląd", "➕ Dodaj towar"])
    
    with tab2:
        kat_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if kat_df.empty:
            st.warning("Najpierw musisz dodać kategorie w ustawieniach.")
        else:
            with st.form("new_product_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                name = col1.text_input("Nazwa towaru")
                category = col1.selectbox("Kategoria", kat_df['nazwa'])
                quantity = col2.number_input("Ilość", min_value=0, step=1)
                price = col2.number_input("Cena (zł)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("Dodaj do magazynu"):
                    if name:
                        kat_id = int(kat_df[kat_df['nazwa'] == category]['id'].values[0])
                        with get_connection() as conn:
                            conn.execute("INSERT INTO produkty (nazwa, ilosc, cena_netto, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                        (name, quantity, price, kat_id, datetime.now().strftime("%d.%m.%Y %H:%M")))
                        st.success(f"Dodano produkt: {name}")
                        st.rerun()

    with tab1:
        inventory = pd.read_sql_query("SELECT id, nazwa, ilosc FROM produkty", get_connection())
        if not inventory.empty:
            to_delete = st.selectbox("Wybierz towar do usunięcia:", inventory['nazwa'])
            if st.button("🗑️ Usuń produkt", type="primary"):
                with get_connection() as conn:
                    conn.execute("DELETE FROM produkty WHERE nazwa = ?", (to_delete,))
                st.rerun()
            
            st.divider()
            for _, row in inventory.iterrows():
                st.write(f"**{row['nazwa']}**: {row['ilosc']} szt.")
                st.progress(min(row['ilosc'] / 100, 1.0))
        else:
            st.info("Brak towarów w bazie.")

# --- MODUŁ 3: ZARZĄDZANIE KATEGORIAMI ---
elif menu == "🛠️ Zarządzanie Kategoriami":
    st.title("🛠️ Ustawienia")
    
    left, right = st.columns(2)
    with left:
        st.subheader("Nowa kategoria")
        new_kat = st.text_input("Nazwa")
        if st.button("Zapisz kategorię"):
            if new_kat:
                try:
                    with get_connection() as conn:
                        conn.execute("INSERT INTO kategorie (nazwa) VALUES (?)", (new_kat,))
                    st.success(f"Dodano: {new_kat}")
                    st.rerun()
                except:
                    st.error("Ta kategoria już istnieje.")

    with right:
        st.subheader("Lista kategorii")
        current_kats = pd.read_sql_query("SELECT nazwa FROM kategorie", get_connection())
        st.table(current_kats)
