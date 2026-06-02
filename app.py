import streamlit as st
import pandas as pd
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="MRP GrizoThermo+", layout="wide")

# ==========================================
# 1. INICJALIZACJA BAZY "NA SUCHO"
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # Stany początkowe - Magazyn Komponentów
    st.session_state.komponenty = pd.DataFrame([
        {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb", "Min_Stan": 1000.0},
        {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg", "Min_Stan": 5.0},
        {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg", "Min_Stan": 3.0}
    ])
    
    # Receptura dla GrizoThermo+
    st.session_state.receptury = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K01", "Ilosc": 32.0},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K02", "Ilosc": 0.2},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K03", "Ilosc": 0.1}
    ])
    
    # Magazyn Produktów Gotowych
    st.session_state.produkty = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "Stan": 0}
    ])
    
    # Historia Ruchów
    st.session_state.historia = pd.DataFrame(columns=[
        "Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Kontrahent"
    ])

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent):
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ,
        "Dokument": dokument,
        "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc,
        "Kontrahent": kontrahent
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

# ==========================================
# MENU GŁÓWNE I PANEL ADMINA
# ==========================================
st.sidebar.title("Nawigacja")

opcje_menu = [
    "📊 Pulpit & Stany", 
    "⚙️ Produkcja", 
    "📥 Przyjęcie towaru (PZ)", 
    "📤 Wydanie towaru (WZ)"
]

st.sidebar.divider()
is_admin = st.sidebar.checkbox("🔐 Odblokuj tryb Admina")

if is_admin:
    opcje_menu.append("🛠️ Panel Admina (Korekty)")

menu = st.sidebar.radio("Wybierz zakładkę:", opcje_menu)

# ------------------------------------------
# ZAKŁADKA 1: PULPIT I STANY
# ------------------------------------------
if menu == "📊 Pulpit & Stany":
    st.header("📊 Aktualne Stany Magazynowe")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Wyroby Gotowe (Rolki)")
        st.dataframe(st.session_state.produkty, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🧱 Surowce (Komponenty)")
        df_k = st.session_state.komponenty.copy()
        df_k["Status"] = df_k.apply(lambda row: "⚠️ MAŁO!" if row["Stan"] <= row["Min_Stan"] else "✅ OK", axis=1)
        st.dataframe(df_k, use_container_width=True, hide_index=True)
        
    st.subheader("📝 Ostatnie operacje (Historia)")
    st.dataframe(st.session_state.historia.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True)

# ------------------------------------------
# ZAKŁADKA 2: PRODUKCJA (BOM & Kalkulator)
# ------------------------------------------
elif menu == "⚙️ Produkcja":
    st.header("⚙️ Kalkulator Produkcji: GrizoThermo+")
    
    wybrany_wariant = "GrizoThermo+ (1,15m x 13mb)"
    
    # Pobieranie stanów komponentów
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    stan_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
    stan_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

    # Przeliczanie potencjału produkcyjnego
    potencjal_alu = int(stan_alu / 32.0)
    potencjal_bialy = int(stan_bialy / 0.2)
    potencjal_zielony = int(stan_zielony / 0.1)

    max_rolek = min(potencjal_alu, potencjal_bialy, potencjal_zielony)

    # Wyświetlanie wyników wąskiego gardła
    st.write("### Z obecnych stanów magazynowych możemy wykonać:")
    col1, col2, col3 = st.columns(3)
    col1.metric("Ograniczenie: Aluminium", f"{potencjal_alu} rolek")
    col2.metric("Ograniczenie: Barw. biały", f"{potencjal_bialy} rolek")
    col3.metric("Ograniczenie: Barw. zielony", f"{potencjal_zielony} rolek")
    
    if max_rolek > 0:
        st.success(f"🚀 Maksymalnie jesteśmy w stanie wyprodukować: **{max_rolek} rolek**.")
    else:
        st.error("❌ Brak wystarczającej ilości surowców do uruchomienia produkcji!")

    st.divider()
    
    # Formularz zlecenia produkcji
    st.subheader("Zatwierdź Produkcję")
    with st.form("produkcja_form"):
        ile_produkujemy = st.number_input("Ile rolek wyprodukowano?", min_value=1, max_value=max_rolek if max_rolek > 0 else 1, value=1 if max_rolek > 0 else 0)
        
        if st.form_submit_button("Zaksięguj Produkcję", disabled=(max_rolek == 0)):
            # 1. Dodajemy rolki do magazynu
            idx_prod = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_wariant][0]
            st.session_state.produkty.at[idx_prod, "Stan"] += ile_produkujemy
            dodaj_ruch("PW", "Wewn.", wybrany_wariant, ile_produkujemy, "Hala Produkcyjna")
            
            # 2. Odejmujemy surowce z magazynu
            receptura = st.session_state.receptury[st.session_state.receptury["Wariant"] == wybrany_wariant]
            for _, wiersz in receptura.iterrows():
                id_komp = wiersz["ID_Komp"]
                zuzycie_laczne = wiersz["Ilosc"] * ile_produkujemy
                
                idx_komp = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == id_komp][0]
                st.session_state.komponenty.at[idx_komp, "Stan"] -= zuzycie_laczne
                nazwa_komp = st.session_state.komponenty.at[idx_komp, "Nazwa"]
                dodaj_ruch("RW", "Wewn.", nazwa_komp, zuzycie_laczne, "Hala Produkcyjna")
            
            st.success(f"Udana produkcja! Zaksięgowano {ile_produkujemy} rolek.")
            st.rerun()

# ------------------------------------------
# ZAKŁADKA 3: PRZYJĘCIE (PZ)
# ------------------------------------------
elif menu == "📥 Przyjęcie towaru (PZ)":
    st.header("📥 Nowa dostawa surowców (PZ)")
    with st.form("pz_form"):
        nr_doc = st.text_input("Numer dokumentu (np. FV, nr zamówienia)")
        dostawca = st.text_input("Nazwa dostawcy")
        wybrany_komp = st.selectbox("Wybierz surowiec", st.session_state.komponenty["Nazwa"].tolist())
        ilosc = st.number_input("Ilość przyjęta (w jednostce surowca)", min_value=0.1, value=100.0)
        
        if st.form_submit_button("Zatwierdź Przyjęcie"):
            idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == wybrany_komp][0]
            st.session_state.komponenty.at[idx, "Stan"] += ilosc
            dodaj_ruch("PZ", nr_doc, wybrany_komp, ilosc, dostawca)
            st.success("Zapisano przyjęcie towaru na magazyn!")
            st.rerun()

# ------------------------------------------
# ZAKŁADKA 4: WYDANIE (WZ)
# ------------------------------------------
elif menu == "📤 Wydanie towaru (WZ)":
    st.header("📤 Wydanie gotowych mat do klienta (WZ)")
    with st.form("wz_form"):
        nr_doc = st.text_input("Numer dokumentu (np. FV, WZ)")
        klient = st.text_input("Nazwa klienta")
        wybrany_prod = st.selectbox("Wybierz wariant do wydania", st.session_state.produkty["Wariant"].tolist())
        
        stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
        st.info(f"Dostępne na magazynie gotowym: **{stan_obecny} rolek**")
        
        ilosc = st.number_input("Ilość rolek do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
        
        if st.form_submit_button("Zatwierdź Wydanie"):
            if ilosc <= stan_obecny:
                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                st.session_state.produkty.at[idx, "Stan"] -= ilosc
                dodaj_ruch("WZ", nr_doc, wybrany_prod, ilosc, klient)
                st.success("Zapisano wydanie towaru!")
                st.rerun()
            else:
                st.error("Błąd: Próbujesz wydać więcej rolek, niż znajduje się na magazynie!")

# ------------------------------------------
# ZAKŁADKA 5: PANEL ADMINA
# ------------------------------------------
elif menu == "🛠️ Panel Admina (Korekty)":
    st.header("🛠️ Ręczna korekta stanów magazynowych")
    st.info("💡 Kliknij dwukrotnie w komórkę w kolumnie 'Stan', aby ją edytować, a następnie kliknij przycisk zapisu.")
    
    st.subheader("1. Korekta Surowców")
    zmienione_komponenty = st.data_editor(st.session_state.komponenty, key="edit_komp", hide_index=True, use_container_width=True)
    
    if st.button("💾 Zapisz nowe stany surowców"):
        st.session_state.komponenty = zmienione_komponenty
        dodaj_ruch("KOREKTA", "Admin", "Wiele surowców", 0, "Aktualizacja ręczna")
        st.success("Zaktualizowano stany surowców!")
        st.rerun()

    st.divider()

    st.subheader("2. Korekta Wyrobów Gotowych")
    zmienione_produkty = st.data_editor(st.session_state.produkty, key="edit_prod", hide_index=True, use_container_width=True)
    
    if st.button("💾 Zapisz nowe stany produktów"):
        st.session_state.produkty = zmienione_produkty
        dodaj_ruch("KOREKTA", "Admin", "Wiele produktów", 0, "Aktualizacja ręczna")
        st.success("Zaktualizowano stany wyrobów gotowych!")
        st.rerun()
