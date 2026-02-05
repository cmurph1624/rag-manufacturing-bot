import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = "evaluation_history.db"

def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        r.*, 
        ic.chunk_size, 
        ic.overlap,
        ic.ingestion_type,
        ic.configuration_json
    FROM runs r
    LEFT JOIN ingestion_configs ic ON r.ingestion_config_id = ic.id
    ORDER BY r.timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_verification(run_id, detail_id, new_status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update the specific detail record
    cursor.execute("UPDATE run_details SET verified_correct = ? WHERE id = ?", (new_status, detail_id))
    
    # Recalculate verified accuracy for the run
    cursor.execute("SELECT COUNT(*), SUM(verified_correct) FROM run_details WHERE run_id = ?", (run_id,))
    total, verified_count = cursor.fetchone()
    
    if total > 0:
        new_accuracy = (verified_count / total) * 100
        cursor.execute("UPDATE runs SET verified_accuracy = ? WHERE id = ?", (new_accuracy, run_id))
    
    conn.commit()
    conn.close()

def main():
    st.set_page_config(page_title="Evaluation Dashboard", layout="wide")
    st.title("🤖 Rag Bot Evaluation Dashboard")
    
    df = load_data()
    
    if df.empty:
        st.warning("No evaluation history found. Run `evaluate.py` to generate data.")
        return

    # Metrics Overview
    latest_run = df.iloc[0]
    
    # Handle backward compatibility if verified_accuracy is null (though migration should fix this)
    verified_acc = latest_run.get('verified_accuracy')
    if pd.isna(verified_acc):
        verified_acc = latest_run['accuracy']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Accuracy", f"{latest_run['accuracy']:.2f}%")
    col1.caption("Raw LLM Judge")
    
    col2.metric("Verified Accuracy", f"{verified_acc:.2f}%")
    col2.caption("Human Verified") # Better name requested by user sort of
    
    col3.metric("Latest Latency", f"{latest_run['avg_latency']:.2f}s")
    col4.metric("Total Runs", len(df))

    # Data Table
    st.subheader("Run History")
    
    # Format columns for display
    display_df = df.copy()
    display_df['accuracy'] = display_df['accuracy'].apply(lambda x: f"{x:.2f}%")
    
    # Check if verified_accuracy exists in df (it should)
    if 'verified_accuracy' in display_df.columns:
        display_df['verified_accuracy'] = display_df['verified_accuracy'].fillna(display_df['accuracy'])
        display_df['verified_accuracy'] = display_df['verified_accuracy'].apply(lambda x: f"{float(x):.2f}%" if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).isdigit()) else x)

    display_df['avg_latency'] = display_df['avg_latency'].apply(lambda x: f"{x:.2f}s")
    
    # Process Ingestion Config for Display
    def format_ingestion_config(row):
        i_type = row.get('ingestion_type')
        config_json = row.get('configuration_json')
        
        # Fallback for old runs
        if not i_type:
            # If chunk_size exists, assume standard
            if pd.notna(row.get('chunk_size')) and row.get('chunk_size') != 0:
                return f"Standard (C={row['chunk_size']}, O={row['overlap']})"
            return "Unknown"

        if i_type == "standard":
            # Prefer JSON if available, else columns
            c_size = row.get('chunk_size')
            overlap = row.get('overlap')
            # Extract from JSON if present?
            return f"Standard (C={c_size}, O={overlap})"
        
        elif i_type == "semantic":
            # Parse JSON to get threshold
            try:
                import json
                if config_json:
                    conf = json.loads(config_json)
                    return f"Semantic (Thresh={conf.get('semantic_threshold')})"
            except:
                pass
            return "Semantic"
            
        return i_type

    display_df['ingest_details'] = display_df.apply(format_ingestion_config, axis=1)

    # Selection
    st.markdown("### Select a Run to View Details")
    
    # Initialize session state for selection if not present
    if "selected_run_id" not in st.session_state:
        st.session_state.selected_run_id = None

    # explicit column order
    column_order = [
         'timestamp', 'model_name', 'retrieval_type', 'ingest_details', 
         'accuracy', 'verified_accuracy', 'total_questions', 'avg_latency',
         'id', 'ingestion_config_id'
    ]
    # Filter to only columns that exist (in case joined cols are missing)
    display_cols = [c for c in column_order if c in display_df.columns]
    display_df = display_df[display_cols]

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="run_history_table", # Add key for stability
        column_config={
            "timestamp": "Time",
            "model_name": "Model",
            "retrieval_type": "Method",
            "ingest_details": "Ingestion Config",
            "accuracy": "Raw Accuracy",
            "verified_accuracy": "Verified Accuracy",
            "total_questions": "Questions",
            "avg_latency": "Latency (avg)",
            "id": None ,
            "ingestion_config_id": None
        }
    )
    
    # Update selection from dataframe *if* user interacted with it
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        # Map back to original df to get ID
        selected_run_id = df.iloc[selected_index]["id"]
        st.session_state.selected_run_id = int(selected_run_id)

    # Use session state to drive the details view
    if st.session_state.selected_run_id:
        run_id = st.session_state.selected_run_id
        
        # Check if run exists in current df (it should, unless deleted)
        selected_run_row = df[df['id'] == run_id]
        
        if selected_run_row.empty:
            st.session_state.selected_run_id = None
            st.rerun()
            return
            
        selected_run = selected_run_row.iloc[0]
        
        st.divider()
        col_header, col_close = st.columns([10, 1])
        with col_header:
            st.subheader(f"Run Details: {selected_run['timestamp']} ({selected_run['model_name']})")
        with col_close:
            if st.button("Close"):
                st.session_state.selected_run_id = None
                st.rerun()
        
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
                # Determine display status based on verification if available, else raw
                is_correct = row['is_correct']
                verified_correct = row.get('verified_correct')
                
                # If verified_correct is None (legacy), default to is_correct
                if pd.isna(verified_correct):
                    verified_correct = is_correct
                
                # Display logic
                status_color = "green" if verified_correct else "red" # Use verified status for color
                status_text = "PASSED" if verified_correct else "FAILED"
                
                # Status Icon
                icon = "✅" if verified_correct else "❌"
                
                # STABLE LABEL: Use question only to prevent expander closing on update
                # We put the status icon in the label though, as it's useful. 
                # Wait, if icon changes, does it close? Yes.
                # So we must use a completely static label if we want it to stay open during toggle.
                # User asked for "detail item I have open remains open".
                # So let's use just the Question.
                
                with st.expander(f"{row['question']}"): 
                    col_info, col_verify = st.columns([3, 1])
                    
                    with col_info:
                        # Status Header inside
                        override_text = " (OVERRIDDEN)" if verified_correct != is_correct else ""
                        st.markdown(f"### {icon} :{status_color}[{status_text}]{override_text}")
                        
                        st.markdown(f"**Latency:** {row['latency']:.2f}s")
                        st.markdown(f"**Retrieval Type:** {row['retrieval_type']}")
                    
                    with col_verify:
                        # Verification Checkbox
                        def on_verify_change(rid=run_id, did=row['id'], k=f"verify_{row['id']}"):
                            new_val = st.session_state[k]
                            update_verification(rid, did, new_val)
                            
                        is_checked = bool(verified_correct)
                        st.checkbox(
                            "Verified Correct", 
                            value=is_checked, 
                            key=f"verify_{row['id']}",
                            on_change=on_verify_change
                        )

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
