import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re
import plotly.express as px

st.set_page_config(page_title="AI Property Match™ | Engine", layout="wide")

# --- CUSTOM CSS INJECTION (THE WEB DESIGN UPGRADE) ---
# This block forces Streamlit to look like a custom web app
# --- CUSTOM CSS INJECTION (THE WEB DESIGN UPGRADE) ---
custom_css = """
<style>
    /* 1. Main app background color */
    .stApp {
        background-color: #F9F9F7 !important;
    }
    
    /* 2. Style the Sidebar and FORCE dark text inside it */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 2px solid #E5E9EA;
    }
    
    /* 3. Create the "Bubbles" (Rounded Cards for Metrics) */
    [data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E9EA;
        padding: 15px 20px;
        border-radius: 16px; 
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); 
    }
    
    /* 4. The Dark Mode Override: Force all text, headers, and labels to be dark slate */
    h1, h2, h3, h4, h5, h6, p, label, div, span, .stMarkdown {
        color: #1E293B !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 5. Fix the input box backgrounds so they don't turn black in dark mode */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #E5E9EA !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- HEADER ---
st.title("🤖 AI Property Match™")
st.subheader("Financial & Lifestyle Matching Engine")

def clean_financial_string(raw_string):
    if not raw_string or raw_string in ["0", "Not Found"]: return 0.0
    try: return float(re.sub(r'[^\d]', '', raw_string))
    except ValueError: return 0.0

# --- THE MASTER SCRAPER ROUTER ---
def scrape_property_data(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    try:
        response = scraper.get(url, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.content, 'html.parser')
        
        image_meta = soup.find("meta", property="og:image")
        main_image = image_meta["content"] if image_meta else None
        
        image_list = []
        if main_image: image_list.append(main_image)
            
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and ('.jpg' in src or '.jpeg' in src) and 'logo' not in src.lower():
                if src not in image_list: image_list.append(src)
                    
        final_images = image_list[:5]

        if "redfin.com" in url: data = parse_redfin(soup)
        elif "zillow.com" in url: data = parse_zillow(soup)
        else: return None 
            
        if data: data['images'] = final_images
        return data
    except Exception: return None

def parse_redfin(soup):
    price_elem = soup.find('div', class_='stat-block price-section')
    raw_price = price_elem.text if price_elem else "0"
    hoa_label = soup.find(string=lambda text: text and 'HOA Dues' in text)
    raw_hoa = hoa_label.find_next('span').text if hoa_label else "0"
    tax_label = soup.find(string=lambda text: text and 'Property Taxes' in text)
    raw_tax = tax_label.find_next('span').text if tax_label else "0"
    return {'price': clean_financial_string(raw_price), 'hoa': clean_financial_string(raw_hoa), 'taxes': round(clean_financial_string(raw_tax) / 12, 2)}

def parse_zillow(soup):
    price_elem = soup.find('span', {'data-testid': 'price'})
    raw_price = price_elem.text if price_elem else "0"
    return {'price': clean_financial_string(raw_price), 'hoa': 0.0, 'taxes': 0.0}

# --- ZONE 1: THE AI MATCHING PROFILE (Sidebar) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Ideal_home_icon.svg/1024px-Ideal_home_icon.svg.png", width=50) # Placeholder logo
st.sidebar.header("The Buyer Profile")

# Expander 1: Financials
with st.sidebar.expander("💰 Financial Constraints", expanded=True):
    annual_income = st.number_input("Gross Annual Income ($)", value=120000, step=5000)
    monthly_debts = st.number_input("Total Monthly Debt ($)", value=500, step=100)
    target_range = st.slider("Target Payment Range ($)", 1000, 15000, (3000, 5000), step=100)
    down_payment_pct = st.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01)
    display_rate = st.number_input("Custom Interest Rate (%)", value=6.500, step=0.125, format="%.3f")
    interest_rate = display_rate / 100 

# Expander 2: Lifestyle (NEW PATH A FEATURES)
with st.sidebar.expander("🏡 Lifestyle Preferences", expanded=True):
    st.caption("These data points will feed the Phase 2 Machine Learning Recommendation Engine.")
    target_zips = st.multiselect("Preferred Zip Codes", ["92117", "92109", "92101", "92104", "92037"], default=["92117", "92109"])
    property_type = st.selectbox("Property Type", ["Single Family Home", "Townhouse", "Condo", "Multi-Family"])
    min_beds = st.number_input("Minimum Bedrooms", value=3, step=1)
    must_haves = st.multiselect("Must Haves", ["Large Yard", "Pool", "Garage", "Ocean View", "Walkable Neighborhood"])

# --- ZONE 2: SMART SEARCH TABS ---
tab1, tab2 = st.tabs(["🌐 AI Auto-Fill", "✏️ Manual Entry"])

target_price, target_hoa, target_taxes, property_images = 0.0, 0.0, 0.0, []

with tab1:
    url_input = st.text_input("Paste Listing URL (Run locally to bypass firewalls):")
    if st.button("Analyze Property") and url_input:
        with st.spinner("Extracting data and image gallery..."):
            scraped_data = scrape_property_data(url_input)
            if scraped_data and scraped_data['price'] > 0:
                target_price, target_hoa, target_taxes, property_images = scraped_data['price'], scraped_data['hoa'], scraped_data['taxes'], scraped_data.get('images', [])
                st.success("Property data extracted!")
            else:
                st.error("Extraction failed. Please use Manual Entry.")

with tab2:
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=target_price, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=target_taxes, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=target_hoa, step=50.0)

# --- ZONE 3: THE DASHBOARD ---
if target_price > 0:
    st.divider()
    
    if property_images:
        st.image(property_images, width=220)
        st.divider()
    
    if target_taxes == 0.0: target_taxes = (target_price * 0.012) / 12 
    monthly_insurance = (target_price * 0.0025) / 12
    down_payment_amount = target_price * down_payment_pct
    loan_amount = target_price - down_payment_amount
    
    r = interest_rate / 12
    monthly_pi = loan_amount * (r * (1 + r)**360) / ((1 + r)**360 - 1) if loan_amount > 0 else 0
    total_piti = monthly_pi + target_taxes + monthly_insurance + target_hoa
    
    st.markdown("### 📊 Affordability Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Purchase Price", f"${target_price:,.0f}")
    col2.metric(f"Down Pmt ({down_payment_pct*100:.0f}%)", f"${down_payment_amount:,.0f}")
    col3.metric("Monthly Payment", f"${total_piti:,.0f}")
    
    if target_range[0] <= total_piti <= target_range[1]:
        col4.metric("Budget Match", "✅ Approved")
    else:
        col4.metric("Budget Match", "🚨 Denied")

    st.markdown("<br>", unsafe_allow_html=True) # Adds a little spacing
    
    # Modernized Chart Colors
    chart_data = {
        "Category": ["Principal & Interest", "Property Taxes", "Insurance", "HOA"],
        "Amount": [monthly_pi, target_taxes, monthly_insurance, target_hoa]
    }
    fig = px.pie(chart_data, values="Amount", names="Category", hole=0.6, color_discrete_sequence=['#1E293B', '#3B82F6', '#93C5FD', '#E2E8F0'])
    fig.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
