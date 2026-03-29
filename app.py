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

# --- THE NEW BACKEND: RENTCAST API INTEGRATION ---
def fetch_property_data_api(address):
    url = "https://api.rentcast.io/v1/properties"
    querystring = {"address": address}
    
    # Passing your VIP Key to the API
    headers = {
        "accept": "application/json",
        "X-Api-Key": "fd98d264e0414f7cbea42bf9936a8109"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # RentCast returns a list of matching properties, we want the first one
            if isinstance(data, list) and len(data) > 0:
                prop = data[0]
                
                # APIs format data cleanly, no regex scrubbing needed!
                # We check for price, fallback to assessed value or last sale price if it's off-market
                price = prop.get('price', prop.get('assessedValue', prop.get('lastSalePrice', 0)))
                annual_taxes = prop.get('propertyTaxes', 0)
                monthly_taxes = annual_taxes / 12 if annual_taxes else 0
                hoa = prop.get('hoaFee', 0)
                
                return {
                    'price': float(price),
                    'hoa': float(hoa),
                    'taxes': float(monthly_taxes),
                    'images': [] # Note: Free tier APIs rarely include image galleries, we omit for now to ensure speed
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
tab1, tab2, tab3 = st.tabs(["🌐 Live API Search", "✏️ Manual Entry", "📬 Contact Info"])

target_price, target_hoa, target_taxes = 0.0, 0.0, 0.0

with tab1:
    # Changed from URL input to structured Address input
    address_input = st.text_input("Enter Property Address (e.g., 3141 Erie St, San Diego, CA):")
    if st.button("Query Database") and address_input:
        with st.spinner("Connecting to Real Estate API..."):
            api_data = fetch_property_data_api(address_input)
            if api_data and api_data['price'] > 0:
                target_price = api_data['price']
                target_hoa = api_data['hoa']
                target_taxes = api_data['taxes']
                st.success("Secure connection established. Data retrieved instantly!")
            else:
                st.error("Property not found in the database. Please check the address or use Manual Entry.")

with tab2:
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=target_price, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=target_taxes, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=target_hoa, step=50.0)

with tab3:
    st.markdown("### 🔒 VIP Buyer Registration")
    st.write("Enter your information below to register your profile and receive personalized property alerts.")
    with st.form("contact_form"):
        col_first, col_last = st.columns(2)
        first_name = col_first.text_input("First Name")
        last_name = col_last.text_input("Last Name")
        phone_num = st.text_input("Phone Number")
        email_addr = st.text_input("Email Address")
        
        submit_contact = st.form_submit_button("Submit Details")
        if submit_contact:
            if first_name and last_name and phone_num and email_addr:
                st.success(f"Success! We've saved your contact info, {first_name}.")
            else:
                st.error("Please fill out all contact fields.")

# --- ZONE 3: THE DASHBOARD ---
if target_price > 0:
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

    st.markdown("<br>", unsafe_allow_html=True) 
    
    chart_data = {
        "Category": ["Principal & Interest", "Property Taxes", "Insurance", "HOA"],
        "Amount": [monthly_pi, target_taxes, monthly_insurance, target_hoa]
    }
    fig = px.pie(chart_data, values="Amount", names="Category", hole=0.6, color_discrete_sequence=['#3B82F6', '#60A5FA', '#93C5FD', '#1E3A8A'])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#F8FAFC'))
    fig.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
