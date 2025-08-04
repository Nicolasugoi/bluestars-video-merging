import os
import streamlit as st

def manual_cleanup_excel_only():
    """Xóa chỉ file Excel temp của session hiện tại"""
    try:
        session_id = st.session_state.get("session_id", "")
        if not session_id:
            st.warning("No active session found.")
            return

        # Chỉ xóa file Excel temp
        excel_file = f"all_{session_id}.xlsx"
        
        if os.path.exists(excel_file):
            try:
                os.remove(excel_file)
                st.success(f"🗑️ Deleted Excel temp file: {os.path.basename(excel_file)}")
            except Exception as e:
                st.error(f"Error deleting Excel file: {e}")
        else:
            st.info("No Excel temp file found to delete.")
        
    except Exception as e:
         st.error(f"Error during Excel cleanup: {e}")