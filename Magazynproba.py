import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px # Opcjonalne, ale Streamlit obsłuży podstawowe wykresy bez tego

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="WMS Nexus", layout="wide", page_icon="🚀")

# Funkcja stylizacji "Dark Industrial"
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .status-card { 
        background-color: #1e2130; border-left: 5px solid #00d4ff; 
        padding: 20px; border-radius: 5px; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('nexus_wms.db', check_same_thread=False)
    cur = conn.cursor()
    # Tabela Lokalizacji (Regały)
    cur.execute('CREATE TABLE IF NOT EXISTS locations (id TEXT PRIMARY KEY, zone TEXT, capacity INTEGER)')
    # Tabela Towarów z terminem ważności i statusem
    cur.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    sku TEXT PRIMARY KEY, 
                    name TEXT, 
                    qty INTEGER, 
                    min_stock INTEGER,
                    location_id TEXT,
                    status TEXT,
                    last_update TEXT)''')
    conn.commit()
    return conn

db = init_db()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067451.png", width=80)
    st.title("WMS NEXUS v3")
    tab = st.selectbox("Moduł Operacyjny", 
        ["🛰️ Monitoring Systemu", "📥 Przyjęcie Towaru", "📍 Zarządzanie Lokalizacją", "⚠️ Alerty i Raporty"])

# --- MODUŁ 1: MONITORING (DASHBOARD) ---
if tab == "🛰️ Monitoring Systemu":
    st.title("🛰️ Panel Monitorowania Operacji")
    
    df = pd.read_sql_query("SELECT * FROM inventory", db)
    
    if not df.empty:
        # Wskaźniki techniczne
        col1, col2, col3, col4 = st.columns(4)
        total_items = df['qty'].sum()
        low_stock_count = len(df[df['qty'] <= df['min_stock']])
        
        col1.metric("Suma SKU", len(df))
        col2.metric("Wolumen Całkowity", total_items)
        col3.metric("Alerty Zapasów", low_stock_count, delta_color="inverse", delta=f"-{low_stock_count}")
        col4.metric("Sprawność Magazynu", "98.4%")

        st.divider()

        # Mapa cieplna magazynu (Wykres)
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Obłożenie Sekcji Magazynowych")
            st.bar_chart(df, x="location_id", y="qty", color="#00d4ff")
        
        with c2:
            st.subheader("Statusy Przetwarzania")
            status_counts = df['status'].value_counts()
            st.write(status_counts)
    else:
        st.info("System gotowy do pracy. Brak danych w bazie.")

# --- MODUŁ 2: PRZYJĘCIE TOWARU (INBOUND) ---
elif tab == "📥 Przyjęcie Towaru":
    st.title("📥 Rejestracja Dostawy (Inbound)")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Kod SKU (np. NEX-100)")
            item_name = st.text_input("Nazwa Techniczna")
            qty = st.number_input("Ilość Przyjęta", min_value=1)
        with col2:
            min_s = st.number_input("Próg Alarmowy (Min Stock)", min_value=0)
            loc = st.selectbox("Alokacja Regałowa", ["A-101", "A-102", "B-201", "C-305"])
            stat = st.select_slider("Status Partii", options=["Kwarantanna", "Kontrola Jakości", "Dostępny"])

        if st.button("🔥 ZATWIERDŹ PRZYJĘCIE"):
            now = datetime.now().strftime("%H:%M:%S")
            cur = db.cursor()
            cur.execute('''INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?,?,?)''', 
                        (sku, item_name, qty, min_s, loc, stat, now))
            db.commit()
            st.balloons()
            st.success(f"Jednostka {sku} została zlokalizowana w strefie {loc}.")

# --- MODUŁ 3: LOKALIZACJE ---
elif tab == "📍 Zarządzanie Lokalizacją":
    st.title("📍 Topografia Magazynu")
    st.write("Podgląd zajętości regałów w czasie rzeczywistym.")
    
    df = pd.read_sql_query("SELECT location_id, name, qty, status FROM inventory", db)
    
    if not df.empty:
        for loc in df['location_id'].unique():
            with st.expander(f"Regał {loc}"):
                items_in_loc = df[df['location_id'] == loc]
                st.table(items_in_loc)
    else:
        st.warning("Nie przypisano jeszcze żadnych towarów do regałów.")

# --- MODUŁ 4: ALERTY ---
elif tab == "⚠️ Alerty i Raporty":
    st.title("⚠️ Centrum Powiadomień")
    
    df = pd.read_sql_query("SELECT * FROM inventory", db)
    low_stock = df[df['qty'] <= df['min_stock']]
    
    if not low_stock.empty:
        st.error(f"Wykryto {len(low_stock)} krytycznych braków!")
        for _, row in low_stock.iterrows():
            st.markdown(f"""
                <div class='status-card'>
                    <strong>ALARM: {row['name']}</strong><br>
                    Obecnie: {row['qty']} | Wymagane: {row['min_stock']}<br>
                    Lokalizacja: {row['location_id']}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Wszystkie stany magazynowe w normie.")
