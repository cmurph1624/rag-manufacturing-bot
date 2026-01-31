import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = "evaluation_history.db"

def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM runs ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def main():
    st.set_page_config(page_title="Evaluation Dashboard", layout="wide")
    st.title("🤖 Rag Bot Evaluation Dashboard")
    
    df = load_data()
    
    if df.empty:
        st.warning("No evaluation history found. Run `evaluate.py` to generate data.")
        return

    # Metrics Overview
    latest_run = df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Accuracy", f"{latest_run['accuracy']:.2f}%")
    col2.metric("Latest Latency", f"{latest_run['avg_latency']:.2f}s")
    col3.metric("Total Runs", len(df))

    # Data Table
    st.subheader("Run History")
    
    # Format columns for display
    display_df = df.copy()
    display_df['accuracy'] = display_df['accuracy'].apply(lambda x: f"{x:.2f}%")
    display_df['avg_latency'] = display_df['avg_latency'].apply(lambda x: f"{x:.2f}s")
    
    # Selection
    st.markdown("### Select a Run to View Details")
    
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "timestamp": "Time",
            "model_name": "Model",
            "retrieval_type": "Method",
            "accuracy": "Accuracy",
            "total_questions": "Questions",
            "avg_latency": "Latency (avg)",
            "id": None 
        }
    )
    
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        selected_run = df.iloc[selected_index]
        run_id = int(selected_run["id"])
        
        st.divider()
        st.subheader(f"Run Details: {selected_run['timestamp']} ({selected_run['model_name']})")
        
        # Load details
        conn = sqlite3.connect(DB_PATH)
        details_df = pd.read_sql_query("SELECT * FROM run_details WHERE run_id = ?", conn, params=(run_id,))
        conn.close()
        
        if details_df.empty:
            st.warning("No details available for this run.")
        else:
            # Filters
            filter_status = st.radio("Filter by Status", ["All", "Failed Only", "Passed Only"], horizontal=True)
            
            if filter_status == "Failed Only":
                details_df = details_df[details_df["is_correct"] == 0]
            elif filter_status == "Passed Only":
                details_df = details_df[details_df["is_correct"] == 1]
            
            st.write(f"Showing {len(details_df)} records")
            
            for index, row in details_df.iterrows():
                status_color = "green" if row['is_correct'] else "red"
                status_text = "PASSED" if row['is_correct'] else "FAILED"
                
                with st.expander(f"[{status_text}] {row['question']}"):
                    st.markdown(f"**Status:** :{status_color}[{status_text}]")
                    st.markdown(f"**Latency:** {row['latency']:.2f}s")
                    st.markdown(f"**Retrieval Type:** {row['retrieval_type']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Bot Answer:**")
                        st.info(row['bot_answer'])
                    with col_b:
                        st.markdown("**Gold Answer:**")
                        st.success(row['gold_answer'])
                    
                    if row['citation_match']:
                        st.caption("✅ Citation matched expected location")
                    else:
                        st.caption("❌ Citation match failed or not applicable")

if __name__ == "__main__":
    main()
