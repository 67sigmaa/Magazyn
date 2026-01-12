import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

# Inicjalizacja klienta Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- NAWIGACJA ---
with st.sidebar:
    st.title("📦 MAGAZYN CLOUD")
    menu = st.radio("Menu:", 
        ["Pulpit", "Zasoby", "Dostawy", "Finanse", "Kategorie"])

# --- MODUŁY ---

if menu == "Pulpit":
    st.title("Pulpit Manedżerski")
    # Pobieranie danych z joinem (tabela kategoria)
    res = supabase.table("produkty").select("nazwa, liczba, cena, kategoria(nazwa)").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # Mapowanie zagnieżdżonego słownika z kategorii na tekst
        df['kategoria_nazwa'] = df['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba SKU", len(df))
        c2.metric("Suma jednostek", int(df['liczba'].sum()))
        val = (df['liczba'] * df['cena']).sum()
        c3.metric("Wycena inwentarza", f"{val:,.2f} PLN")
    else:
        st.info("Baza jest pusta.")

elif menu == "Zasoby":
    st.title("Wyszukiwarka")
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria(nazwa)").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        df['kat_nazwa'] = df['kategoria'].apply(lambda x: x['nazwa'] if x else "Brak")
        qs = st.text_input("Szukaj produktu...")
        
        filtered = df[df['nazwa'].str.contains(qs, case=False)] if qs else df
        st.dataframe(filtered[['nazwa', 'liczba', 'cena', 'kat_nazwa']], use_container_width=True)
        
        st.divider()
        to_del = st.selectbox("Usuń produkt", df['nazwa'].tolist())
        if st.button("Usuń trwale"):
            supabase.table("produkty").delete().eq("nazwa", to_del).execute()
            st.success(f"Usunięto {to_del}")
            st.rerun()

elif menu == "Dostawy":
    st.title("Przyjęcie Towaru")
    # Pobierz kategorie do selectboxa
    kats = supabase.table("kategoria").select("id, nazwa").execute().data
    kat_options = {k['nazwa']: k['id'] for k in kats}
    
    if not kat_options:
        st.error("Dodaj najpierw kategorie!")
    else:
        with st.form("add_prod"):
            nazwa = st.text_input("Nazwa")
            kat_id = st.selectbox("Kategoria", options=list(kat_options.keys()))
            liczba = st.number_input("Ilość", min_value=1)
            cena = st.number_input("Cena", min_value=0.0)
            
            if st.form_submit_button("Zapisz w chmurze"):
                # Sprawdź czy produkt istnieje
                existing = supabase.table("produkty").select("*").eq("nazwa", nazwa).execute()
                
                if existing.data:
                    nowa_liczba = existing.data[0]['liczba'] + liczba
                    supabase.table("produkty").update({"liczba": nowa_liczba, "cena": cena}).eq("nazwa", nazwa).execute()
                else:
                    supabase.table("produkty").insert({
                        "nazwa": nazwa, 
                        "liczba": liczba, 
                        "cena": cena, 
                        "kategoria_id": kat_options[kat_id]
                    }).execute()
                st.success("Zsynchronizowano z Supabase")

elif menu == "Kategorie":
    st.title("Zarządzanie Kategoriami")
    c1, c2 = st.columns(2)
    
    with c1:
        n_kat = st.text_input("Nazwa nowej kategorii")
        n_opis = st.text_area("Opis (opcjonalnie)")
        if st.button("Dodaj kategorię"):
            supabase.table("kategoria").insert({"nazwa": n_kat, "opis": n_opis}).execute()
            st.rerun()
            
    with c2:
        lista_k = supabase.table("kategoria").select("nazwa").execute().data
        if lista_k:
            st.write("Aktualne kategorie:")
            for k in lista_k:
                st.text(f"• {k['nazwa']}")
