# Crypto Tax Calculator | 🇵🇱 | Binance

## Overview

A vibe-coded Streamlit application for calculating Polish tax (**PIT-38**) for cryptocurrency transactions based on Binance transaction history CSV files. Its main feature is the integration with the National Bank of Poland (NBP) API, which allows for fetching historical exchange rates from the business day preceding each transaction.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kacperfin/crypto-tax-calculator-pl
   cd crypto-tax-calculator-pl
   ```

2. **Create and activate a virtual environment**:

   **Linux**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   **Windows**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

**Run the application**:
   ```bash
   streamlit run streamlit_app.py
   ```

## Disclaimer

This is a hobby project developed for personal use. The correctness of the calculations from a legal or tax perspective has not been verified by a professional. **Do not rely on this project for filing your taxes.** Consult with a tax advisor or accountant.