import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Kalkulator Podatkowy Krypto (PIT-38)", layout="wide")

st.title("🪙 Kalkulator Podatkowy Krypto (PIT-38)")
st.markdown("""
Rozliczanie podatku od kryptowalut na podstawie pliku CSV z giełdy Binance.
            
**Instrukcja:**
1. Wgraj plik CSV.
3. W panelu bocznym wybierz rok, który rozliczasz.
2. W panelu bocznym wybierz, które waluty z pliku to waluty tradycyjne (FIAT). Aplikacja przeliczy tylko transakcje z udziałem tych walut.
""")

st.divider()

st.write('Przykładowy plik CSV:')

example = pd.read_csv('example.csv')

st.dataframe(example)

st.divider()

# --- HELPER FUNCTIONS ---

def parse_amount(amount_str):
    """
    Parses the 'Amount' string to separate value and currency.
    Example: '173.74616EUR' -> (173.74616, 'EUR')
    """
    if pd.isna(amount_str):
        return 0.0, None
    match = re.match(r"([0-9.]+)([A-Z]+)", str(amount_str))
    if match:
        return float(match.group(1)), match.group(2)
    return 0.0, None

@st.cache_data
def get_nbp_rate(currency_code, date_str):
    """
    Fetches the average exchange rate (Table A) from NBP API.
    """
    if currency_code == 'PLN':
        return 1.0, date_str

    target_date = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    
    for _ in range(10):
        formatted_date = target_date.strftime("%Y-%m-%d")
        url = f"https://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/{formatted_date}/?format=json"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data['rates'][0]['mid'], formatted_date
        except Exception:
            pass
        
        target_date -= timedelta(days=1)
    
    return None, None

# --- MAIN APPLICATION LOGIC ---

uploaded_file = st.file_uploader("Wgraj plik CSV z historią transakcji", type=["csv"])

if uploaded_file is not None:
    try:
        # Load data
        df = pd.read_csv(uploaded_file)
        
        # Pre-process Date
        try:
            df['Date_Obj'] = pd.to_datetime(df['Date(UTC)'])
            df['Date_YMD'] = df['Date_Obj'].dt.strftime('%Y-%m-%d') # type: ignore
        except:
            st.error(f"Błąd przetwarzania daty. Sprawdź, czy Twój plik CSV jest zgodny z przykładowym formatem z Binance.")
            st.stop()

        # Extract Currencies immediately to populate Sidebar
        try:
            df[['Amount_Val', 'Currency']] = df['Amount'].apply(lambda x: pd.Series(parse_amount(x)))
        except:
            st.error('Błąd odnośnie kolumny "Amount". Sprawdź, czy Twój plik CSV jest zgodny z przykładowym formatem z Binance.')
            st.stop()

        # Get unique currencies found in the CSV
        all_found_currencies = df['Currency'].dropna().unique().tolist()
        all_found_currencies.sort()

        # --- SIDEBAR CONFIGURATION (Dynamic) ---
        with st.sidebar:
            st.header("⚙️ Konfiguracja")
            
            # Tax Rate
            tax_rate_percent = st.number_input("Stawka podatku (%)", value=19.0, step=0.5)
            
            # Year Selection
            available_years = sorted(df['Date_Obj'].dt.year.unique().tolist(), reverse=True)
            selected_year = st.selectbox("Rok podatkowy", options=available_years, index=0)

            st.divider()

            # Define common FIATs to pre-select them if they exist in the file
            common_fiats = ['EUR', 'USD', 'PLN', 'GBP', 'CHF', 'JPY']
            
            # Calculate defaults: intersection of found currencies and common fiats
            default_selection = [c for c in all_found_currencies if c in common_fiats]

            st.subheader("Wybór walut FIAT")
            st.write("Zaznacz waluty, które mają być przeliczane przez NBP (odznacz krypto):")
            
            selected_fiats = st.multiselect(
                "Wykryte waluty w pliku:",
                options=all_found_currencies,
                default=default_selection
            )
            
            st.caption(f"Znaleziono w pliku łącznie: {len(all_found_currencies)} różnych walut/tokenów.")

        # --- CALCULATION LOGIC ---

        if not selected_fiats:
            st.warning("👈 Wybierz przynajmniej jedną walutę FIAT w panelu bocznym, aby rozpocząć obliczenia.")
            st.stop()

        # Filter DataFrame based on USER SELECTION (currencies and year)
        df_fiat = df[
            (df['Currency'].isin(selected_fiats)) & 
            (df['Date_Obj'].dt.year == selected_year)
        ].copy()
        
        st.success(f"Analizuję {len(df_fiat)} transakcji dla walut: {', '.join(selected_fiats)} w roku {selected_year}")

        if not df_fiat.empty:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []
            total_rows = len(df_fiat)

            for i, (index, row) in enumerate(df_fiat.iterrows()):
                # Update Progress
                progress_bar.progress((i + 1) / total_rows)
                
                # Fetch Rate
                rate, rate_date = get_nbp_rate(row['Currency'], row['Date_YMD'])
                
                # Logic for valid/invalid rate
                if rate is None:
                    # If user selected a Crypto (e.g. BTC) as FIAT, NBP will return None.
                    # We handle this gracefully.
                    status_text.text(f"Brak kursu NBP dla: {row['Currency']}")
                    pln_value = 0.0
                else:
                    status_text.text(f"Pobrano kurs dla: {row['Currency']} ({row['Date_YMD']})")
                    pln_value = row['Amount_Val'] * rate

                tax_category = "KOSZT" if row['Side'] == 'BUY' else "PRZYCHÓD"

                results.append({
                    'Data transakcji': row['Date_YMD'],
                    'Para': row['Pair'],
                    'Typ': row['Side'],
                    'Kwota': row['Amount_Val'],
                    'Waluta': row['Currency'],
                    'Kurs NBP': rate if rate else 0.0,
                    'Data kursu': rate_date,
                    'Wartość PLN': round(pln_value, 2),
                    'Kategoria': tax_category
                })
                
                time.sleep(0.05)

            status_text.text("Gotowe!")
            progress_bar.empty()

            # Results & Summary
            df_results = pd.DataFrame(results)

            total_revenue = df_results[df_results['Kategoria'] == 'PRZYCHÓD']['Wartość PLN'].sum()
            total_cost = df_results[df_results['Kategoria'] == 'KOSZT']['Wartość PLN'].sum()
            income = total_revenue - total_cost
            tax = max(0, income * (tax_rate_percent / 100.0))

            st.divider()
            st.header(f"📊 Wynik")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Przychód", f"{total_revenue:,.2f} PLN")
            c2.metric("Koszt", f"{total_cost:,.2f} PLN")
            c3.metric("Dochód", f"{income:,.2f} PLN")

            st.subheader(f"Podatek ({tax_rate_percent}%): {tax:,.2f} PLN")

            if income < 0:
                st.warning(
                    f"**Wykazano stratę podatkową: {abs(income):,.2f} PLN**\n\n"
                    "Pamiętaj, aby wykazać tę stratę w zeznaniu rocznym PIT-38."
                )

            # Warnings for missing rates
            missing_rates = df_results[df_results['Kurs NBP'] == 0.0]
            if not missing_rates.empty:
                st.warning(f"Uwaga: Dla {len(missing_rates)} transakcji nie udało się pobrać kursu NBP (wartość 0 PLN). Sprawdź, czy nie zaznaczyłeś krypto jako FIAT w sidebarze.")

            st.dataframe(df_results)

            csv_data = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("Pobierz CSV", csv_data, "pit38_krypto.csv", "text/csv")
    except:
        st.error('Wystąpił błąd. Sprawdź, czy Twój plik CSV odpowiada przykładowemu formatowi z Binance.')
else:
    # Sidebar placeholder when no file is uploaded
    with st.sidebar:
        st.header("⚙️ Konfiguracja")
        st.info("Wgraj plik CSV, aby zobaczyć opcje wyboru walut.")