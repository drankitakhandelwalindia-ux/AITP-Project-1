import gradio as gr
import requests
import pandas as pd
from supabase import create_client, Client

# --- 1. CONFIGURATION & ASSETS ---
SUPABASE_URL = "https://fjxgdnclunhwapsjxzvv.supabase.co"
SUPABASE_KEY = "sb_publishable_w5mYvOX05S5yasnESIGThA_QbVBhmaU"
LOGO_URL = "https://raw.githubusercontent.com/drankitakhandelwalindia-ux/AITP-Project-1/main/unnamed.jpg"
CSS_URL = "https://raw.githubusercontent.com/drankitakhandelwalindia-ux/AITP-Project-1/refs/heads/main/style.css"

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch Custom CSS
try:
    response = requests.get(CSS_URL)
    mishtee_css = response.text if response.status_code == 200 else ""
except:
    mishtee_css = ""

# --- 2. CORE FUNCTIONS ---

def get_customer_portal_data(phone_number):
    """Retrieves greeting and order history."""
    if not phone_number or len(phone_number) < 10:
        return "Please enter a valid 10-digit mobile number.", pd.DataFrame()
    
    try:
        # Fetch Name
        cust_resp = supabase.table("customers").select("full_name").eq("phone", phone_number).single().execute()
        if not cust_resp.data:
            return "Welcome! It looks like you're new to the magic. Please register to see your history.", pd.DataFrame()
        
        greeting = f"## Namaste, {cust_resp.data['full_name']} ji! \nGreat to see you again."

        # Fetch Order History
        order_resp = supabase.table("orders").select(
            "order_id, order_date, qty_kg, status, products(sweet_name)"
        ).eq("cust_phone", phone_number).order("order_date", desc=True).execute()

        if not order_resp.data:
            return greeting, pd.DataFrame(columns=["Order ID", "Date", "Item", "Qty (kg)", "Status"])

        df = pd.DataFrame(order_resp.data)
        df['Item'] = df['products'].apply(lambda x: x['sweet_name'] if x else "Unknown")
        df_display = df[['order_id', 'order_date', 'Item', 'qty_kg', 'status']]
        df_display.columns = ["Order ID", "Date", "Item", "Qty (kg)", "Status"]

        return greeting, df_display
    except Exception as e:
        return f"System busy. Please try again later.", pd.DataFrame()

def get_trending_products():
    """Retrieves top 4 best sellers."""
    try:
        resp = supabase.table("orders").select(
            "qty_kg, products(sweet_name, variant_type, price_per_kg)"
        ).execute()

        if not resp.data: return pd.DataFrame()

        df_raw = pd.DataFrame(resp.data)
        df_raw['Sweet Name'] = df_raw['products'].apply(lambda x: x['sweet_name'])
        df_raw['Variant'] = df_raw['products'].apply(lambda x: x['variant_type'])
        df_raw['Price (₹/kg)'] = df_raw['products'].apply(lambda x: x['price_per_kg'])

        trending = df_raw.groupby(['Sweet Name', 'Variant', 'Price (₹/kg)'])['qty_kg'].sum().reset_index()
        return trending.sort_values(by='qty_kg', ascending=False).head(4).rename(columns={'qty_kg': 'Total Sold (kg)'})
    except:
        return pd.DataFrame(columns=["Sweet Name", "Variant", "Price", "Total Sold"])

# --- 3. GRADIO UI LAYOUT ---

with gr.Blocks(css=mishtee_css, title="MishTee-Magic") as demo:
    
    # Header Section
    with gr.Column(elem_id="header", variant="compact"):
        with gr.Row():
            gr.Image(LOGO_URL, show_label=False, container=False, width=180)
        gr.Markdown("<center><h1>MishTee-Magic</h1></center>")
        gr.Markdown("<center><h3>[ Purity and Health ]</h3></center>")
    
    gr.HTML("<hr style='border: 0.5px solid #C06C5C; opacity: 0.3; margin: 20px 0;'>")

    # Welcome & Login Area
    with gr.Row():
        with gr.Column(scale=2):
            phone_input = gr.Textbox(label="Enter Mobile Number", placeholder="91XXXXXXXX", max_lines=1)
            login_btn = gr.Button("REVEAL THE MAGIC", variant="primary")
        with gr.Column(scale=3):
            greeting_output = gr.Markdown("### Welcome back to our artisanal kitchen.")

    # Main Content Tabs
    with gr.Tabs():
        with gr.TabItem("MY ORDER HISTORY"):
            history_table = gr.Dataframe(interactive=False)
            
        with gr.TabItem("TRENDING TODAY"):
            trending_table = gr.Dataframe(interactive=False)
            refresh_trending = gr.Button("Update Trends", variant="secondary")

    # Event Logic
    login_btn.click(
        fn=get_customer_portal_data,
        inputs=[phone_input],
        outputs=[greeting_output, history_table]
    )
    
    # Load trending data on app start or refresh
    demo.load(fn=get_trending_products, outputs=trending_table)
    refresh_trending.click(fn=get_trending_products, outputs=trending_table)

    # Footer
    gr.Markdown("<br><center><small>© 2024 MishTee-Magic. A2 Milk | Organic | Low-Sugar</small></center>")

if __name__ == "__main__":
    demo.launch()
