import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import plotly.express as px

st.set_page_config(page_title="AI Property Match™ | Financial Readiness", layout="wide")
st.title("🤖 AI Property Match™")
st.subheader("Financial Readiness & Affordability Engine")

if 'authorized' not in st.session_state:
    st.session_state['authorized'] = False

def clean_financial_string(raw_string):
    if not raw_string or raw_string in ["0", "Not Found"]: return 0.0
    try: return float(re.sub(r'[^\d]', '', raw_string))
    except ValueError: return 0.0

# --- THE NEW MASTER SCRAPER ROUTER ---
def scrape_property_data(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    try:
        response = scraper.get(url, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Grab the universal Hero Image (og:image)
        image_meta = soup.find("meta", property="og:image")
        property_image = image_meta["content"] if image_meta else None

        # 2. Route to the correct website logic
        if "redfin.com" in url:
            return parse_redfin(soup, property_image)
        elif "zillow.com" in url:
            return parse_zillow(soup, property_image)
        else:
            return None # Unsupported site
            
    except Exception:
        return None

# --- SITE-SPECIFIC PARSERS ---
def parse_redfin(soup, image_url):
    price_elem = soup.find('div', class_='stat-block price-section')
    raw_price = price_elem.text if price_elem else "0"
    
    hoa_label = soup.find(string=lambda text: text and 'HOA Dues' in text)
    raw_hoa = hoa_label.find_next('span').text if hoa_label else "0"
    
    tax_label = soup.find(string=lambda text: text and 'Property Taxes' in text)
    raw_tax = tax_label.find_next('span').text if tax_label else "0"
    
    return {
        'price': clean_financial_string(raw_price),
        'hoa': clean_financial_string(raw_hoa),
        'taxes': round(clean_financial_string(raw_tax) / 12, 2),
        'image': image_url
    }

def parse_zillow(soup, image_url):
    # ZILLOW PLACEHOLDER: Zillow's HTML changes constantly and blocks bots heavily.
    # This is a basic attempt to find their standard price tag.
    price_elem = soup.find('span', {'data-testid': 'price'})
    raw_price = price_elem.text if price_elem else "0"
    
    return {
        'price': clean_financial_string(raw_price),
        'hoa': 0.0, # Harder to scrape reliably on Zillow
        'taxes': 0.0, # Will trigger our 1.2% San Diego fallback
        'image': image_url
    }

# --- ZONE 1: BUYER FINANCIAL PROFILE ---
st.sidebar.header("📊 Buyer Financial Profile")
annual_income = st.sidebar.number_input("Gross Annual Income ($)", value=120000, step=5000)
monthly_debts = st.sidebar.number_input("Total Monthly Debt ($)", value=500, step=100)

st.sidebar.divider()
st.sidebar.subheader("Target Goals")
target_range = st.sidebar.slider("Target Payment Range ($)", 1000, 15000, (3000, 5000), step=100)
down_payment_pct = st.sidebar.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01)
interest_rate = st.sidebar.slider("Custom Interest Rate %", 0.01, 0.10, 0.065, 0.001)

# --- ZONE 2: SMART SEARCH TABS ---
tab1, tab2 = st.tabs(["🌐 AI Auto-Fill (Redfin & Zillow)", "✏️ Manual Entry"])

target_price = 0.0
target_hoa = 0.0
target_taxes = 0.0
property_image = None

with tab1:
    url_input = st.text_input("Paste Listing URL (Redfin or Zillow):")
    if st.button("Analyze Property") and url_input:
        with st.spinner("Extracting data and images..."):
            scraped_data = scrape_property_data(url_input)
            if scraped_data and scraped_data['price'] > 0:
                target_price = scraped_data['price']
                target_hoa = scraped_data['hoa']
                target_taxes = scraped_data['taxes']
                property_image = scraped_data['image']
                st.success("Property data successfully extracted!")
            else:
                st.error("Extraction failed. The site may be blocking automated requests. Please use Manual Entry.")

with tab2:
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=target_price, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=target_taxes, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=target_hoa, step=50.0)

# --- ZONE 3: LEAD CAPTURE ---
if target_price > 0 and not st.session_state['authorized']:
    st.divider()
    st.info("🔒 **Unlock Your Full Financial Breakdown**")
    with st.form("lead_capture_form"):
        st.write("Authorize to view personalized affordability metrics.")
        client_name = st.text_input("Full Name")
        client_email = st.text_input("Email Address")
        submitted = st.form_submit_button("Unlock Dashboard")
        if submitted and client_name and client_email:
            st.session_state['authorized'] = True
            st.rerun()

# --- ZONE 4: THE DASHBOARD ---
if target_price > 0 and st.session_state['authorized']:
    st.divider()
    
    # NEW: Display the Property Image!
    if property_image:
        st.image(property_image, use_container_width=True, caption="Target Property")
    
    if target_taxes == 0.0: target_taxes = (target_price * 0.012) / 12 
    monthly_insurance = (target_price * 0.0025) / 12
    down_payment_amount = target_price * down_payment_pct
    loan_amount = target_price - down_payment_amount
    
    r = interest_rate / 12
    monthly_pi = loan_amount * (r * (1 + r)**360) / ((1 + r)**360 - 1) if loan_amount > 0 else 0
    total_piti = monthly_pi + target_taxes + monthly_insurance + target_hoa
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Purchase Price", f"${target_price:,.0f}")
    col2.metric(f"Down Payment ({down_payment_pct*100:.0f}%)", f"${down_payment_amount:,.0f}")
    col3.metric("Est. Monthly Payment", f"${total_piti:,.0f}")
    
    if target_range[0] <= total_piti <= target_range[1]:
        col4.metric("Target Match", "✅ In Range")
    else:
        col4.metric("Target Match", "🚨 Out Range")

    st.subheader("Payment Breakdown")
    chart_data = {
        "Category": ["Principal & Interest", "Property Taxes", "Homeowners Insurance", "HOA Dues"],
        "Amount": [monthly_pi, target_taxes, monthly_insurance, target_hoa]
    }
    fig = px.pie(chart_data, values="Amount", names="Category", hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)
