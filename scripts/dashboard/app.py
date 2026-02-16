import streamlit as st
import pandas as pd
import os
import glob

# Page Config
st.set_page_config(page_title="RAGAS Evaluation Dashboard", layout="wide")
st.title("📊 RAGAS Evaluation Dashboard")

# Paths
RESULTS_DIR = "evaluation_results"

def get_run_options():
    """Scans for result files and returns a dict mapping display_name -> file_path"""
    files = glob.glob(os.path.join(RESULTS_DIR, "ragas_results*.csv"))
    # Sort by creation time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)
    
    options = {}
    for f in files:
        filename = os.path.basename(f)
        # Parse filename: ragas_results_[NAME]_[TIMESTAMP].csv
        # Fallback for old ragas_results.csv
        if filename == "ragas_results.csv":
            display = "Latest (Legacy)"
        else:
            try:
                # Remove prefix and extension
                base = filename.replace("ragas_results_", "").replace(".csv", "")
                parts = base.split("_")
                # Assumes format: name_date_time (where date_time is 2 parts)
                # But name can have underscores. 
                # Timestamp is always last 2 parts: YYYYMMDD_HHMMSS
                if len(parts) >= 2:
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    name = "_".join(parts[:-2])
                    display = f"{name} ({timestamp_str})"
                else:
                    display = base
            except:
                display = filename
        
        options[display] = f
    return options

# Sidebar Selection
run_options = get_run_options()

if not run_options:
    st.warning(f"No results found in `{RESULTS_DIR}`. Run `scripts/evaluate_ragas.py` first.")
    st.stop()

selected_run_name = st.sidebar.selectbox("Select Evaluation Run", list(run_options.keys()))
LATEST_RESULTS = run_options[selected_run_name]

st.sidebar.info(f"Viewing: `{os.path.basename(LATEST_RESULTS)}`")

def load_data():
    if not os.path.exists(LATEST_RESULTS):
        return None
    return pd.read_csv(LATEST_RESULTS)

df = load_data()

if df is None:
    st.warning("Failed to load data.")
else:
    # --- Metrics Overview ---
    st.header("📈 Key Metrics")
    
    # Calculate averages
    metrics = {
        "Faithfulness": df.get("faithfulness", pd.Series([0])).mean(),
        "Answer Relevancy": df.get("answer_relevancy", pd.Series([0])).mean(),
        "Context Precision": df.get("context_precision", pd.Series([0])).mean(),
        "Context Recall": df.get("context_recall", pd.Series([0])).mean(),
    }
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faithfulness", f"{metrics['Faithfulness']:.2f}")
    col2.metric("Answer Relevancy", f"{metrics['Answer Relevancy']:.2f}")
    col3.metric("Context Precision", f"{metrics['Context Precision']:.2f}")
    col4.metric("Context Recall", f"{metrics['Context Recall']:.2f}")

    # --- Detailed Data ---
    st.divider()
    st.header("📝 Detailed Results")
    
    # Styled Dataframe
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", format="%d"),
            "user_input": "Question",
            "response": "Generated Answer",
            "reference": "Ground Truth",
            "retrieved_contexts": "Retrieved Contexts",
            "faithfulness": st.column_config.NumberColumn("Faithfulness", format="%.2f"),
            "answer_relevancy": st.column_config.NumberColumn("Relevancy", format="%.2f"),
            "context_precision": st.column_config.NumberColumn("Precision", format="%.2f"),
            "context_recall": st.column_config.NumberColumn("Recall", format="%.2f"),
        }
    )

    # --- Expander for Details ---
    st.divider()
    st.subheader("🔍 Inspect Individual Items")
    
    for _, row in df.iterrows():
        # Handle case where 'id' might be missing in old results
        doc_id = row.get('id', 'N/A')
        # If ID is float (due to NaNs in mixed data), convert to int/str
        try:
             doc_id = int(doc_id)
        except:
             pass
             
        with st.expander(f"ID: {doc_id} | Question: {row['user_input']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Generated Answer:**")
                st.info(row['response'])
            with c2:
                st.markdown("**Ground Truth:**")
                st.success(row['reference'])
            
            st.markdown("**Retrieved Contexts:**")
            st.text(row['retrieved_contexts'])
            
            st.markdown("---")
            cols = st.columns(4)
            cols[0].metric("Faithfulness", f"{row.get('faithfulness', 0):.2f}")
            cols[1].metric("Relevancy", f"{row.get('answer_relevancy', 0):.2f}")
            cols[2].metric("Precision", f"{row.get('context_precision', 0):.2f}")
            cols[3].metric("Recall", f"{row.get('context_recall', 0):.2f}")
