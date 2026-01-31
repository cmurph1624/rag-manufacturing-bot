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
    
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "timestamp": "Time",
            "model_name": "Model",
            "accuracy": "Accuracy",
            "total_questions": "Questions",
            "avg_latency": "Latency (avg)",
            "id": None # Hide ID
        }
    )

if __name__ == "__main__":
    main()
