import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Magazyn Pro v2.0",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_stdio=True)

# --- FUNKCJE BAZY DANYCH ---
def get_connection():
    return sqlite3.connect('magazyn_v2.db', check_same_thread=False)

def inicjalizuj_baze():
    conn = get_connection()
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
    conn.commit()
    conn.close()

def wykonaj_sql(query, params=()):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()

# --- LOGIKA APLIKACJI ---
inicjalizuj_baze()

# --- PANEL BOCZNY (NAWIGACJA) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2271/2271062.png", width=100)
    st.title("System Zarządzania")
    menu = st.radio("Przejdź do:", ["📊 Dashboard", "📦 Asortyment", "⚙️ Ustawienia Kategorii"])
    st.divider()
    st.info("Zalogowano jako: Administrator")

# --- MODUŁ 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Statystyki Magazynowe")
    
    query = '''SELECT p.id, p.nazwa, p.ilosc, p.cena_netto, k.nazwa as kategoria 
               FROM produkty p JOIN kategorie k ON p.kategoria_id = k.id'''
    df = pd.read_sql_query(query, get_connection())
    
    if not df.empty:
        df['wartosc'] = df['ilosc'] * df['cena_netto']
        
        # Wskaźniki (KPI)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wszystkie Produkty", len(df))
        c2.metric("Łączna Ilość", int(df['ilosc'].sum()))
        c3.metric("Wartość Netto", f"{df['wartosc'].sum():,.2f} zł")
        c4.metric("Średnia Cena", f"{df['cena_netto'].mean():,.2f} zł")
        
        st.divider()
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("📋 Pełna lista produktów")
            st.dataframe(df[['nazwa', 'kategoria', 'ilosc', 'cena_netto', 'wartosc']], use_container_width=True)
            
            # Export danych
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Pobierz raport CSV", csv, "raport_magazynowy.csv", "text/csv")
            
        with col_right:
            st.subheader("📈 Udział kategorii")
            kat_stats = df.groupby('kategoria')['ilosc'].sum()
            st.bar_chart(kat_stats)
    else:
        st.warning("Baza danych jest pusta. Przejdź do sekcji Asortyment, aby dodać produkty.")

# --- MODUŁ 2: ASORTYMENT (DODAWANIE I USUWANIE) ---
elif menu == "📦 Asortyment":
    st.title("📦 Zarządzanie Produktami")
    
    tab_list, tab_add = st.tabs(["🔎 Przeglądaj i Edytuj", "✨ Dodaj Nowy Produkt"])
    
    with tab_add:
        kategorie_df = pd.read_sql_query("SELECT * FROM kategorie", get_connection())
        if kategorie_df.empty:
            st.error("Błąd: Najpierw zdefiniuj kategorie w ustawieniach!")
        else:
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                nazwa = c1.text_input("Nazwa produktu")
                kat = c1.selectbox("Kategoria", kategorie_df['nazwa'])
                ilosc = c2.number_input("Ilość", min_value=0, step=1)
                cena = c2.number_input("Cena netto (zł)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("✅ Dodaj produkt do bazy"):
                    if nazwa:
                        kat_id = int(kategorie_df[kategorie_df['nazwa'] == kat]['id'].values[0])
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        wykonaj_sql("INSERT INTO produkty (nazwa, ilosc, cena_netto, kategoria_id, data_aktualizacji) VALUES (?,?,?,?,?)",
                                   (nazwa, ilosc, cena, kat_id, now))
                        st.success(f"Dodano: {nazwa}")
                        st.rerun()
    
    with tab_list:
        df_list = pd.read_sql_query("SELECT id, nazwa, ilosc FROM produkty", get_connection())
        if not df_list.empty:
            st.write("Wybierz produkt, aby go usunąć:")
            produkt_do_usuniecia = st.selectbox("Wybierz produkt", df_list['nazwa'])
            if st.button("🗑️ Usuń wybrany produkt", type="primary"):
                wykonaj_sql("DELETE FROM produkty WHERE nazwa = ?", (produkt_do_usuniecia,))
                st.toast(f"Usunięto {produkt_do_usuniecia}")
                st.rerun()
        else:
            st.info("Brak produktów do wyświetlenia.")

# --- MODUŁ 3: USTAWIENIA KATEGORII ---
elif menu == "⚙️ Ustawienia Kategorii":
    st.title("⚙️ Konfiguracja Systemu")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Nowa Kategoria")
        nowa_kat = st.text_input("Nazwa (np. Meble, Akcesoria)")
        if st.button("Dodaj kategorię"):
            if nowa_kat:
                try:
                    wykonaj_sql("INSERT INTO kategorie (nazwa) VALUES (?)", (nowa_kat,))
                    st.success("Dodano!")
                    st.rerun()
                except:
                    st.error("Ta kategoria już istnieje!")

    with col_b:
        st.subheader("Istniejące Kategorie")
        kat_df = pd.read_sql_query("SELECT nazwa FROM kategorie", get_connection())
        st.table(kat_df)
