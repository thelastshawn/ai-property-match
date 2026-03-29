import streamlit as st
import requests
import re
import plotly.express as px

st.set_page_config(page_title="AI Property Match™ | Engine", layout="wide")

# --- CUSTOM CSS INJECTION (MIDNIGHT SAPPHIRE THEME) ---
custom_css = """
<style>
    .stApp { background-color: #0B0F19 !important; }
    [data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #1F2937; }
    [data-testid="metric-container"] {
        background-color: #1E3A8A !important; 
        border: 1px solid #2563EB; padding: 15px 20px; border-radius: 16px; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); 
    }
    h1, h2, h3, h4, h5, h6, p, label, div, span, .stMarkdown {
        color: #F8FAFC !important; font-family: 'Helvetica Neue', sans-serif;
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #1F2937 !important; color: #F8FAFC !important; border: 1px solid #374151 !important;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { font-weight: bold; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- HEADER ---
st.title("🤖 AI Property Match™")
st.subheader("Financial & Lifestyle Matching Engine")

# --- THE NEW BACKEND: REALTY IN US (RAPIDAPI) INTEGRATION ---
def fetch_property_data_api(zip_code):
    url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
    
    # Your exact payload, adjusted to use the user's zip code input
    payload = {
        "limit": 10, # We only need the top few to grab the newest one
        "offset": 0,
        "postal_code": str(zip_code),
        "status": ["for_sale", "ready_to_build"],
        "sort": {
            "direction": "desc",
            "field": "list_date"
        }
    }
    
    headers = {
        "x-rapidapi-key": "ad67d0a64dmsh514c74e7fcdc0a0p13b2fbjsnd81dec4f00d5",
        "x-rapidapi-host": "realty-in-us.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    
    try:
        # Note: We use requests.post() here instead of .get() based on the API docs
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Navigate the nested JSON structure the API returns
            results = data.get("data", {}).get("home_search", {}).get("results", [])
            
            if results and len(results) > 0:
                prop = results[0] # Grab the newest listing
                
                # Extract the data safely
                price = prop.get("list_price", 0)
                hoa = prop.get("description", {}).get("hoa", 0)
                
                # Property tax is often nested in tax_record
                annual_taxes = prop.get("tax_record", {}).get("property_tax", 0)
                monthly_taxes = annual_taxes / 12 if annual_taxes else 0
                
                # Grab the address and the primary photo to display
                address = prop.get("location", {}).get("address", {}).get("line", "Unknown Address")
                photo_url = prop.get("primary_photo", {}).get("href", "")
                
                return {
                    'price': float(price),
                    'hoa': float(hoa) if hoa else 0.0,
                    'taxes': float(monthly_taxes),
                    'address': address,
                    'image': photo_url.replace("s.jpg", "od-w1024_h768.webp") if photo_url else None # Attempts to grab higher res
                }
        return None
    except Exception as e:
        return None

# --- ZONE 1: THE AI MATCHING PROFILE (Sidebar) ---
st.sidebar.header("The Buyer Profile")

with st.sidebar.expander("💰 Financial Constraints", expanded=True):
    annual_income = st.number_input("Gross Annual Income ($)", value=120000, step=5000)
    monthly_debts = st.number_input("Total Monthly Debt ($)", value=500, step=100)
    target_range = st.slider("Target Payment Range ($)", 1000, 15000, (3000, 5000), step=100)
    down_payment_pct = st.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01)
    display_rate = st.number_input("Custom Interest Rate (%)", value=6.500, step=0.125, format="%.3f")
    interest_rate = display_rate / 100 

with st.sidebar.expander("🏡 Lifestyle Preferences", expanded=True):
    target_zips = st.multiselect("Preferred Zip Codes", ["92117", "92109", "92101", "92104", "92037"], default=["92117", "92109"])
    property_type = st.selectbox("Property Type", ["Single Family Home", "Townhouse", "Condo", "Multi-Family"])
    min_beds = st.number_input("Minimum Bedrooms", value=3, step=1)
    must_haves = st.multiselect("Must Haves", ["Large Yard", "Pool", "Garage", "Ocean View", "Walkable Neighborhood"])

# --- ZONE 2: SMART SEARCH & LEAD CAPTURE TABS ---
tab1, tab2, tab3 = st.tabs(["🌐 Live Local Search", "✏️ Manual Entry", "📬 Contact Info"])

target_price, target_hoa, target_taxes, display_address, display_image = 0.0, 0.0, 0.0, "", None

with tab1:
    # Changed input to Zip Code to match the API requirements
    zip_input = st.text_input("Enter Zip Code to pull the newest listing:", value="92117")
    if st.button("Query Database") and zip_input:
        with st.spinner("Connecting to Realtor DB..."):
            api_data = fetch_property_data_api(zip_input)
            if api_data and api_data['price'] > 0:
                target_price = api_data['price']
                target_hoa = api_data['hoa']
                target_taxes = api_data['taxes']
                display_address = api_data['address']
                display_image = api_data['image']
                st.success("Secure connection established. Newest listing retrieved!")
            else:
                st.error("Could not find active listings in that Zip Code, or API quota exceeded.")

with tab2:
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=target_price, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=target_taxes, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=target_hoa, step=50.0)

with tab3:
    st.markdown("### 🔒 VIP Buyer Registration")
