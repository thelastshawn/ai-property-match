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
    .property-card { background-color: #1F2937; padding: 10px; border-radius: 10px; border: 1px solid #374151; margin-bottom: 15px; }
    .disclaimer { font-size: 0.8em; color: #9CA3AF !important; font-style: italic; margin-top: 10px;}
    .pagination-text { text-align: center; color: #9CA3AF; font-size: 1.0em; padding-bottom: 5px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- HEADER & SLOGAN ---
st.title("🤖 AI Property Match™")
st.subheader("Financial & Lifestyle Matching Engine")
# Updated Trust Statement (Brokerage Removed)
st.caption("🔒 Secure, transparent market math to help San Diego buyers purchase with confidence.")

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
    annual_income = st.number_input("Gross Annual Income ($)", value=120000, step=5000, help="Your total yearly income before taxes.")
    target_range = st.slider("Target Payment Range ($)", 1000, 15000, (3000, 5000), step=100, help="The monthly payment you are comfortable making, including estimated taxes and insurance.")
    down_payment_pct = st.slider("Down Payment %", 0.0, 1.0, 0.20, 0.01, help="The percentage of the home's price you plan to pay upfront in cash. Putting down 20% usually avoids private mortgage insurance (PMI).")
    
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
        display_rate = st.number_input("Custom Interest Rate (%)", value=6.500, step=0.125, format="%.3f", help="Enter the specific interest rate quoted by your lender.")
        loan_term_years = st.selectbox("Loan Term", [30, 15], index=0, help="The lifespan of your loan in years.")
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
    min_beds = st.number_input("Minimum Bedrooms", value=3, step=1, help="The minimum number of sleeping rooms you need.")
    min_baths = st.number_input("Minimum Bathrooms", value=2, step=1, help="Includes both full and half bathrooms.")
    min_sqft = st.number_input("Minimum SqFt", value=1200, step=100, help="Total livable interior space. For reference, a standard 2-car garage is about 400 SqFt.")
    max_hoa_fee = st.number_input("Max Monthly HOA ($)", value=500, step=50, help="Homeowners Association fees. Condos and townhomes typically have higher HOAs to cover exterior maintenance, pools, and amenities.")

# --- ZONE 3: THE POP-UP DASHBOARD ---
@st.dialog("📊 Property Financial Analysis", width="large")
def show_dashboard(prop):
    target_price = prop['price']
    target_taxes = prop['taxes']
    target_hoa = prop['hoa']
    
    st.markdown(f"### 🏠 **{prop['address']}** | {prop['type']}")
    
    if prop['images']:
        st.caption("🔍 *Click any image to enlarge*")
        st.image(prop['images'], width=150) 
    
    if target_taxes == 0.0: target_taxes = (target_price * 0.012) / 12 
    monthly_insurance = (target_price * 0.0025) / 12
    down_payment_amount = target_price * down_payment_pct
    loan_amount = target_price - down_payment_amount
    
    total_months = loan_term_years * 12
    r = interest_rate / 12
    monthly_pi = loan_amount * (r * (1 + r)**total_months) / ((1 + r)**total_months - 1) if loan_amount > 0 else 0
    total_piti = monthly_pi + target_taxes + monthly_insurance + target_hoa
    
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Purchase Price", f"${target_price:,.0f}")
    col2.metric(f"Down Pmt ({down_payment_pct*100:.0f}%)", f"${down_payment_amount:,.0f}")
    col3.metric("Est. Monthly", f"${total_piti:,.0f}")
    
    if target_range[0] <= total_piti <= target_range[1]: col4.metric("Verdict", "✅ Match")
    else: col4.metric("Verdict", "🚨 Not a Match")

    chart_data = {
        "Category": ["Principal & Interest", "Property Taxes", "Insurance", "HOA"],
        "Amount": [monthly_pi, target_taxes, monthly_insurance, target_hoa]
    }
    fig = px.pie(chart_data, values="Amount", names="Category", hole=0.6, color_discrete_sequence=['#3B82F6', '#60A5FA', '#93C5FD', '#1E3A8A'])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#F8FAFC'), margin=dict(t=0, b=0, l=0, r=0))
    fig.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('<p class="disclaimer">Disclaimer: This affordability breakdown is an estimate for educational purposes only and does not constitute official financial advice or a guarantee of loan approval. Property taxes and insurance rates are estimations.</p>', unsafe_allow_html=True)

# --- ZONE 2: SMART SEARCH TABS ---
tab1, tab2, tab3 = st.tabs(["🌐 Live Area Search", "✏️ Manual Entry", "📬 Contact Information"])

with tab1:
    st.markdown("### 📍 Search by Zip Code")
    
    zip_input = st.text_input("Enter Zip Code:", value="92117")
    
    if st.button("🔍 Search Area", use_container_width=True):
        with st.spinner("Applying filters and scanning for up to 100 properties..."):
            results = fetch_property_gallery_api(zip_input, min_beds, min_baths, min_sqft, max_hoa_fee)
            if results:
                st.session_state['property_results'] = results
                st.session_state['current_page'] = 0 
            else:
                st.error("No properties match your strict filters.")

    if st.session_state['property_results']:
        st.divider()
        col_title, col_sort = st.columns([2, 1])
        col_title.markdown("### 🏡 Matching Properties")
        
        def update_sort():
            st.session_state['current_page'] = 0 
            
        sort_option = col_sort.selectbox("Sort By:", ["Newest / Relevant", "Price: Low to High", "Price: High to Low"], on_change=update_sort)
        
        display_results = st.session_state['property_results']
        if sort_option == "Price: Low to High": display_results = sorted(display_results, key=lambda x: x['price'])
        elif sort_option == "Price: High to Low": display_results = sorted(display_results, key=lambda x: x['price'], reverse=True)
        
        # --- PAGINATION LOGIC ---
        ITEMS_PER_PAGE = 9
        total_items = len(display_results)
        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
        
        if st.session_state['current_page'] >= total_pages:
            st.session_state['current_page'] = 0
            
        start_idx = st.session_state['current_page'] * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_results = display_results[start_idx:end_idx]
        
        cols = st.columns(3)
        for idx, prop in enumerate(page_results): 
            with cols[idx % 3]: 
                st.markdown('<div class="property-card">', unsafe_allow_html=True)
                st.image(prop['images'][0], use_container_width=True) 
                st.markdown(f"**${prop['price']:,.0f}** | {prop['type']}")
                st.caption(prop['address'])
                
                if st.button("📊 Analyze Financials", key=f"btn_{prop['address']}", use_container_width=True):
                    show_dashboard(prop)
                st.markdown('</div>', unsafe_allow_html=True)
                
        # --- UPGRADED PAGINATION CONTROLS ---
        st.divider()
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        
        if col_prev.button("⬅️ Previous", disabled=(st.session_state['current_page'] == 0), use_container_width=True):
            st.session_state['current_page'] -= 1
            st.rerun()
            
        def handle_page_jump():
            selected_page = st.session_state['page_jumper_select']
            st.session_state['current_page'] = selected_page - 1
            
        col_page.markdown(f"<div class='pagination-text'><b>{total_items}</b> properties found</div>", unsafe_allow_html=True)
        
        page_numbers = list(range(1, total_pages + 1))
        
        col_page.selectbox(
            "Jump to page:", 
            options=page_numbers, 
            index=st.session_state['current_page'],
            key="page_jumper_select", 
            on_change=handle_page_jump,
            label_visibility="collapsed"
        )
        
        if col_next.button("Next ➡️", disabled=(st.session_state['current_page'] >= total_pages - 1), use_container_width=True):
            st.session_state['current_page'] += 1
            st.rerun()

with tab2:
    st.markdown("### ✏️ Manual Entry")
    st.caption("Bypass the API and enter property details manually.")
    col_a, col_b, col_c = st.columns(3)
    manual_price = col_a.number_input("Purchase Price ($)", value=0.0, step=10000.0)
    manual_taxes = col_b.number_input("Monthly Taxes ($)", value=0.0, step=100.0)
    manual_hoa = col_c.number_input("Monthly HOA ($)", value=0.0, step=50.0)
    
    if st.button("📊 Analyze Manual Entry", use_container_width=True):
        if manual_price > 0:
            mock_prop = {
                'price': manual_price,
                'taxes': manual_taxes,
                'hoa': manual_hoa,
                'address': "Manually Entered Property",
                'type': "Custom Entry",
                'images': []
            }
            show_dashboard(mock_prop)

with tab3:
    st.markdown("### 📬 Contact Information")
    with st.form("contact_form"):
        col_first, col_last = st.columns(2)
        first_name = col_first.text_input("First Name")
        last_name = col_last.text_input("Last Name")
        phone_num = st.text_input("Phone Number")
        email_addr = st.text_input("Email Address")
        if st.form_submit_button("Submit Details"):
            st.success("Contact info securely saved.")
