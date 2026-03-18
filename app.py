import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import plotly.express as px

# --- PAGE SETUP & BRANDING ---
st.set_page_config(page_title="AI Property Match™ | Financial Readiness", layout="wide")
st.title("🤖 AI Property Match™")
st.subheader("Financial Readiness & Affordability Engine")

# --- THE SCRAPER ENGINE ---
def clean_financial_string(raw_string):
    if not raw_string or raw_string in ["0", "Not Found"]: return 0.0
    try: return float(re.sub(r'[^\d]', '', raw_string))
    except ValueError: return 0.0

def scrape_full_property_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price_elem = soup.find('div', class_='stat-block price-section')
        raw_price = price_elem.text if price_elem else "0"
        
        hoa_label = soup.find(string=lambda text: text and 'HOA Dues' in text)
        raw_hoa = hoa_label.find_next('span').text if hoa_label else "0"
        
        tax_label = soup.find(string=lambda text: text and 'Property Taxes' in text)
        raw_tax = tax_label.find_next('span').text if tax_label else "0"
        
        return {
            'price': clean_financial_string(raw_price),
            'hoa': clean_financial_string(raw_hoa),
            'taxes': round(clean_financial_string(raw_tax) / 12, 2)
        }
    except Exception:
        return None

# --- ZONE 1: BUYER FINANCIAL PROFILE (Sidebar) ---
st.sidebar.header("📊 Buyer Financial Profile")
st.sidebar.caption("Adjust inputs to match financial readiness.")
annual_income = st.sidebar.number_input("Gross Annual Income ($)", value=120000, step=5000)
monthly_debts = st.sidebar.number_input("Total Monthly Debt ($)", value=500, step=100)
down_payment_pct = st.sidebar.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01)
interest_rate = st.sidebar.slider("Interest Rate %", 0.01, 0.10, 0.065, 0.001)

# --- ZONE 2: SMART SEARCH TABS ---
tab1, tab2 = st.tabs(["🌐 AI Auto-Fill (Paste URL)", "✏️ Manual Entry"])

target_price = 0.0
target_hoa = 0.0
target_taxes = 0.0

with tab1:
    url_input = st.text_input("Paste Redfin Listing URL for instant analysis:")
    if st.button("Analyze Property") and url_input:
        with st.spinner("AI Property Match™ is extracting data..."):
            scraped_data = scrape_full_property_data(url_input)
            if scraped_data and scraped_data['price'] > 0:
                target_price = scraped_data['price']
                target_hoa = scraped_data['hoa']
                target_taxes = scraped_data['taxes']
                st.success("Property data successfully extracted!")
            else:
                st.error("Extraction failed. Please check the URL or use Manual Entry.")

with tab2:
    st.caption("Bypass the automated scraper and enter property details manually.")
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=target_price, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=target_taxes, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=target_hoa, step=50.0)

# --- ZONE 3 & 4: THE READINESS DASHBOARD ---
if target_price > 0:
    st.divider()
    
    # Financial Logic & Local Assumptions
    if target_taxes == 0.0: target_taxes = (target_price * 0.012) / 12 # 1.2% Default Baseline
    monthly_insurance = (target_price * 0.0025) / 12
    down_payment = target_price * down_payment_pct
    loan_amount = target_price - down_payment
    r = interest_rate / 12
    monthly_pi = loan_amount * (r * (1 + r)**360) / ((1 + r)**360 - 1) if loan_amount > 0 else 0
    
    total_piti = monthly_pi + target_taxes + monthly_insurance + target_hoa
    dti_ratio = (total_piti + monthly_debts) / (annual_income / 12)
    
    # Dashboard KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Purchase Price", f"${target_price:,.0f}")
    col2.metric("Est. Monthly Payment", f"${total_piti:,.0f}")
    
    if dti_ratio <= 0.43:
        col3.metric("Readiness Status (DTI)", f"{dti_ratio * 100:.1f}%", "Likely Approved")
    else:
        col3.metric("Readiness Status (DTI)", f"{dti_ratio * 100:.1f}%", "-Likely Denied") 

    # Visual Breakdown
    st.subheader("Monthly Payment Breakdown")
    chart_data = {
        "Category": ["Principal & Interest", "Property Taxes", "Homeowners Insurance", "HOA Dues"],
        "Amount": [monthly_pi, target_taxes, monthly_insurance, target_hoa]
    }
    # Using a modern, tech-focused color palette for the chart
    fig = px.pie(chart_data, values="Amount", names="Category", hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
    st.plotly_chart(fig, use_container_width=True)