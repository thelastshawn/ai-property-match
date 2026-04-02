import streamlit as st
import requests
import math
import plotly.express as px

st.set_page_config(page_title="AI Property Match™ | Engine", layout="wide")

# --- STATE MANAGEMENT ---
if 'property_results' not in st.session_state:
    st.session_state['property_results'] = []
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 0

# --- CUSTOM CSS INJECTION (MIDNIGHT SAPPHIRE) ---
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
    .property-card { background-color: #1F2937; padding: 10px; border-radius: 10px; border: 1px solid #374151; margin-bottom: 15px; }
    .disclaimer { font-size: 0.8em; color: #9CA3AF !important; font-style: italic; margin-top: 10px;}
    
    .pagination-text { text-align: center; color: #9CA3AF; font-size: 1.0em; padding-bottom: 5px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- HEADER ---
st.title("🤖 AI Property Match™")
st.subheader("Financial & Lifestyle Matching Engine")

# --- THE BACKEND: API FETCH WITH NEW FILTERS ---
def fetch_property_gallery_api(zip_code, beds, baths, min_sqft, max_hoa):
    url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
    payload = {
        "limit": 100, 
        "offset": 0,
        "postal_code": str(zip_code),
        "status": ["for_sale", "ready_to_build", "pending"], 
        "sort": { "direction": "desc", "field": "list_date" },
        "beds_min": int(beds),
        "baths_min": int(baths),
        "sqft_min": int(min_sqft)
    }
    headers = {
        "x-rapidapi-key": "ad67d0a64dmsh514c74e7fcdc0a0p13b2fbjsnd81dec4f00d5",
        "x-rapidapi-host": "realty-in-us.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("home_search", {}).get("results", [])
            
            parsed_properties = []
            for prop in results:
                price = prop.get("list_price", 0)
                if not price: continue 
                
                hoa = prop.get("description", {}).get("hoa", 0)
                if max_hoa > 0 and (hoa and hoa > max_hoa): continue 
                
                annual_taxes = prop.get("tax_record", {}).get("property_tax", 0)
                monthly_taxes = annual_taxes / 12 if annual_taxes else 0
                address = prop.get("location", {}).get("address", {}).get("line", "Unknown Address")
                home_type = prop.get("description", {}).get("type", "Home").replace("_", " ").title()
                
                photo_list = []
                raw_photos = prop.get("photos", [])
                if raw_photos:
                    photo_list = [p.get("href", "").replace("s.jpg", "od-w1024_h768.webp") for p in raw_photos if p.get("href")]
                else:
                    primary = prop.get("primary_photo", {}).get("href", "")
                    if primary: photo_list.append(primary.replace("s.jpg", "od-w1024_h768.webp"))
                
                parsed_properties.append({
                    'price': float(price),
                    'hoa': float(hoa) if hoa else 0.0,
                    'taxes': float(monthly_taxes),
                    'address': address,
                    'type': home_type,
                    'images': photo_list[:6] if photo_list else ["https://via.placeholder.com/400x300?text=No+Photo"]
                })
            return parsed_properties
        return []
    except Exception as e:
        return []

# --- ZONE 1: THE AI MATCHING PROFILE (Sidebar) ---
st.sidebar.header("The Buyer Profile")

with st.sidebar.expander("💰 Financial Constraints", expanded=True):
    annual_income = st.number_input("Gross Annual Income ($)", value=120000, step=5000)
    target_range = st.slider("Target Payment Range ($)", 1000, 15000, (3000, 5000), step=100)
    down_payment_pct = st.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01)
    
    # NEW: Added Tooltip to Loan Program
    loan_program = st.selectbox(
        "Loan Program", 
        [
            "30-Year Fixed (Conventional) ~ 6.48%",
            "15-Year Fixed (Conventional) ~ 5.80%",
            "30-Year Fixed (FHA) ~ 6.12%",
            "30-Year Fixed (VA) ~ 5.86%",
            "5/1 ARM ~ 6.00%",
            "Custom Rate"
        ],
        help="Conventional is standard. FHA helps buyers with lower credit or down payments. VA is exclusively for military veterans. 15-Year builds equity faster but requires a higher monthly payment."
    )
    
    if loan_program == "Custom Rate":
        display_rate = st.number_input("Custom Interest Rate (%)", value=6.500, step=0.125, format="%.3f")
        loan_term_years = st.selectbox("Loan Term", [30, 15], index=0)
    else:
        loan_term_years = 15 if "15-Year" in loan_program else 30
        if "30-Year Fixed (Conventional)" in loan_program: display_rate = 6.48
        elif "15-Year Fixed (Conventional)" in loan_program: display_rate = 5.80
        elif "FHA" in loan_program: display_rate = 6.12
        elif "VA" in loan_program: display_rate = 5.86
        elif "5/1 ARM" in loan_program: display_rate = 6.00
        st.info(f"Applying {display_rate}% over {loan_term_years} years.")
        
    interest_rate = display_rate / 100 

with st.sidebar.expander("🏡 Property Filters", expanded=True):
    # NEW: Added Tooltips to all Property Filters
    min_beds = st.number_input("Minimum Bedrooms", value=3, step=1, help="The minimum number of sleeping rooms you need.")
    min_baths = st.number_input("Minimum Bathrooms", value=2, step=1, help="Includes both full and half bathrooms.")
    min_sqft = st.number_input("Minimum SqFt", value=1200, step=100, help="Total livable interior space. For reference, a standard 2-car garage is about 400 SqFt.")
    max_hoa_fee = st.number_input("Max Monthly HOA ($)", value=500, step=50, help="Homeowners Association fees. Condos and townhomes typically have higher HOAs to cover exterior maintenance, pools, and amenities.")
