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
    
    st.session_state.komponenty = pd.DataFrame([
        {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb", "Min_Stan": 1000.0},
        {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg", "Min_Stan": 5.0},
        {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg", "Min_Stan": 3.0}
    ])
    
    st.session_state.receptury = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K01", "Ilosc": 32.0},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K02", "Ilosc": 0.2},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K03", "Ilosc": 0.1}
    ])
    
    st.session_state.produkty = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "Stan": 0}
    ])
    
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

def koloruj_status(val):
    if isinstance(val, str):
        if 'MAŁO!' in val:
            return 'color: #ff4b4b; font-weight: bold; background-color: #ffe6e6;'
        elif 'OK' in val:
            return 'color: #00c04b; font-weight: bold;'
    return ''

# ==========================================
# MENU GŁÓWNE BZCZNE (SIDEBAR)
# ==========================================
st.sidebar.title("Nawigacja")

opcje_menu = [
    "📊 Pulpit", 
    "⚙️ Produkcja", 
    "🚚 Operacje Magazynowe (PZ/WZ)"
]

st.sidebar.divider()
is_admin = st.sidebar.checkbox("🔐 Odblokuj tryb Admina")

if is_admin:
    opcje_menu.append("🛠️ Panel Admina")

menu = st.sidebar.radio("Wybierz moduł:", opcje_menu)

# ------------------------------------------
# ZAKŁADKA 1: PULPIT I STANY (Z ZAKŁADKAMI)
# ------------------------------------------
if menu == "📊 Pulpit":
    st.header("📊 Aktualne Stany Magazynowe")
    
    # Tworzenie poziomych zakładek wewnątrz pulpitu
    tab_prod, tab_komp, tab_hist = st.tabs(["📦 Wyroby Gotowe", "🧱 Surowce (Komponenty)", "📝 Historia Operacji"])
    
    with tab_prod:
        st.subheader("Stan magazynu gotowych mat")
        st.dataframe(
            st.session_state.produkty, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Wariant": st.column_config.TextColumn("Wariant Maty", width="large"),
                "Stan": st.column_config.NumberColumn("Sztuk na magazynie", format="%d 📦")
            }
        )
    
    with tab_komp:
        st.subheader("Stan magazynu surowców")
        df_k = st.session_state.komponenty.copy()
        df_k["Status"] = df_k.apply(lambda row: "⚠️ MAŁO!" if row["Stan"] <= row["Min_Stan"] else "✅ OK", axis=1)
        
        styled_df_k = df_k.style.map(koloruj_status, subset=['Status'])
        
        st.dataframe(
            styled_df_k, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Nazwa": st.column_config.TextColumn("Nazwa Surowca", width="medium"),
                "Stan": st.column_config.NumberColumn("Stan", format="%.2f"),
                "Min_Stan": None  # Ukrywamy dla czytelności
            }
        )
        
    with tab_hist:
        st.subheader("Ostatnie ruchy magazynowe")
        st.dataframe(
            st.session_state.historia.sort_values(by="Data", ascending=False), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data": st.column_config.DatetimeColumn("Data operacji", format="YYYY-MM-DD HH:mm"),
                "Typ": st.column_config.TextColumn("Typ Ruchu"),
                "Dokument": st.column_config.TextColumn("Nr Dokumentu"),
                "Ilosc": st.column_config.NumberColumn("Ilość", format="%.2f")
            }
        )

# ------------------------------------------
# ZAKŁADKA 2: PRODUKCJA 
# ------------------------------------------
elif menu == "⚙️ Produkcja":
    st.header("⚙️ Produkcja: GrizoThermo+")
    
    # Zakładki dla produkcji - oddzielamy podgląd od formularza
    tab_kalk, tab_zlecenie = st.tabs(["🧮 Kalkulator Potencjału", "✅ Zlecenie Produkcji"])
    
    wybrany_wariant = "GrizoThermo+ (1,15m x 13mb)"
    
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    stan_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
    stan_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

    potencjal_alu = int(stan_alu / 32.0)
    potencjal_bialy = int(stan_bialy / 0.2)
    potencjal_zielony = int(stan_zielony / 0.1)

    max_rolek = min(potencjal_alu, potencjal_bialy, potencjal_zielony)

    with tab_kalk:
        st.write("### Z obecnych stanów magazynowych możemy wykonać:")
        col1, col2, col3 = st.columns(3)
        col1.metric("Zapas: Aluminium", f"{potencjal_alu} rolek")
        col2.metric("Zapas: Barw. biały", f"{potencjal_bialy} rolek")
        col3.metric("Zapas: Barw. zielony", f"{potencjal_zielony} rolek")
        
        if max_rolek > 0:
            st.success(f"🚀 Maksymalnie jesteśmy w stanie wyprodukować: **{max_rolek} rolek**.")
        else:
            st.error("❌ Brak wystarczającej ilości surowców do uruchomienia produkcji!")

    with tab_zlecenie:
        st.subheader("Zatwierdź nową partię")
        with st.form("produkcja_form"):
            ile_produkujemy = st.number_input("Ile rolek wyprodukowano?", min_value=1, max_value=max_rolek if max_rolek > 0 else 1, value=1 if max_rolek > 0 else 0)
            
            if st.form_submit_button("Zaksięguj Produkcję", disabled=(max_rolek == 0)):
                idx_prod = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_wariant][0]
                st.session_state.produkty.at[idx_prod, "Stan"] += ile_produkujemy
                dodaj_ruch("PW", "Wewn.", wybrany_wariant, ile_produkujemy, "Hala Produkcyjna")
                
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
# ZAKŁADKA 3: OPERACJE MAGAZYNOWE (PZ / WZ)
# ------------------------------------------
elif menu == "🚚 Operacje Magazynowe (PZ/WZ)":
    st.header("🚚 Ruchy Magazynowe")
    
    # PZ i WZ jako osobne, czyste zakładki
    tab_pz, tab_wz = st.tabs(["📥 Przyjęcie Surowców (PZ)", "📤 Wydanie Mat (WZ)"])
    
    with tab_pz:
        st.subheader("Rejestracja nowej dostawy")
        with st.form("pz_form"):
            nr_doc = st.text_input("Numer dokumentu (np. FV, nr zamówienia)")
            dostawca = st.text_input("Nazwa dostawcy")
            wybrany_komp = st.selectbox("Wybierz surowiec", st.session_state.komponenty["Nazwa"].tolist())
            ilosc = st.number_input("Ilość przyjęta (w jednostce surowca)", min_value=0.1, value=100.0)
            
            if st.form_submit_button("Zatwierdź Przyjęcie (PZ)"):
                idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == wybrany_komp][0]
                st.session_state.komponenty.at[idx, "Stan"] += ilosc
                dodaj_ruch("PZ", nr_doc, wybrany_komp, ilosc, dostawca)
                st.success("Zapisano przyjęcie towaru na magazyn!")
                st.rerun()

    with tab_wz:
        st.subheader("Wydanie gotowych produktów do klienta")
        with st.form("wz_form"):
            nr_doc_wz = st.text_input("Numer dokumentu (np. FV, WZ)", key="wz_doc")
            klient = st.text_input("Nazwa klienta")
            wybrany_prod = st.selectbox("Wybierz wariant do wydania", st.session_state.produkty["Wariant"].tolist())
            
            stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
            st.info(f"Dostępne na magazynie gotowym: **{stan_obecny} rolek**")
            
            ilosc_wz = st.number_input("Ilość rolek do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
            
            if st.form_submit_button("Zatwierdź Wydanie (WZ)"):
                if ilosc_wz <= stan_obecny:
                    idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                    st.session_state.produkty.at[idx, "Stan"] -= ilosc_wz
                    dodaj_ruch("WZ", nr_doc_wz, wybrany_prod, ilosc_wz, klient)
                    st.success("Zapisano wydanie towaru!")
                    st.rerun()
                else:
                    st.error("Błąd: Próbujesz wydać więcej rolek, niż znajduje się na magazynie!")

# ------------------------------------------
# ZAKŁADKA 4: PANEL ADMINA
# ------------------------------------------
elif menu == "🛠️ Panel Admina":
    st.header("🛠️ Ręczna korekta stanów magazynowych")
    st.info("💡 Tylko kolumny **Stan Aktualny** są edytowalne. Kliknij dwukrotnie wartość, wpisz poprawną i zatwierdź przyciskiem ZAPISZ.")
    
    # Osobne zakładki dla edycji, żeby zachować porządek
    tab_korekt_surowce, tab_korekt_prod = st.tabs(["🧱 Korekta Surowców", "📦 Korekta Wyrobów Gotowych"])
    
    with tab_korekt_surowce:
        zmienione_komponenty = st.data_editor(
            st.session_state.komponenty, 
            key="edit_komp", 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", disabled=True),
                "Nazwa": st.column_config.TextColumn("Nazwa Surowca", disabled=True),
                "Jednostka": st.column_config.TextColumn("Jm.", disabled=True),
                "Min_Stan": st.column_config.NumberColumn("Min. Stan (Alarm)", disabled=True),
                "Stan": st.column_config.NumberColumn("Stan Aktualny ✏️", format="%.2f", required=True)
            }
        )
        
        if st.button("💾 Zapisz nowe stany surowców"):
            st.
