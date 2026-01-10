import sqlite3
import streamlit as st
import pandas as pd

# Ustawienia strony
st.set_page_config(page_title="System Magazynowy", page_icon="📦", layout="wide")

# --- BAZA DANYCH ---
def get_connection():
    return sqlite3.connect('sklep.db', check_same_thread=False)

def inicjalizuj_baze():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS kategoria 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT, opis TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS produkty 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, nazwa TEXT, liczba INTEGER, 
                      cena REAL, kategoria_id INTEGER, 
                      FOREIGN KEY (kategoria_id) REFERENCES kategoria (id))''')
    conn.commit()
    conn.close()

# --- FUNKCJE LOGICZNE ---
def pobierz_dane(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def wykonaj_sql(sql, params):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

# --- INTERFEJS ---
inicjalizuj_baze()

st.sidebar.title("📦 Menu Magazynu")
wybor = st.sidebar.radio("Wybierz akcję:", ["Podgląd Magazynu", "Dodaj Produkt", "Zarządzaj Kategoriami"])

if wybor == "Podgląd Magazynu":
    st.header("📊 Stan Magazynowy")
    
    # Wyszukiwarka
    szukaj = st.text_input("Szukaj produktu po nazwie...")
    
    query = '''SELECT p.id, p.nazwa, p.liczba, p.cena, (p.liczba * p.cena) as wartosc, k.nazwa as kategoria 
               FROM produkty p JOIN kategoria k ON p.kategoria_id = k.id'''
    
    df = pobierz_dane(query)
    
    if not df.empty:
        if szukaj:
            df = df[df['nazwa'].str.contains(szukaj, case=False)]
        
        # Statystyki na górze
        col1, col2, col3 = st.columns(3)
        col1.metric("Liczba produktów", len(df))
        col2.metric("Łączna ilość sztuk", int(df['liczba'].sum()))
        col3.metric("Wartość magazynu", f"{df['wartosc'].sum():.2f} zł")
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Magazyn jest pusty. Dodaj pierwsze produkty w menu bocznym.")

elif wybor == "Dodaj Produkt":
    st.header("➕ Dodawanie nowego produktu")
    
    # Pobranie kategorii do listy rozwijanej
    kategorie_df = pobierz_dane("SELECT id, nazwa FROM kategoria")
    
    if kategorie_df.empty:
        st.warning("Najpierw dodaj przynajmniej jedną kategorię!")
    else:
        with st.form("form_dodaj_produkt", clear_on_submit=True):
            nazwa = st.text_input("Nazwa produktu")
            liczba = st.number_input("Ilość", min_value=0, step=1)
            cena = st.number_input("Cena (zł)", min_value=0.0, step=0.01)
            
            # Mapowanie nazw kategorii na ID
            kat_map = dict(zip(kategorie_df['nazwa'], kategorie_df['id']))
            wybrana_kat = st.selectbox("Kategoria", options=list(kat_map.keys()))
            
            submit = st.form_submit_button("Dodaj do bazy")
            
            if submit and nazwa:
                wykonaj_sql("INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?, ?, ?, ?)",
                           (nazwa, liczba, cena, kat_map[wybrana_kat]))
                st.success(f"Produkt '{nazwa}' został dodany!")

elif wybor == "Zarządzaj Kategoriami":
    st.header("📂 Kategorie produktów")
    
    tab1, tab2 = st.tabs(["Lista kategorii", "Dodaj nową"])
    
    with tab1:
        kat_df = pobierz_dane("SELECT * FROM kategoria")
        st.table(kat_df)
        
    with tab2:
        with st.form("form_kat"):
            n_kat = st.text_input("Nazwa kategorii (np. Elektronika)")
            o_kat = st.text_area("Opis")
            if st.form_submit_button("Zapisz kategorię") and n_kat:
                wykonaj_sql("INSERT INTO kategoria (nazwa, opis) VALUES (?, ?)", (n_kat, o_kat))
                st.success("Kategoria dodana!")
                st.rerun()
