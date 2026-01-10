import sqlite3
import streamlit as st

# Funkcja inicjalizująca bazę danych
def inicjalizuj_baze():
    # Używamy check_same_thread=False, aby SQLite działał poprawnie w Streamlit
    conn = sqlite3.connect('sklep.db', check_same_thread=False)
    cursor = conn.cursor()

    # Tworzenie tabeli Kategoria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kategoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL,
            opis TEXT
        )
    ''')

    # Tworzenie tabeli Produkty
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produkty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL,
            liczba INTEGER,
            cena REAL,
            kategoria_id INTEGER,
            FOREIGN KEY (kategoria_id) REFERENCES kategoria (id)
        )
    ''')
    
    conn.commit()
    return conn

def dodaj_kategorie(conn, nazwa, opis):
    sql = 'INSERT INTO kategoria (nazwa, opis) VALUES (?, ?)'
    cur = conn.cursor()
    cur.execute(sql, (nazwa, opis))
    conn.commit()

def dodaj_produkt(conn, nazwa, liczba, cena, kategoria_id):
    sql = 'INSERT INTO produkty (nazwa, liczba, cena, kategoria_id) VALUES (?, ?, ?, ?)'
    cur = conn.cursor()
    cur.execute(sql, (nazwa, liczba, cena, kategoria_id))
    conn.commit()

def wyswietl_wszystko(conn):
    cur = conn.cursor()
    query = '''
        SELECT p.id, p.nazwa, p.liczba, p.cena, k.nazwa 
        FROM produkty p
        JOIN kategoria k ON p.kategoria_id = k.id
    '''
    cur.execute(query)
    rows = cur.fetchall()
    
    if rows:
        st.subheader("Lista produktów w bazie:")
        # Wyświetlamy dane jako ładną tabelę w Streamlit
        st.table(rows)
    else:
        st.info("Baza danych jest pusta. Kliknij przycisk poniżej, aby dodać dane.")

# --- GŁÓWNA LOGIKA PROGRAMU ---
if __name__ == "__main__":
    st.title("Zarządzanie Sklepem 🛒")
    
    polaczenie = inicjalizuj_baze()

    # Przycisk do dodawania danych, żeby nie dodawały się przy każdym odświeżeniu strony
    if st.button("Dodaj przykładowe dane do bazy"):
        dodaj_kategorie(polaczenie, "Elektronika", "Urządzenia elektroniczne")
        dodaj_kategorie(polaczenie, "Dom", "Artykuły domowe")
        
        dodaj_produkt(polaczenie, "Laptop", 5, 3500.00, 1)
        dodaj_produkt(polaczenie, "Myszka", 20, 150.50, 1)
        dodaj_produkt(polaczenie, "Czajnik", 10, 89.99, 2)
        st.success("Dodano przykładowe dane!")

    # Wyświetlanie tabeli
    wyswietl_wszystko(polaczenie)
    
    polaczenie.close()
