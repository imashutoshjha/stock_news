import streamlit as st
import os
from model import generate_news_summary

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Portfolio News Generator", layout="wide")

# ─── Global CSS & Theme ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  body, .block-container {
    background-color: #f5f7fa !important;
    color: #333 !important;
  }
  .css-1d391kg {
    background-color: #ffffff;
    color: #333;
    border-right: 1px solid #e1e4e8;
  }
  .stButton>button { 
    background-color: #ff6b6b !important;
    color: #fff !important;
    border-radius: 4px;
  }
  .stButton>button:hover {
    background-color: #ff8787 !important;
  }
  .news-card {
    background-color: #ffffff;
    color: #333;
    border-left: 4px solid #ff6b6b;
    border-radius: 8px;
    padding: 1.2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  }
  .news-card h2 {
    margin: 0 0 0.5rem;
    color: #ff6b6b;
    font-size: 1.4rem;
  }
  .news-card p {
    margin: 0;
    line-height: 1.6;
  }
  [role="option"][aria-selected="true"] {
    background-color: #ff6b6b !important;
    color: #fff !important;
  }
  [role="option"]:hover {
    background-color: #ff8787 !important;
    color: #fff !important;
  }
  #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── CSV Loader ─────────────────────────────────────────────────────────────────
def load_and_enrich(csv_path="indian_stocks_cleaned.csv"):
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
        headers = [h.strip().strip('"') for h in lines[0].split(',')]
        stocks = []
        for line in lines[1:]:
            if not line:
                continue
            cells = [c.strip().strip('"') for c in line.split(',')]
            while len(cells) < len(headers):
                cells.append('')
            rec = dict(zip(headers, cells))
            sym = rec.get('SYMBOL', '').strip()
            if not sym or sym == 'SYMBOL':
                continue
            rec['NAME'] = rec.get('NAME', sym).strip()
            rec['DISPLAY'] = f"{rec['NAME']} ({sym})"
            stocks.append(rec)
        stocks.sort(key=lambda r: r['NAME'])
        return stocks
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        st.stop()

stocks_data = load_and_enrich()

# ─── Session State ─────────────────────────────────────────────────────────────
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = []
if "generate" not in st.session_state:
    st.session_state.generate = False

# ─── Layout: Two Columns ─────────────────────────────────────────────────────────
left, right = st.columns([0.3, 0.7])

with left:
    st.header("⚙️ Controls")

    # Search & Add
    choice = st.selectbox("🔍 Pick a stock", ["-- Select --"] + [r['DISPLAY'] for r in stocks_data])
    if st.button("➕ Add", use_container_width=True):
        if choice == "-- Select --":
            st.error("Select a stock first!")
        elif choice in st.session_state.selected_stocks:
            st.markdown(
                '<div style="background-color:#b71c1c;color:white;padding:10px;border-radius:4px;margin-top:10px;">'
                '⚠️ <strong>Already added.</strong></div>',
                unsafe_allow_html=True
            )
        else:
            st.session_state.selected_stocks.append(choice)

    st.markdown("---")
    # Moved Clear & Generate to here
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.selected_stocks = []
        st.session_state.generate = False

    if st.button("📊stocks-Generate Report", use_container_width=True):
        if st.session_state.selected_stocks:
            st.session_state.generate = True
        else:
            st.error("Add at least one stock.")

    st.markdown("---")
    st.subheader("✅ Your Picks")
    # List picks + remove buttons
    for idx, disp in enumerate(st.session_state.selected_stocks):
        c1, c2 = st.columns([0.8, 0.2])
        c1.write(f"{idx+1}. {disp}")
        if c2.button("➖", key=f"rm_{idx}", use_container_width=True):
            st.session_state.selected_stocks.pop(idx)
            st.session_state.generate = False

with right:
    st.title("📈 Portfolio News Generator")


    if st.session_state.generate:
        stock_dict = {
            rec['NAME']: rec['SYMBOL']
            for rec in stocks_data
            if rec['DISPLAY'] in st.session_state.selected_stocks
        }
        summaries = generate_news_summary(stock_dict)

        # st.markdown("---")
        st.subheader("📰 News Summaries")
        for stock, summary in summaries.items():
            st.markdown(f"""
                <div class="news-card">
                  <h2>{stock}</h2>
                  <p>{summary}</p>
                </div>
            """, unsafe_allow_html=True)
