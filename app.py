import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MRP Maty Termoizolacyjne", layout="wide")

# ==========================================
# 1. INICJALIZACJA DANYCH W PAMĘCI (MOCK DB)
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # Magazyn Komponentów
    st.session_state.komponenty = pd.DataFrame([
        {"ID": "K01", "Nazwa": "Pianka PE 5mm", "Stan": 1500, "Jednostka": "m", "Min_Stan": 500},
        {"ID": "K02", "Nazwa": "Folia Aluminiowa", "Stan": 2000, "Jednostka": "m", "Min_Stan": 800},
        {"ID": "K03", "Nazwa": "Klej przemysłowy", "Stan": 50, "Jednostka": "kg", "Min_Stan": 20},
        {"ID": "K04", "Nazwa": "Tuleja tekturowa", "Stan": 100, "Jednostka": "szt", "Min_Stan": 30}
    ])
    
    # Receptury (BOM) - co potrzeba na 1 rolkę maty
    st.session_state.receptury = pd.DataFrame([
        {"Wariant": "Mata Standard 5mm", "ID_Komp": "K01", "Ilosc": 50},  # 50m pianki na rolkę
        {"Wariant": "Mata Standard 5mm", "ID_Komp": "K02", "Ilosc": 50},  # 50m folii na rolkę
        {"Wariant": "Mata Standard 5mm", "ID_Komp": "K03", "Ilosc": 1},   # 1kg kleju na rolkę
        {"Wariant": "Mata Standard 5mm", "ID_Komp": "K04", "Ilosc": 1},   # 1 tuleja
        
        {"Wariant": "Mata Premium 10mm", "ID_Komp": "K01", "Ilosc": 100}, # grubsza, 100m pianki
        {"Wariant": "Mata Premium 10mm", "ID_Komp": "K02", "Ilosc": 50},
        {"Wariant": "Mata Premium 10mm", "ID_Komp": "K03", "Ilosc": 1.5},
        {"Wariant": "Mata Premium 10mm", "ID_Komp": "K04", "Ilosc": 1}
    ])
    
    # Magazyn Produktów Gotowych
    st.session_state.produkty = pd.DataFrame([
        {"Wariant": "Mata Standard 5mm", "Stan": 15},
        {"Wariant": "Mata Premium 10mm", "Stan": 5}
    ])
    
    # Historia Ruchów (pusta na start)
    st.session_state.historia = pd.DataFrame(columns=["Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Kontrahent"])

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
# INTERFEJS UŻYTKOWNIKA (MENU)
# ==========================================
menu = st.sidebar.radio("Nawigacja", ["Pulpit & Stany", "Zlecenie Produkcji", "Przyjęcie (PZ)", "Wydanie (WZ)"])

# ------------------------------------------
# ZAKŁADKA 1: PULPIT I STANY
# ------------------------------------------
if menu == "Pulpit & Stany":
    st.header("📊 Pulpit Magazynowy")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Wyroby Gotowe")
        st.dataframe(st.session_state.produkty, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🧱 Surowce (Komponenty)")
        # Wyróżnianie stanów poniżej minimum (alert)
        df_k = st.session_state.komponenty.copy()
        df_k["Status"] = df_k.apply(lambda row: "⚠️ MAŁO!" if row["Stan"] <= row["Min_Stan"] else "✅ OK", axis=1)
        st.dataframe(df_k, use_container_width=True, hide_index=True)
        
    st.subheader("📝 Historia Operacji")
    st.dataframe(st.session_state.historia.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True)

# ------------------------------------------
# ZAKŁADKA 2: PRODUKCJA (MRP)
# ------------------------------------------
elif menu == "Zlecenie Produkcji":
    st.header("⚙️ Kalkulator i Zlecenie Produkcji")
    
    warianty_lista = st.session_state.produkty["Wariant"].tolist()
    wybrany_wariant = st.selectbox("Wybierz wariant do produkcji:", warianty_lista)
    
    # LOGIKA MRP: Sprawdzanie maksymalnej możliwej produkcji
    receptura_wariantu = st.session_state.receptury[st.session_state.receptury["Wariant"] == wybrany_wariant]
    
    max_rolek = float('inf') # Zaczynamy od nieskończoności
    waskie_gardlo = ""
    
    szczegoly = []
    
    for _, wiersz in receptura_wariantu.iterrows():
        id_komp = wiersz["ID_Komp"]
        potrzeba_na_rolke = wiersz["Ilosc"]
        
        komponent = st.session_state.komponenty[st.session_state.komponenty["ID"] == id_komp].iloc[0]
        stan_komp = komponent["Stan"]
        nazwa_komp = komponent["Nazwa"]
        
        # Ile rolek możemy zrobić z TEGO konkretnego surowca?
        mozliwe_z_tego = int(stan_komp / potrzeba_na_rolke)
        
        szczegoly.append(f"- **{nazwa_komp}**: Mamy {stan_komp}, potrzeba {potrzeba_na_rolke}/rolkę -> Starczy na **{mozliwe_z_tego}** rolek.")
        
        if mozliwe_z_tego < max_rolek:
            max_rolek = mozliwe_z_tego
            waskie_gardlo = nazwa_komp
            
    st.info(f"### Maksymalnie możesz wyprodukować: **{max_rolek}** rolek.")
    if max_rolek > 0:
        st.write(f"Wąskie gardło (najsłabsze ogniwo): {waskie_gardlo}")
    with st.expander("Zobacz szczegóły wyliczeń"):
        for s in szczegoly:
            st.write(s)
            
    st.divider()
    st.subheader("Zatwierdź Produkcję")
    ile_produkujemy = st.number_input("Ile rolek chcesz wyprodukować?", min_value=1, max_value=max_rolek if max_rolek > 0 else 1, value=1 if max_rolek > 0 else 0)
    
    if st.button("Wyprodukuj i zaktualizuj magazyn", disabled=(max_rolek == 0)):
        # 1. Zwiększ stan produktów
        idx_prod = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_wariant][0]
        st.session_state.produkty.at[idx_prod, "Stan"] += ile_produkujemy
        
        # 2. Zmniejsz stan komponentów (RW)
        for _, wiersz in receptura_wariantu.iterrows():
            id_komp = wiersz["ID_Komp"]
            potrzeba_na_rolke = wiersz["Ilosc"]
            zuzycie_laczne = potrzeba_na_rolke * ile_produkujemy
            
            idx_komp = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == id_komp][0]
            st.session_state.komponenty.at[idx_komp, "Stan"] -= zuzycie_laczne
            
            nazwa_komp = st.session_state.komponenty.at[idx_komp, "Nazwa"]
            dodaj_ruch("RW", "Wewn.", nazwa_komp, zuzycie_laczne, "Hala Produkcyjna")
            
        # 3. Zapisz ruch (PW - Przychód Wewnętrzny)
        dodaj_ruch("PW", "Wewn.", wybrany_wariant, ile_produkujemy, "Hala Produkcyjna")
        
        st.success(f"Wyprodukowano {ile_produkujemy} rolek: {wybrany_wariant}!")
        st.rerun()

# ------------------------------------------
# ZAKŁADKA 3: PRZYJĘCIE (PZ)
# ------------------------------------------
elif menu == "Przyjęcie (PZ)":
    st.header("📥 Przyjęcie Zewnętrzne Towaru (PZ)")
    with st.form("pz_form"):
        nr_doc = st.text_input("Numer dokumentu (np. FV/123)")
        dostawca = st.text_input("Dostawca")
        
        lista_komp = st.session_state.komponenty["Nazwa"].tolist()
        wybrany_komp = st.selectbox("Wybierz surowiec", lista_komp)
        ilosc = st.number_input("Ilość", min_value=1.0, value=100.0)
        
        if st.form_submit_button("Zatwierdź Przyjęcie"):
            idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == wybrany_komp][0]
            st.session_state.komponenty.at[idx, "Stan"] += ilosc
            dodaj_ruch("PZ", nr_doc, wybrany_komp, ilosc, dostawca)
            st.success("Zapisano przyjęcie!")
            st.rerun()

# ------------------------------------------
# ZAKŁADKA 4: WYDANIE (WZ)
# ------------------------------------------
elif menu == "Wydanie (WZ)":
    st.header("📤 Wydanie Zewnętrzne Towaru (WZ)")
    with st.form("wz_form"):
        nr_doc = st.text_input("Numer dokumentu (np. WZ/123)")
        klient = st.text_input("Odbiorca (Klient)")
        
        lista_prod = st.session_state.produkty["Wariant"].tolist()
        wybrany_prod = st.selectbox("Wybierz produkt gotowy", lista_prod)
        
        stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
        st.info(f"Dostępne na magazynie: **{stan_obecny}** rolek")
        
        ilosc = st.number_input("Ilość rolek do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
        
        if st.form_submit_button("Zatwierdź Wydanie"):
            if ilosc <= stan_obecny:
                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                st.session_state.produkty.at[idx, "Stan"] -= ilosc
                dodaj_ruch("WZ", nr_doc, wybrany_prod, ilosc, klient)
                st.success("Zapisano wydanie!")
                st.rerun()
            else:
                st.error("Brak wystarczającej ilości towaru na magazynie!")
