import streamlit as st
import requests
import re
import plotly.express as px

st.set_page_config(page_title="AI Property Match™ | Engine", layout="wide")

# --- STATE MANAGEMENT ---
if 'property_results' not in st.session_state:
    st.session_state['property_results'] = []
if 'selected_property' not in st.session_state:
    st.session_state['selected_property'] = None

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
    
    .property-card {
        background-color: #1F2937;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- HEADER ---
st.title("🤖 AI Property Match™")
st.subheader("Financial & Lifestyle Matching Engine")

# --- THE BACKEND: API FETCH LOGIC ---
def fetch_property_gallery_api(zip_code):
    url = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
    payload = {
        "limit": 18, # Increased limit so we have plenty of properties to sort
        "offset": 0,
        "postal_code": str(zip_code),
        "status": ["for_sale", "ready_to_build"],
        "sort": { "direction": "desc", "field": "list_date" }
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
                annual_taxes = prop.get("tax_record", {}).get("property_tax", 0)
                monthly_taxes = annual_taxes / 12 if annual_taxes else 0
                address = prop.get("location", {}).get("address", {}).get("line", "Unknown Address")
                
                # NEW LOGIC: Try to grab an array of photos instead of just one
                photo_list = []
                raw_photos = prop.get("photos", [])
                if raw_photos:
                    photo_list = [p.get("href", "").replace("s.jpg", "od-w1024_h768.webp") for p in raw_photos if p.get("href")]
                else:
                    primary = prop.get("primary_photo", {}).get("href", "")
                    if primary: photo_list.append(primary.replace("s.jpg", "od-w1024_h768.webp"))
                
                # Limit to 6 photos max so we don't overwhelm the UI
                photo_list = photo_list[:6]
                
                parsed_properties.append({
                    'price': float(price),
                    'hoa': float(hoa) if hoa else 0.0,
                    'taxes': float(monthly_taxes),
                    'address': address,
                    'images': photo_list if photo_list else ["https://via.placeholder.com/400x300?text=No+Photo"]
                })
            return parsed_properties
        return []
    except Exception as e:
        return []

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

# --- ZONE 2: SMART SEARCH TABS ---
tab1, tab2, tab3 = st.tabs(["🌐 Live Area Search", "✏️ Manual Entry", "📬 Contact Info"])

target_price, target_hoa, target_taxes, display_address, display_images = 0.0, 0.0, 0.0, "", []

with tab1:
    col1, col2 = st.columns([3, 1])
    zip_input = col1.text_input("Enter Zip Code to pull newest listings:", value="92117")
    
    if col2.button("🔍 Search Area", use_container_width=True):
        with st.spinner("Connecting to Realtor DB..."):
            results = fetch_property_gallery_api(zip_input)
            if results:
                st.session_state['property_results'] = results
                st.session_state['selected_property'] = None 
            else:
                st.error("No active listings found or API quota exceeded.")

    # Render the Sorting Menu and the 3-Column Grid
    if st.session_state['property_results']:
        st.divider()
        
        # NEW: The Sorting Dropdown
        col_title, col_sort = st.columns([2, 1])
        col_title.markdown("### 🏡 Available Properties")
        sort_option = col_sort.selectbox("Sort By:", ["Newest / Relevant", "Price: Low to High", "Price: High to Low"])
        
        # Apply the sort to our stored results
        display_results = st.session_state['property_results']
        if sort_option == "Price: Low to High":
            display_results = sorted(display_results, key=lambda x: x['price'])
        elif sort_option == "Price: High to Low":
            display_results = sorted(display_results, key=lambda x: x['price'], reverse=True)
        
        cols = st.columns(3)
        for idx, prop in enumerate(display_results[:9]): # Only show top 9 to keep UI clean
            with cols[idx % 3]: 
                st.markdown('<div class="property-card">', unsafe_allow_html=True)
                st.image(prop['images'][0], use_container_width=True) # Show primary image on card
                st.markdown(f"**${prop['price']:,.0f}**")
                st.caption(prop['address'])
                
                if st.button("📊 Analyze Financials", key=f"btn_{prop['address']}", use_container_width=True):
                    st.session_state['selected_property'] = prop
                st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.caption("Bypass the API and enter property details manually.")
    col_a, col_b, col_c = st.columns(3)
    target_price = col_a.number_input("Purchase Price ($)", value=0.0, step=10000.0)
    target_taxes = col_b.number_input("Monthly Taxes ($)", value=0.0, step=100.0)
    target_hoa = col_c.number_input("Monthly HOA ($)", value=0.0, step=50.0)
    if target_price > 0: st.session_state['selected_property'] = None

with tab3:
    st.markdown("### 🔒 VIP Buyer Registration")
    with st.form("contact_form"):
        first_name = st.text_input("First Name")
        email_addr = st.text_input("Email Address")
        if st.form_submit_button("Submit Details"):
            st.success("Contact info saved.")

# --- ZONE 3: THE DASHBOARD ---
active_property = st.session_state.get('selected_property')

if active_property:
    target_price = active_property['price']
    target_taxes = active_property['taxes']
    target_hoa = active_property['hoa']
    display_address = active_property['address']
    display_images = active_property['images']

if target_price > 0:
    st.divider()
    
    if display_address:
        col_title, col_close = st.columns([4, 1])
        col_title.markdown(f"### Target Property: **{display_address}**")
        if col_close.button("✖️ Clear Selection"):
            st.session_state['selected_property'] = None
            st.rerun()
            
    # NEW: The Image Gallery (Small icons that enlarge when clicked)
    if display_images:
        st.caption("🔍 *Click any image to enlarge to full screen*")
        st.image(display_images, width=180) # Renders a horizontal row of small images
    
    # Financial Logic
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
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#F8FAFC'), margin=dict(t=0, b=0, l=0, r=0))
    fig.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
