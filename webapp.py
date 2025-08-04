import streamlit as st
import os
import pandas as pd
from datetime import datetime
import shutil
from streamlit_sortables import sort_items
import soundfile as sf
import time
import zipfile
import subprocess
from PIL import Image, ImageDraw, ImageFont

import video
import clean
import sub
import script_gemini  
import tts  
import get_add
import script_gemini
import prompt

# CSS cho drag-drop và preview
st.markdown("""
<style>
.asin-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: bold;
    margin: 10px 0;
    text-align: center;
}

.file-box {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 2px 0;
    font-family: monospace;
    font-size: 14px;
    color: #495057;
}

.sortable-container {
    min-height: 50px;
    padding: 10px;
    border: 2px dashed #ccc;
    border-radius: 6px;
    background: #fafafa;
}

.sortable-container:hover {
    border-color: #667eea;
    background: #f0f8ff;
}
</style>
""", unsafe_allow_html=True)

def start_log_group(group_name):
    """Start a new log group"""
    if "sidebar_logs" not in st.session_state:
        st.session_state.sidebar_logs = []
    if "current_log_group" not in st.session_state:
        st.session_state.current_log_group = None
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    group_marker = {
        "type": "group_start",
        "name": group_name,
        "timestamp": timestamp,
        "logs": []
    }
    st.session_state.sidebar_logs.append(group_marker)
    st.session_state.current_log_group = len(st.session_state.sidebar_logs) - 1

def end_log_group():
    """End the current log group"""
    if "current_log_group" in st.session_state:
        st.session_state.current_log_group = None

def add_log_to_sidebar(message, log_type="info"):
    """Add log message to sidebar with categorization"""
    if "sidebar_logs" not in st.session_state:
        st.session_state.sidebar_logs = []
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Thêm icon dựa trên loại log
    icons = {"info": "ℹ️","success": "✅", "warning": "⚠️","error": "❌","step": "🚀"}
    
    icon = icons.get(log_type, "ℹ️")
    formatted_message = f"[{timestamp}] {icon} {message}"
    
    # Nếu đang trong group, thêm vào group
    if ("current_log_group" in st.session_state and 
        st.session_state.current_log_group is not None and
        st.session_state.current_log_group < len(st.session_state.sidebar_logs)):
        
        group_item = st.session_state.sidebar_logs[st.session_state.current_log_group]
        if isinstance(group_item, dict) and group_item.get("type") == "group_start":
            group_item["logs"].append({
                "message": formatted_message,
                "log_type": log_type
            })
        else:
            # Fallback nếu group không hợp lệ
            st.session_state.sidebar_logs.append(formatted_message)
    else:
        # Thêm log bình thường nếu không trong group
        st.session_state.sidebar_logs.append(formatted_message)
    
    # Giữ chỉ 100 log entries gần nhất
    if len(st.session_state.sidebar_logs) > 100:
        st.session_state.sidebar_logs = st.session_state.sidebar_logs[-100:]

st.sidebar.header("📋 Activity Logs") # Sidebar logs
def render_sidebar_logs():
    if "sidebar_logs" in st.session_state and st.session_state.sidebar_logs:    
        for log in reversed(st.session_state.sidebar_logs):
            if isinstance(log, dict) and log.get("type") == "group_start":
                # Hiển thị log group với border
                group_name = log.get("name", "Unknown Operation")
                group_logs = log.get("logs", [])
                timestamp = log.get("timestamp", "")
                
                if group_logs:  
                    st.sidebar.markdown(
                        f"""
                        <div style="
                            border: 2px solid #667eea; 
                            border-radius: 8px; 
                            padding: 8px; 
                            margin: 8px 0; 
                            background: rgba(102, 126, 234, 0.1);
                            backdrop-filter: blur(10px);
                        ">
                            <strong>🔄 {group_name}</strong> <small style="opacity: 0.7;">({timestamp})</small> ⬆️
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # Hiển thị logs trong group (theo thứ tự ngược)
                    for group_log in reversed(group_logs):
                        message = group_log.get("message", "")
                        log_type = group_log.get("log_type", "info")
                        
                        # Thêm indent để nhận biết đây là log trong group
                        indented_message = "    " + message
                        
                        if "✅" in message:
                            st.sidebar.success(indented_message, icon="✅")
                        elif "❌" in message:
                            st.sidebar.error(indented_message, icon="❌")
                        elif "⚠️" in message:
                            st.sidebar.warning(indented_message, icon="⚠️")
                        elif "🚀" in message:
                            st.sidebar.info(indented_message, icon="🚀")
                        else:
                            st.sidebar.text(indented_message)
            
            elif isinstance(log, str):
                # Log bình thường (không thuộc group)
                if "✅" in log:
                    st.sidebar.success(log, icon="✅")
                elif "❌" in log:
                    st.sidebar.error(log, icon="❌")
                elif "⚠️" in log:
                    st.sidebar.warning(log, icon="⚠️")
                elif "🚀" in log:
                    st.sidebar.info(log, icon="🚀")
                else:
                    st.sidebar.text(log)
        
    else:
        st.sidebar.info("No activity logs yet. Run some operations to see logs here.")

render_sidebar_logs()

# Auto-refresh nếu có flag render completed
if st.session_state.get("render_completed", False):
    st.session_state["render_completed"] = False  # Reset flag
    st.rerun()

def get_audio_duration(audio_path):
    try:
        f = sf.SoundFile(audio_path)
        return f.frames / f.samplerate
    except Exception:
        return 0

def get_session_id():
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    return st.session_state["session_id"]

def save_uploaded_file(uploaded_file, save_path):
    try:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True, f"{uploaded_file.name} -> {save_path}"
    except Exception as e:
        return False, f"Error saving {uploaded_file.name}: {e}"

def copy_file(src, dst):
    try:
        shutil.copy2(src, dst)
        return True, f"{os.path.basename(src)} -> {dst}"
    except Exception as e:
        return False, f"Error copying {os.path.basename(src)}: {e}"

def handle_special_file_upload(upload_file, prefix, session_id, valid_exts, session_key):
    if upload_file:
        ext = os.path.splitext(upload_file.name)[1]
        if ext.lower() in valid_exts:
            fname = f"{prefix}_{session_id}{ext}"
            ok, msg = save_uploaded_file(upload_file, fname)
            if ok:
                st.session_state[session_key] = fname
                return True, f"{prefix.capitalize()} ({upload_file.name}) -> {fname}"
            else:
                st.session_state[session_key] = None
                return False, msg
        else:
            return False, f"{prefix.capitalize()}: Invalid file format."
    else:
        st.session_state[session_key] = None
        return True, f"No {prefix} uploaded, will skip {prefix}."

def handle_special_file_copy(settings_folder_path, prefix, session_id, valid_exts, session_key, display_name):
    found = False
    msg = ""
    for f_name in os.listdir(settings_folder_path):
        if f_name.lower().startswith(f"{prefix}.") and f_name.lower().split('.')[-1] in valid_exts:
            src_path = os.path.join(settings_folder_path, f_name)
            ext = os.path.splitext(f_name)[1]
            dst_name = f"{prefix}_{session_id}{ext}"
            ok, msg = copy_file(src_path, dst_name)
            if ok:
                st.session_state[session_key] = dst_name
                msg = f"{display_name} ({f_name}) -> {dst_name}"
            else:
                st.session_state[session_key] = None
            found = True
            break
    if not found:
        st.session_state[session_key] = None
        msg = f"No {display_name.lower()} file found, will skip {display_name.lower()}."
    return found, msg

def detect_gpu_codecs():
    potential_codecs = ['libx264']
    hardware_codecs = ['h264_nvenc', 'hevc_nvenc', 'av1_nvenc','h264_qsv', 'hevc_qsv', 'av1_qsv',
        'h264_amf', 'hevc_amf', 'av1_amf','h264_mf', 'hevc_mf','h264_vaapi', 'hevc_vaapi', 'av1_vaapi',]
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], 
                              capture_output=True, text=True, check=True, startupinfo=startupinfo)
        output = result.stdout.lower()
        for codec in hardware_codecs:
            if codec.lower() in output and codec not in potential_codecs:
                potential_codecs.append(codec)
    except:
        pass
    return potential_codecs

def ensure_audio1_column(excel_file_path, audio1_path_to_write_abs):
    for _ in range(5):
        try:
            df = pd.read_excel(excel_file_path)
            break
        except zipfile.BadZipFile:
            time.sleep(0.5)
        except FileNotFoundError:
            return
        except Exception as e:
            st.warning(f"Error reading Excel '{os.path.basename(excel_file_path)}' when updating Audio1: {e}. Retrying...")
            time.sleep(1)
    else:
        st.error(f"Excel file '{os.path.basename(excel_file_path)}' is locked, corrupted, or has other errors.")
        return

    audio1_val_for_excel = audio1_path_to_write_abs if audio1_path_to_write_abs and os.path.exists(audio1_path_to_write_abs) else ""
    df["Audio1"] = audio1_val_for_excel

    try:
        df.to_excel(excel_file_path, index=False)
    except Exception as e:
        st.error(f"Error saving Excel '{os.path.basename(excel_file_path)}' after updating Audio1: {e}")

def reorder_media_excel_dragdrop(excel_file_path, session_id):
    for key in list(st.session_state.keys()):
        if key.startswith(f"media_sort_") and key.endswith(f"_{session_id}"):
            del st.session_state[key]
    
    if not os.path.exists(excel_file_path):
        st.warning(f"Excel file {os.path.basename(excel_file_path)} does not exist.")
        return

    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        st.error(f"Error reading Excel: {e}")
        return

    if df.empty:
        st.info("Excel file is empty.")
        return

    asin_col = df.columns[0]
    media_cols = [col for col in df.columns if col.startswith("Media") and col != "Media1"]
    asins = df[asin_col].dropna().astype(str).unique().tolist()
    
    valid_asins = []
    for asin in asins:
        row = df[df[asin_col] == asin]
        if not row.empty:            # Kiểm tra xem có ít nhất 1 file media tồn tại không
            has_valid_media = False
            for col in media_cols:
                val = str(row.iloc[0].get(col, "")).strip()
                if val and val.lower() != "nan" and os.path.exists(val):
                    has_valid_media = True
                    break
            if has_valid_media:
                valid_asins.append(asin)
    
    if not valid_asins:
        st.info("No ASINs with valid media files found. Please check your media folder or run 'Prepare media' again.")
        return

    for asin in valid_asins:
        row = df[df[asin_col] == asin]
        if row.empty:
            continue

        st.markdown(f'<div class="asin-header">ASIN: {asin}</div>', unsafe_allow_html=True)

        # Build current media list - chỉ lấy những file tồn tại
        media_list = []
        for col in media_cols:
            val = str(row.iloc[0].get(col, "")).strip()
            if val and val.lower() != "nan" and os.path.exists(val):
                media_list.append(val)

        if not media_list:
            st.write("_(no valid media files)_")
            continue

        display = [os.path.basename(m) for m in media_list]  # Chỉ hiển thị tên file
        try:
            new_disp = sort_items(
                items=display,
                key=f"media_sort_{asin}_{session_id}",
                direction="vertical"
            )
        except Exception as e:
            st.error(f"Drag-drop error for {asin}: {e}")
            new_disp = display

        # Map back to full paths
        new_paths = []
        for d in new_disp:
            orig = next((m for m in media_list if os.path.basename(m) == d), None)
            if orig:
                new_paths.append(orig)

        # Render each media in a 3-col row
        for idx, path in enumerate(new_paths):
            key = f"preview_{asin}_{idx}"

            c1, c2, c3 = st.columns([2,9,1])
            with c1:
                st.badge(asin)
            with c2:
                st.markdown(f"<div class='file-box'>{os.path.basename(path)}</div>", unsafe_allow_html=True)
            with c3:
                if st.button("👁️", key=f"btn_{key}"):
                    # Create a modal dialog for video preview
                    @st.dialog(f"Preview: {os.path.basename(path)}", width="large")
                    def show_video():
                        if os.path.exists(path):
                            st.video(path)
                        else:
                            st.error(f"File not found: {path}")
                    
                    show_video()

        # Save if changed
        orig_list = [os.path.basename(m) for m in media_list]
        new_list = [os.path.basename(m) for m in new_paths]
        if new_list != orig_list:
            st.markdown("✅ Order changed — remember to save!")
            if st.button(f"💾 Save for {asin}", key=f"save_{asin}"):
                idxs = df[df[asin_col]==asin].index
                
                # Clear all media columns first
                for i in range(2, len(media_cols)+2):
                    if f"Media{i}" in df.columns:
                        df.loc[idxs, f"Media{i}"] = ""
                
                # Set new order
                for i, p in enumerate(new_paths):
                    col_name = f"Media{i+2}"
                    if col_name in df.columns:
                        df.loc[idxs, col_name] = p
                
                df.to_excel(excel_file_path, index=False)
                st.success(f"Saved order for {asin}")
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

# Session State Initialization
if "actual_audio1_filename" not in st.session_state:
    st.session_state.actual_audio1_filename = None
if "logo_filename_session_actual" not in st.session_state:
    st.session_state.logo_filename_session_actual = None
if "available_gpu_codecs" not in st.session_state:
    st.session_state.available_gpu_codecs = detect_gpu_codecs()
if "rendered_video_paths" not in st.session_state:
    st.session_state.rendered_video_paths = []
if "show_video_preview" not in st.session_state:
    st.session_state.show_video_preview = False
if "previous_input_folder" not in st.session_state:
    st.session_state.previous_input_folder = ""
if "render_completed" not in st.session_state:
    st.session_state.render_completed = False

def on_input_folder_change():
    """Callback function when input folder changes - compress old logs"""
    current_folder = st.session_state.get("input_folder", "")
    previous_folder = st.session_state.get("previous_input_folder", "")
    
    # Chỉ thực hiện khi folder thực sự thay đổi và không phải lần đầu load
    if current_folder != previous_folder and previous_folder != "":
        if "sidebar_logs" in st.session_state and st.session_state.sidebar_logs:
            # Thu gọn logs cũ xuống chỉ còn 5 logs gần nhất
            compressed_logs = st.session_state.sidebar_logs[-5:] if len(st.session_state.sidebar_logs) > 5 else st.session_state.sidebar_logs
            st.session_state.sidebar_logs = compressed_logs
            
            # Thêm log thông báo về việc thay đổi folder
            add_log_to_sidebar(f"📁 Input folder changed: {current_folder}", "info")
    
    # Cập nhật previous folder
    st.session_state.previous_input_folder = current_folder

session_id = get_session_id()
excel_filename = f"all_{session_id}.xlsx"

ORIGINAL_TTS_CRED_NAME = "text-to-speech.json"
ORIGINAL_EXCEL_NAME = "all.xlsx"
ORIGINAL_AUDIO1_NAME = "Audio1.mp3"

# Main App
st.title("Media Automation Pipeline")
st.text_input("🔑 Enter your Gemini API Key", key="gemini_api_key", placeholder="e.g., AIzaSyDBEI...")

# Configuration
st.header("📁 Setup Source and Destination Folders")
input_folder = st.text_input(
    "Path to folder containing raw videos:",
    value="./raw video",
    key="input_folder",
    on_change=on_input_folder_change
)
audio2_folder = st.text_input(
    "Where will you store voice files?", 
    value="./voice", 
    key="audio_output_folder"
)
output_folder = st.text_input(
    "Path to output folder for final videos:",
    value="./final video",
    key="output_folder"
)

st.header("📂 1. Load Initial Settings")
brand = st.radio("Which brand are you making videos for?", ("BlueStars", "Canamax"), key="brand_selection")
upload_method = st.radio(
    "You need to provide initial setup files:",
    ("Load from settings folder","Upload individual files"),
    key="upload_method_radio"
)

ORIGINAL_LOGO_NAME = brand + "_logo.png"
bluestars_outtro_path = "bluestars_outtro.mp4"

# Method 1
if upload_method == "Load from settings folder":
    st.info(f"""
    Nhập dường dẫn thư mục chứa các file sau. 
    - `{ORIGINAL_TTS_CRED_NAME}`: chuyển văn bản thành giọng nói (tuỳ chọn)
    - `{ORIGINAL_EXCEL_NAME}`: file Excel chứa dữ liệu làm việc (nếu muốn làm việc đang dở)
    - `{ORIGINAL_LOGO_NAME}`: logo brand
    - `{ORIGINAL_AUDIO1_NAME}`: nhạc nền
    """ + (f"""- `{bluestars_outtro_path}`: outtro video""" if brand == "BlueStars" else ""))

    settings_folder_path = st.text_input("Folder path:", key="settings_folder_path_input")

    if st.button("Load settings from folder", key="btn_load_settings_folder"):
        loaded_successfully = []
        load_infos = []
        load_errors = []

        if settings_folder_path and os.path.isdir(settings_folder_path):
            st.session_state.settings_loaded = True
            
            # Chỉ copy Excel file, các file khác sử dụng trực tiếp từ settings folder
            excel_original_path = os.path.join(settings_folder_path, ORIGINAL_EXCEL_NAME)
            if os.path.exists(excel_original_path):
                ok, msg = copy_file(excel_original_path, excel_filename)
                (loaded_successfully if ok else load_errors).append(msg)
            else:
                try:
                    pd.DataFrame(columns=["ASIN"]).to_excel(excel_filename, index=False)
                    load_infos.append(f"'{ORIGINAL_EXCEL_NAME}' not found, created new Excel file: {excel_filename}")
                except Exception as e:
                    load_errors.append(f"Error creating new Excel file: {e}")

            # TTS credentials - sử dụng trực tiếp từ settings folder
            tts_cred_path = os.path.join(settings_folder_path, ORIGINAL_TTS_CRED_NAME)
            if os.path.exists(tts_cred_path):
                st.session_state["tts_cred_path"] = tts_cred_path
                loaded_successfully.append(f"TTS Credentials found: {ORIGINAL_TTS_CRED_NAME}")
            else:
                st.session_state["tts_cred_path"] = None
                load_infos.append(f"TTS Credentials '{ORIGINAL_TTS_CRED_NAME}' not found, will be skipped.")

            # Logo - sử dụng trực tiếp từ settings folder
            logo_path = None
            for ext in ['png', 'jpg', 'jpeg']:
                potential_logo = os.path.join(settings_folder_path, f"{brand.lower()}_logo.{ext}")
                if os.path.exists(potential_logo):
                    logo_path = potential_logo
                    break
            
            if logo_path:
                st.session_state["logo_filename_session_actual"] = logo_path
                loaded_successfully.append(f"Logo found: {os.path.basename(logo_path)}")
            else:
                st.session_state["logo_filename_session_actual"] = None
                load_infos.append(f"Logo file '{brand.lower()}_logo.*' not found, will be skipped.")

            # Audio1 - sử dụng trực tiếp từ settings folder  
            audio1_path = None
            for ext in ['mp3', 'wav', 'aac', 'm4a']:
                potential_audio = os.path.join(settings_folder_path, f"audio1.{ext}")
                if os.path.exists(potential_audio):
                    audio1_path = potential_audio
                    break
            
            if audio1_path:
                st.session_state["actual_audio1_filename"] = audio1_path
                loaded_successfully.append(f"Audio1 found: {os.path.basename(audio1_path)}")
            else:
                st.session_state["actual_audio1_filename"] = None
                load_infos.append(f"Audio1 file 'audio1.*' not found, will be skipped.")

            # BlueStars outro - sử dụng trực tiếp từ settings folder
            if brand == "BlueStars":
                outtro_path = None
                for ext in ['mp4', 'mov', 'avi']:
                    potential_outtro = os.path.join(settings_folder_path, f"bluestars_outtro.{ext}")
                    if os.path.exists(potential_outtro):
                        outtro_path = potential_outtro
                        break
                
                if outtro_path:
                    st.session_state["bluestars_outtro_filename_session"] = outtro_path
                    loaded_successfully.append(f"BlueStars Outro found: {os.path.basename(outtro_path)}")
                else:
                    st.session_state["bluestars_outtro_filename_session"] = None
                    load_infos.append(f"BlueStars Outro 'bluestars_outtro.*' not found, will be skipped.")

            if loaded_successfully:
                st.success("Setup files have been loaded for the session:")
                for msg in loaded_successfully: 
                    st.write(f"- {msg}")
            if load_infos:
                st.info("Additional information:")
                for msg in load_infos: 
                    st.write(f"- {msg}")
            if load_errors:
                st.error("Errors occurred while loading settings:")
                for msg in load_errors: 
                    st.write(f"- {msg}")
        else:
            st.error("Invalid folder path or folder not found.")
            st.session_state.settings_loaded = False
# Method 2
elif upload_method == "Upload individual files":
    st.markdown("Upload required files. If your workflow doesn't include all steps below, you don't need to upload all files.")
    
    tts_cred_file_upload = st.file_uploader(
        "1. Upload Text-to-Speech Credentials (text-to-speech.json)", 
        type="json", 
        key="tts_cred_single_upload"
    )
    excel_file_upload = st.file_uploader(
        "2. Upload Excel work file (all-***.xlsx)", 
        type=["xlsx"], 
        key="excel_single_upload"
    )
    logo_file_upload = st.file_uploader(
        f"3. Upload logo file ({ORIGINAL_LOGO_NAME})", 
        type=["png", "jpg", "jpeg"], 
        key="logo_single_upload"
    )
    audio1_file_upload = st.file_uploader(
        f"4. Upload Audio1 - background music ({ORIGINAL_AUDIO1_NAME})", 
        type=["mp3", "wav", "aac", "m4a"], 
        key="audio1_single_upload"
    )
    
    if brand == "BlueStars":
        outtro_file_upload = st.file_uploader(
            "5. Upload outro video (bluestars_outtro.mp4)", 
            type=["mp4", "mov", "avi"], 
            key="outtro_single_upload"
        )

    if st.button("Confirm and process uploaded files", key="btn_process_uploaded_files"):
        st.session_state.settings_loaded = True
        loaded_successfully_upload = []
        load_errors_upload = []

        upload_files = [
            (excel_file_upload, excel_filename, "Excel File"),
        ]
        
        for upload, filename, desc in upload_files:
            if upload:
                ok, msg = save_uploaded_file(upload, filename)
                (loaded_successfully_upload if ok else load_errors_upload).append(msg)
            elif desc == "Excel File" and not os.path.exists(excel_filename):
                try:
                    pd.DataFrame(columns=["ASIN"]).to_excel(excel_filename, index=False)
                    loaded_successfully_upload.append(f"Created new Excel file: {excel_filename}")
                except Exception as e:
                    load_errors_upload.append(f"Error creating new Excel file: {e}")

        # TTS Credentials - lưu trực tiếp path vào session_state
        if tts_cred_file_upload:
            # Lưu tạm file để sử dụng
            temp_tts_path = f"temp_tts_{session_id}.json"
            ok, msg = save_uploaded_file(tts_cred_file_upload, temp_tts_path)
            if ok:
                st.session_state["tts_cred_path"] = temp_tts_path
                loaded_successfully_upload.append(f"TTS Credentials uploaded: {tts_cred_file_upload.name}")
            else:
                st.session_state["tts_cred_path"] = None
                load_errors_upload.append(msg)
        else:
            st.session_state["tts_cred_path"] = None
            loaded_successfully_upload.append("No TTS credentials uploaded, voice generation will be skipped.")

        # Logo - lưu trực tiếp path vào session_state  
        if logo_file_upload:
            temp_logo_path = f"temp_logo_{session_id}.{logo_file_upload.name.split('.')[-1]}"
            ok, msg = save_uploaded_file(logo_file_upload, temp_logo_path)
            if ok:
                st.session_state["logo_filename_session_actual"] = temp_logo_path
                loaded_successfully_upload.append(f"Logo uploaded: {logo_file_upload.name}")
            else:
                st.session_state["logo_filename_session_actual"] = None
                load_errors_upload.append(msg)
        else:
            st.session_state["logo_filename_session_actual"] = None
            loaded_successfully_upload.append("No logo uploaded, will skip logo.")

        # Audio1 - lưu trực tiếp path vào session_state
        if audio1_file_upload:
            temp_audio1_path = f"temp_audio1_{session_id}.{audio1_file_upload.name.split('.')[-1]}"
            ok, msg = save_uploaded_file(audio1_file_upload, temp_audio1_path)
            if ok:
                st.session_state["actual_audio1_filename"] = temp_audio1_path
                loaded_successfully_upload.append(f"Audio1 uploaded: {audio1_file_upload.name}")
            else:
                st.session_state["actual_audio1_filename"] = None
                load_errors_upload.append(msg)
        else:
            st.session_state["actual_audio1_filename"] = None
            loaded_successfully_upload.append("No Audio1 uploaded, will skip background music.")

        # BlueStars outro - xử lý upload nếu có
        if brand == "BlueStars" and 'outtro_file_upload' in locals() and outtro_file_upload:
            temp_outtro_path = f"temp_outtro_{session_id}.{outtro_file_upload.name.split('.')[-1]}"
            ok, msg = save_uploaded_file(outtro_file_upload, temp_outtro_path)
            if ok:
                st.session_state["bluestars_outtro_filename_session"] = temp_outtro_path
                loaded_successfully_upload.append(f"BlueStars Outro uploaded: {outtro_file_upload.name}")
            else:
                st.session_state["bluestars_outtro_filename_session"] = None
                load_errors_upload.append(msg)

        if loaded_successfully_upload:
            st.success("Files have been uploaded and processed for the session:")
            for msg in loaded_successfully_upload: 
                st.write(f"- {msg}")
        if load_errors_upload:
            st.error("Errors occurred while loading settings:")
            for msg in load_errors_upload: 
                st.write(f"- {msg}")

# Update after file loading
current_audio1_for_excel = st.session_state.get('actual_audio1_filename')
if os.path.exists(excel_filename):
    ensure_audio1_column(excel_filename, os.path.abspath(current_audio1_for_excel) if current_audio1_for_excel else "")
bluestars_outtro_path = st.session_state.get("bluestars_outtro_filename_session", "")

# Pipeline Steps
st.markdown("---")
st.header("🛠️ 2. Prepare and Arrange Media Order")
st.subheader("Auto-detect ASIN from media file names")

if st.button("Prepare media (auto-detect ASIN from file names)", key="btn_prepare_media"):
    start_log_group("Media Preparation")
    
    add_log_to_sidebar("🚀 Starting media preparation...", "step")
    logs_prepare = []
    current_logo = st.session_state.get("logo_filename_session_actual", "")
    logs_prepare += get_add.main_web(
        excel_path=excel_filename,
        asin_folder_root=input_folder,
        static_media1_path=os.path.abspath(current_logo) if current_logo and os.path.exists(current_logo) else "",
    )
    
    # Phân loại log theo nội dung
    for lg in logs_prepare:
        if lg.startswith("✅"):
            add_log_to_sidebar(lg, "success")
        elif lg.startswith("❌"):
            add_log_to_sidebar(lg, "error")
        elif lg.startswith("⚠️"):
            add_log_to_sidebar(lg, "warning")
        else:
            add_log_to_sidebar(lg, "info")
    
    add_log_to_sidebar("Media preparation completed!", "success")
    
    # Kết thúc log group
    end_log_group()
    
    st.session_state.media_prepared = True
    st.success("✅ Media preparation completed! Check sidebar for details.")
    st.rerun()

st.subheader("🔄 Drag and drop to arrange media order for each video")

# Hiển thị drag & drop
if os.path.exists(excel_filename) or st.session_state.get('media_prepared'):
    reorder_media_excel_dragdrop(excel_filename, session_id)

st.markdown("---")
st.header("⏱️ 3. Calculate Video Duration")
if st.button("Calculate Duration", key="btn_duration"):
    # Bắt đầu log group cho Duration Calculation
    start_log_group("Duration Calculation")
    
    add_log_to_sidebar("🚀 Starting duration calculation...", "step")
        
    try:
        logs_duration = get_add.calculate_duration(input_excel=excel_filename, output_excel=excel_filename)
        
        if logs_duration:
            for l_dur in logs_duration: 
                if l_dur.startswith("✅"):
                    add_log_to_sidebar(l_dur, "success")
                elif l_dur.startswith("❌"):
                    add_log_to_sidebar(l_dur, "error")
                elif l_dur.startswith("⚠️"):
                    add_log_to_sidebar(l_dur, "warning")
                else:
                    add_log_to_sidebar(l_dur, "info")
        else:
            add_log_to_sidebar("Duration calculation completed (no detailed logs)", "info")
            
        add_log_to_sidebar("Duration calculation completed!", "success")
        
        end_log_group()
        
        st.session_state.duration_calculated = True
        st.success("✅ Duration calculation completed! Check sidebar for details.")
        
        st.rerun()
        
    except Exception as e:
        add_log_to_sidebar(f"Duration calculation failed: {str(e)}", "error")
        end_log_group()  # Kết thúc group ngay cả khi có lỗi
        st.error(f"Error during duration calculation: {e}")

st.markdown("---")
st.header("📝 4. Product Information & Prompt Generation")

# Step 4.1: Fetch Product Titles (with retry option)
st.subheader("4.1 Fetch Product Information")
col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 Fetch Product Titles", key="btn_fetch_titles"):
        api_key = st.session_state.get("gemini_api_key", "").strip()
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
            add_log_to_sidebar(f"❌ Excel file {os.path.basename(excel_filename)} does not exist.", "error")
        else:
            try:
                start_log_group("Fetch Product Information")
                add_log_to_sidebar("🚀 Starting product information fetch...", "step")
                logs = prompt.crawl_amazon_data(excel_filename)
                if logs and isinstance(logs, list):
                    for log in logs:
                        if isinstance(log, str):
                            if log.startswith("✅"):
                                add_log_to_sidebar(log, "success")
                            elif log.startswith("❌"):
                                add_log_to_sidebar(log, "error")
                            elif log.startswith("⚠️"):
                                add_log_to_sidebar(log, "warning")
                            else:
                                add_log_to_sidebar(log, "info")
                else:
                    add_log_to_sidebar("Product titles fetch completed", "info")
                add_log_to_sidebar("Product information fetch completed!", "success")
                end_log_group()
                st.success("✅ Product titles fetched and saved to Excel!")
                st.session_state.info_ready = True
                st.rerun()
            except Exception as e:
                add_log_to_sidebar(f"Product fetch failed: {str(e)}", "error")
                end_log_group()  
                st.error(f"Error fetching product titles: {e}")

with col2:
    if st.button("🔁 Retry Failed ASINs", key="btn_retry_failed_titles"):
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
        else:
            try:
                start_log_group("Retry Failed Product Information")
                
                add_log_to_sidebar("🚀 Starting retry for failed ASINs...", "step")
                logs = prompt.crawl_amazon_data(excel_filename)
                if logs and isinstance(logs, list):
                    for log in logs:
                        if isinstance(log, str):
                            if log.startswith("✅"):
                                add_log_to_sidebar(log, "success")
                            elif log.startswith("❌"):
                                add_log_to_sidebar(log, "error")
                            elif log.startswith("⚠️"):
                                add_log_to_sidebar(log, "warning")
                            else:
                                add_log_to_sidebar(log, "info")
                else:
                    add_log_to_sidebar("Retry fetch completed", "info")
                
                add_log_to_sidebar("Retry failed ASINs completed!", "success")
                end_log_group()
                
                st.success("✅ Retried ASINs with missing titles. Check Excel again.")
                st.session_state.info_ready = True
                st.rerun()
            except Exception as e:
                add_log_to_sidebar(f"Retry failed ASINs error: {str(e)}", "error")
                end_log_group()  
                st.error(f"Error retrying failed product info fetch: {e}")

# Step 4.2: Generate Prompts
st.subheader("4.2 Generate Prompts")
col3, col4 = st.columns(2)

with col3:
    if st.button("📋 Generate Base Prompts", key="btn_gen_base_prompts"):
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
        elif not st.session_state.get('duration_calculated'):
            st.warning("⚠️ Please calculate duration first in step 3.")
        else:
            try:
                start_log_group("Generate Base Prompts") 
                add_log_to_sidebar("🚀 Starting base prompts generation...", "step")
                prompt.generate_base_prompts(excel_filename)
                add_log_to_sidebar("Base prompts generation completed!", "success")
                end_log_group()
                
                st.success("✅ Base prompts generated and saved to Excel!")
                st.session_state.prompt_ready = True
                st.rerun()
            except Exception as e:
                add_log_to_sidebar(f"Base prompts generation failed: {str(e)}", "error")
                end_log_group() 
                st.error(f"Error generating base prompts: {e}")

with col4:
    if st.button("🎯 Generate Final Prompts", key="btn_gen_final_prompts"):
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
        else:
            try:
                start_log_group("Generate Final Prompts")
                add_log_to_sidebar("🚀 Starting final prompts generation...", "step")
                prompt.generate_final_prompts(excel_filename)
                add_log_to_sidebar("Final prompts generation completed!", "success")
                end_log_group()
                
                st.success("✅ Final prompts generated and saved to Excel!")
                st.session_state.prompt_ready = True
                st.rerun()
            except Exception as e:
                add_log_to_sidebar(f"Final prompts generation failed: {str(e)}", "error")
                end_log_group() 
                st.error(f"Error generating final prompts: {e}")
            except Exception as e:
                st.error(f"Error generating final prompts: {e}")

# Step 4.3: Reset/Fix Invalid Data (if needed)
with st.expander("🔧 Reset/Fix Invalid Data (if needed)", expanded=False):
    st.info("Use these tools if you see 'nan' values or other invalid data that prevent processing.")
    
    col5, col6 = st.columns(2)
    
    with col5:
        if st.button("🧹 Clear Invalid Titles", key="btn_reset_titles"):
            if not os.path.exists(excel_filename):
                st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
            else:
                try:
                    start_log_group("Clear Invalid Titles")
                    add_log_to_sidebar("🚀 Starting clear invalid titles...", "step")
                    prompt.reset_product_titles(excel_filename)
                    add_log_to_sidebar("Invalid ProductTitle entries cleared!", "success")
                    end_log_group()
                    
                    st.success("✅ Invalid ProductTitle entries cleared!")
                    st.rerun()
                except Exception as e:
                    add_log_to_sidebar(f"Clear invalid titles failed: {str(e)}", "error")
                    end_log_group()
                    st.error(f"Error resetting titles: {e}")
    
    with col6:
        if st.button("🔧 Fix Invalid Prompts", key="btn_regenerate_prompts"):
            if not os.path.exists(excel_filename):
                st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
            else:
                try:
                    start_log_group("Fix Invalid Prompts")
                    
                    add_log_to_sidebar("🚀 Starting fix invalid prompts...", "step")
                    logs = prompt.regenerate_invalid_prompts(excel_filename)
                    for log in logs:
                        if log.startswith("✅"):
                            add_log_to_sidebar(log, "success")
                        elif log.startswith("❌"):
                            add_log_to_sidebar(log, "error")
                        elif log.startswith("⚠️"):
                            add_log_to_sidebar(log, "warning")
                        else:
                            add_log_to_sidebar(log, "info")
                    add_log_to_sidebar("Fix invalid prompts completed!", "success")
                    end_log_group()
                    st.success("✅ Invalid prompts have been regenerated!")
                    st.session_state.prompt_ready = True
                    st.rerun()
                except Exception as e:
                    add_log_to_sidebar(f"Fix invalid prompts failed: {str(e)}", "error")
                    end_log_group()  # Kết thúc group ngay cả khi có lỗi
                    st.error(f"Error regenerating prompts: {e}")
                except Exception as e:
                    st.error(f"Error regenerating prompts: {e}")

# Edit prompts if ready
if st.session_state.get("prompt_ready", False) or st.session_state.get("info_ready", False):
    if os.path.exists(excel_filename):
        try:
            df_full = pd.read_excel(excel_filename)
        except Exception as e:
            st.error(f"Error reading Excel '{os.path.basename(excel_filename)}' when editing Prompt: {e}")
            df_full = pd.DataFrame()
        if "ASIN" in df_full.columns:
            st.subheader("📝 Edit Prompts (spreadsheet)")

            available_columns = ["ASIN"]
            try:
                if "ProductTitle" in df_full.columns:
                    available_columns.append("ProductTitle")
                if "Bullets" in df_full.columns:
                    available_columns.append("Bullets")
                if "Prompt" in df_full.columns:
                    available_columns.append("Prompt")

                safe_columns = []
                for col in available_columns:
                    if col in df_full.columns:
                        safe_columns.append(col)
                
                if len(safe_columns) == 0 or "ASIN" not in safe_columns:
                    st.error("❌ Excel file structure is invalid. Please run previous steps to generate proper data.")
                    df_edit = pd.DataFrame()
                else:
                    try:
                        df_edit = df_full[df_full["ASIN"].apply(
                            lambda x: pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
                        )][safe_columns].copy()
                    except Exception:
                        st.error("❌ Failed to process Excel data. Please check your Excel file and run previous steps.")
                        df_edit = pd.DataFrame()
            except Exception:
                st.error("❌ Excel file has structural issues. Please regenerate your Excel file.")
                df_edit = pd.DataFrame()

                if not df_edit.empty:
                    column_config = {
                        "ASIN": st.column_config.Column(label="ASIN", disabled=True, width="small")
                    }

                    if "ProductTitle" in df_edit.columns and st.session_state.get("info_ready", False):
                        column_config["ProductTitle"] = st.column_config.Column(label="Product Title")
                    
                    if "Bullets" in df_edit.columns and st.session_state.get("info_ready", False):
                        column_config["Bullets"] = st.column_config.Column(label="Bullet Points")

                    if "Prompt" in df_edit.columns and st.session_state.get("prompt_ready", False):
                        column_config["Prompt"] = st.column_config.Column(label="Prompt")

                    edited = st.data_editor(
                        df_edit,
                        column_config=column_config,
                        num_rows="dynamic",
                        use_container_width=True,
                        key="prompt_data_editor"
                    )

                    if st.button("💾 Save edited Prompts", key="save_prompts"):
                        try:
                            df_new = df_full[df_full["ASIN"].isin(edited["ASIN"])].copy()
                            edited = edited.set_index("ASIN")
                            df_new = df_new.set_index("ASIN")
                            df_new.update(edited)
                            df_new = df_new.reset_index()
                            df_new.to_excel(excel_filename, index=False)
                            st.success("✅ Prompts saved to Excel!")
                        except Exception as e:
                            st.error(f"Error saving edited Prompts to Excel: {e}")
                else:
                    st.info("No valid ASINs found with data to edit. Please run previous steps first.")
        else:
            st.info("Excel file doesn't contain ASIN column. Please run previous steps first.")


st.header("✂️ 5. Generate Video Subtitles")
if st.button("🔖 Generate Subtitles from ProductTitle", key="btn_make_sub"):
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key:
        st.error("⚠️ Enter Gemini API Key first")
    else:
        start_log_group("Generate Video Subtitles")

        add_log_to_sidebar("🚀 Starting subtitle generation...", "step")
        logs = sub.main_web(api_key, excel_filename)
        for l in logs: 
            if l.startswith("✅"):
                add_log_to_sidebar(l, "success")
            elif l.startswith("❌"):
                add_log_to_sidebar(l, "error")
            elif l.startswith("⚠️"):
                add_log_to_sidebar(l, "warning")
            else:
                add_log_to_sidebar(l, "info")
        
        add_log_to_sidebar("Subtitle generation completed!", "success")
        end_log_group()
        st.session_state.subtitles_generated = True
        st.success("✅ Subtitle generation completed! Check sidebar for details.")
        st.rerun()

if st.session_state.get("subtitles_generated", False) or (os.path.exists(excel_filename) and "Subtitle" in pd.read_excel(excel_filename).columns):
    st.subheader("📝 Edit Subtitles")
    try:
        df_subtitle = pd.read_excel(excel_filename)
        
        if "Subtitle" in df_subtitle.columns and "ASIN" in df_subtitle.columns:
            available_sub_columns = ["ASIN", "Subtitle"]
            if "ProductTitle" in df_subtitle.columns:
                available_sub_columns.append("ProductTitle")
                
            df_subtitle_edit = df_subtitle[df_subtitle["ASIN"].apply(
                lambda x: pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
            )][available_sub_columns].copy()
            if not df_subtitle_edit.empty:
                
                column_config = {
                    "ASIN": st.column_config.Column(label="ASIN", disabled=True, width="small"),
                    "Subtitle": st.column_config.Column(label="Subtitle", width="large")
                }
                
                if "ProductTitle" in df_subtitle_edit.columns:
                    column_config["ProductTitle"] = st.column_config.Column(label="Product Title", disabled=True, width="large")
                
                edited_subtitles = st.data_editor(
                    df_subtitle_edit,
                    column_config=column_config,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="subtitle_editor",
                    disabled=["ASIN", "ProductTitle"]
                )
                
                # Check for changes
                try:
                    original_subtitles = df_subtitle_edit.reset_index(drop=True).to_dict('records')
                    edited_subtitles_data = edited_subtitles.reset_index(drop=True).to_dict('records')
                    has_subtitle_changes = original_subtitles != edited_subtitles_data
                except:
                    has_subtitle_changes = True
                
                if has_subtitle_changes:
                    st.warning("⚠️ You have unsaved subtitle changes!")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("💾 Save Subtitle Changes", key="save_subtitle_changes"):
                            try:
                                # Read original Excel
                                original_df = pd.read_excel(excel_filename)
                                
                                # Update subtitles for matching ASINs
                                for _, row in edited_subtitles.iterrows():
                                    asin = row["ASIN"]
                                    new_subtitle = row["Subtitle"]
                                    original_df.loc[original_df["ASIN"] == asin, "Subtitle"] = new_subtitle
                                
                                # Save back to Excel
                                original_df.to_excel(excel_filename, index=False)
                                st.success("✅ Subtitle changes saved successfully!")
                                add_log_to_sidebar("Subtitles updated and saved", "success")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error saving subtitle changes: {e}")
                                add_log_to_sidebar(f"Error saving subtitles: {e}", "error")
                    
                    with col2:
                        if st.button("🔄 Discard Subtitle Changes", key="discard_subtitle_changes"):
                            st.rerun()
                else:
                    st.success("✅ Subtitles are up to date")
            else:
                st.info("No valid ASINs found with subtitles to edit.")
        else:
            st.info("No subtitle data found. Please generate subtitles first.")
            
    except Exception as e:
        st.error(f"Error loading subtitle data: {e}")
        add_log_to_sidebar(f"Error loading subtitles: {e}", "error")

# Generate Scripts
st.markdown("---")
st.header("🤖 6. Generate Scripts with Gemini")
if st.button("🚀 Auto-generate scripts", key="btn_gen_script_auto"):
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key:
        st.warning("⚠️ Please enter Google AI Studio API Key first.")
    elif not os.path.exists(excel_filename):
        st.error(f"Excel file {os.path.basename(excel_filename)} does not exist – run previous steps first.")
    else:
        try:
            # Bắt đầu log group cho Script Generation
            start_log_group("Script Generation")
            
            add_log_to_sidebar("🚀 Starting script generation...", "step")
            logs, good_script, bad_script = script_gemini.main_web(api_key, excel_file_path=excel_filename)
            st.success(f"✅ Scripts generated and saved to 'Script' column in Excel! ✅: {good_script}, ❌: {bad_script}")
            
            # Hiển thị detailed logs trong expander (main UI)
            with st.expander("📋 Detailed Script Generation Log", expanded=False):
                if isinstance(logs, list):
                    for log in logs:
                        if isinstance(log, str):
                            st.text(log)
                else:
                    st.text(str(logs))
            
            # Phân loại logs và gửi vào sidebar
            if isinstance(logs, list):
                for log in logs:
                    if isinstance(log, str):
                        if log.startswith("✅") or "Script OK" in log:
                            add_log_to_sidebar(log, "success")
                        elif log.startswith("❌") or "failed" in log.lower() or "error" in log.lower():
                            add_log_to_sidebar(log, "error")
                        elif log.startswith("⚠️") or "warning" in log.lower():
                            add_log_to_sidebar(log, "warning")
                        else:
                            add_log_to_sidebar(log, "info")
            else:
                # Nếu logs không phải list, add toàn bộ như info
                add_log_to_sidebar(str(logs), "info")
            
            add_log_to_sidebar(f"Script generation completed! ✅: {good_script}, ❌: {bad_script}", "success")
            
            # Kết thúc log group
            end_log_group()
            
        except Exception as e:
            add_log_to_sidebar(f"Script generation failed: {str(e)}", "error")
            end_log_group()  # Kết thúc group ngay cả khi có lỗi
            st.error(f"Error occurred during script generation: {e}")

# Text-to-Speech
st.markdown("---")
st.header("🔊 7. Convert Script to Voice (audio2)")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔊 Generate Voice", key="btn_tts_full"):
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
            add_log_to_sidebar(f"❌ Excel file {os.path.basename(excel_filename)} does not exist.", "error")
        elif not st.session_state.get("tts_cred_path") or not os.path.exists(st.session_state.get("tts_cred_path", "")):
            st.warning(f"You need to upload Text-to-Speech credentials file and ensure it's loaded successfully.")
            add_log_to_sidebar("❌ TTS credentials file not found.", "error")
        else:
            try:
                start_log_group("Voice Generation")
    
                add_log_to_sidebar("🚀 Starting voice generation (all ASINs)...", "step")

                df_check = pd.read_excel(excel_filename)
                if df_check.empty:
                    add_log_to_sidebar("❌ Excel file is empty - no data to process.", "error")
                    end_log_group()
                    st.error("Excel file is empty. Please run previous steps to populate data first.")
                else:
                    required_columns = ["ASIN", "Script"]
                    missing_columns = [col for col in required_columns if col not in df_check.columns]
                    if missing_columns:
                        add_log_to_sidebar(f"❌ Missing required columns: {missing_columns}. Please generate scripts first.", "error")
                        end_log_group()
                        st.error(f"Missing required columns: {missing_columns}. Please generate scripts first.")
                    else:
                        # Check if there are valid scripts to process
                        valid_scripts = df_check[df_check["Script"].notna() & (df_check["Script"] != "")]
                        if valid_scripts.empty:
                            add_log_to_sidebar("❌ No valid scripts found in Excel. Please generate scripts first.", "error")
                            end_log_group()
                            st.error("No valid scripts found in Excel. Please generate scripts first.")
                        else:
                            add_log_to_sidebar(f"Found {len(valid_scripts)} ASINs with scripts to process.", "info")
                            
                            logs_tts = tts.main_web(excel_path=excel_filename, tts_cred_filename=st.session_state.get("tts_cred_path"), audio2_folder=st.session_state.get("audio_output_folder", "./voice"), retry_mode=False)
                            for l_tts in logs_tts: 
                                if l_tts.startswith("✅"):
                                    add_log_to_sidebar(l_tts, "success")
                                elif l_tts.startswith("❌"):
                                    add_log_to_sidebar(l_tts, "error")
                                else:
                                    add_log_to_sidebar(l_tts, "info")
                            add_log_to_sidebar("Voice generation completed!", "success")

                            end_log_group()
                            
                            st.success("✅ Voice generation completed! Check sidebar for details.")
                            st.rerun()  # Force refresh để cập nhật sidebar
            except Exception as e:
                add_log_to_sidebar(f"Voice generation failed: {str(e)}", "error")
                end_log_group()  # Kết thúc group ngay cả khi có lỗi
                st.error(f"Error occurred during voice generation: {e}")

with col2:
    if st.button("🔁 Retry Unsatisfied Voice", key="btn_tts_retry"):
        if not os.path.exists(excel_filename):
            st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
            add_log_to_sidebar(f"❌ Excel file {os.path.basename(excel_filename)} does not exist.", "error")
        elif not st.session_state.get("tts_cred_path") or not os.path.exists(st.session_state.get("tts_cred_path", "")):
            st.warning(f"You need to upload Text-to-Speech credentials file and ensure it's loaded successfully.")
            add_log_to_sidebar("❌ TTS credentials file not found.", "error")
        else:
            try:
                start_log_group("Voice Generation Retry")
                
                add_log_to_sidebar("🚀 Starting voice generation retry (unsatisfied only)...", "step")
                df = pd.read_excel(excel_filename)
                if df.empty:
                    add_log_to_sidebar("❌ Excel file is empty - no data to process.", "error")
                    end_log_group()
                    st.error("Excel file is empty. Please run previous steps to populate data first.")
                else:
                    if "VoiceDurationCheck" in df.columns and "Audio2" in df.columns:
                        needs_retry = df[
                            (df["VoiceDurationCheck"].isna()) | 
                            (df["VoiceDurationCheck"].astype(str).str.lower().isin(['', 'nan', 'none'])) |
                            (df["Audio2"].isna()) | 
                            (df["Audio2"].astype(str).str.lower().isin(['', 'nan', 'none'])) |
                            (~df["Audio2"].astype(str).apply(lambda x: os.path.exists(str(x)) if pd.notna(x) and str(x).strip() != '' else False))
                        ]
                        
                        if len(needs_retry) > 0:
                            add_log_to_sidebar(f"Found {len(needs_retry)} ASINs needing voice retry", "info")
                            df.loc[needs_retry.index, "VoiceDurationCheck"] = ""
                            df.to_excel(excel_filename, index=False)
                            add_log_to_sidebar("Cleared VoiceDurationCheck for retry ASINs", "info")
                            
                            logs_tts = tts.main_web(excel_path=excel_filename, tts_cred_filename=st.session_state.get("tts_cred_path"), audio2_folder=st.session_state.get("audio_output_folder", "./voice"), retry_mode=True)
                            for l_tts in logs_tts: 
                                if l_tts.startswith("✅"):
                                    add_log_to_sidebar(l_tts, "success")
                                elif l_tts.startswith("❌"):
                                    add_log_to_sidebar(l_tts, "error")
                                else:
                                    add_log_to_sidebar(l_tts, "info")
                            add_log_to_sidebar("Voice generation retry completed!", "success")
                            
                            end_log_group()
                            
                            st.success("✅ Voice generation retry completed! Check sidebar for details.")
                            st.rerun()  # Force refresh để cập nhật sidebar
                        else:
                            add_log_to_sidebar("No ASINs found needing voice retry", "info")
                            end_log_group()
                            st.info("✅ All ASINs already have satisfactory voice generation!")
                    else:
                        add_log_to_sidebar("❌ No voice data columns found in Excel. Please run voice generation first.", "error")
                        end_log_group()
                        st.error("No voice data columns found in Excel. Please run voice generation first.")
            except Exception as e:
                add_log_to_sidebar(f"Voice generation retry failed: {str(e)}", "error")
                end_log_group()  # Kết thúc group ngay cả khi có lỗi
                st.error(f"Error occurred during voice generation retry: {e}")

# Review and Edit Voice Files
if os.path.exists(excel_filename):
    try:
        df_voice = pd.read_excel(excel_filename)
        
        # Check if voice-related columns exist and have data
        voice_columns_exist = any(col in df_voice.columns for col in ["Script", "Audio2", "VoiceDurationCheck"])
        has_voice_data = False
        
        if voice_columns_exist:
            # Check if there's actually voice data
            for col in ["Audio2", "VoiceDurationCheck"]:
                if col in df_voice.columns:
                    non_empty_data = df_voice[col].dropna().astype(str)
                    non_empty_data = non_empty_data[~non_empty_data.str.lower().isin(['nan', 'none', ''])]
                    if len(non_empty_data) > 0:
                        has_voice_data = True
                        break
        
        if has_voice_data:
            st.subheader("🎤 Review & Edit Voice Files")
            st.info("💡 **Tip**: To regenerate voice for specific ASINs, edit the Script and delete the VoiceDurationCheck value, then run 'Generate voice' again.")
            
            # Filter valid ASINs with voice data
            voice_edit_columns = ["ASIN", "ProductTitle", "Script", "Audio2", "VoiceDurationCheck"]
            available_columns = [col for col in voice_edit_columns if col in df_voice.columns]
            
            df_voice_edit = df_voice[df_voice["ASIN"].apply(
                lambda x: pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
            )][available_columns].copy()
            
            if not df_voice_edit.empty:
                show_voice_file = False
                if "Audio2" in df_voice_edit.columns:
                    has_empty_audio2 = df_voice_edit["Audio2"].apply(
                        lambda x: pd.isna(x) or str(x).strip() == '' or str(x).lower() == 'nan'
                    ).any()
                    
                    if has_empty_audio2:
                        show_voice_file = True
                        df_voice_edit["Audio2_FileName"] = df_voice_edit["Audio2"].apply(
                            lambda x: os.path.basename(str(x)) if pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan' else ""
                        )
                
                column_config = {
                    "ASIN": st.column_config.Column(label="ASIN", disabled=True, width="small"),
                    "ProductTitle": st.column_config.Column(label="Product Title", disabled=True, width="medium"),
                    "Script": st.column_config.Column(label="Script", width="large"),
                    "Audio2": st.column_config.Column(label="Audio2 Path", width="medium"),
                    "VoiceDurationCheck": st.column_config.Column(label="Voice Check", width="small")
                }
                
                if show_voice_file:
                    column_config["Audio2_FileName"] = st.column_config.Column(label="Voice File", disabled=True, width="small")
                
                # Remove columns that don't exist
                final_columns = [col for col in df_voice_edit.columns if col in column_config]
                column_config = {k: v for k, v in column_config.items() if k in final_columns}
                
                edited_voice = st.data_editor(
                    df_voice_edit[final_columns],
                    column_config=column_config,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="voice_data_editor",
                    disabled=["ASIN", "ProductTitle", "Audio2_FileName"]
                )
            else:
                st.info("No valid ASINs found with voice data to edit.")
                
    except Exception as e:
        st.error(f"Error loading voice data: {e}")
        add_log_to_sidebar(f"Error loading voice data: {e}", "error")

# Video Rendering
codecs = detect_gpu_codecs()
st.markdown("---")
st.header("🎞️ Render Video")

# Logo and subtitle customization
st.subheader("Customize logo position and size on video")
logo_scale_percent = st.slider("Logo size (%). Default 15%", min_value=5, max_value=50, value=15, step=1, key="logo_scale_slider")
VIDEO_W, VIDEO_H = 1920, 1080
max_margin = 1920 - int(1920 * (logo_scale_percent / 100))

if brand == "BlueStars":
    logo_x = st.slider("Distance from right edge (px)", 0, max_margin, 50, step=5, key="logo_x")
else:
    logo_x = st.slider("Distance from left edge (px)", 0, max_margin, 50, step=5, key="logo_x")

logo_y = st.slider("Distance from top edge (px)", 0, 1080, 50, step=5, key="logo_y")
logo_path = st.session_state.get("logo_filename_session_actual", "")
sub_text = st.text_input("🔤 Preview subtitle", value="Sample Product Title")

st.subheader("🎬 Customize subtitles")
subtitle_align = st.selectbox("Subtitle horizontal alignment:", options=["left", "center", "right"], index=1)
subtitle_y = st.slider("Distance from top (px)", min_value=0, max_value=VIDEO_H-50, value=VIDEO_H-150, step=5)
subtitle_fontsize = st.slider("Font size (px)", min_value=30, max_value=120, value=85, step=1)
subtitle_borderw = st.slider("Border thickness (px)", min_value=0, max_value=10, value=2, step=1)
subtitle_fontcolor = st.color_picker("Font color", value="#000000")
subtitle_bordercolor = st.color_picker("Border color", value="#FFFFFF")
subtitle_margin = st.slider("Side margins (px)", min_value=10, max_value=300, value=100)
subtitle_min_fontsize = st.slider("Minimum font size (px)", min_value=10, max_value=50, value=30)

# Preview
st.subheader("Preview logo & subtitle")
if logo_path and os.path.exists(logo_path):
    canvas = Image.new("RGB", (VIDEO_W, VIDEO_H), (30, 30, 30))
    draw = ImageDraw.Draw(canvas)

    logo = Image.open(logo_path)
    w = int(VIDEO_W * (logo_scale_percent / 100))
    h = int(logo.height * w / logo.width)
    logo = logo.resize((w, h), Image.Resampling.LANCZOS)
    
    px = VIDEO_W - w - logo_x if brand == "BlueStars" else logo_x
    py = logo_y
    
    if logo.mode == "RGBA":
        canvas.paste(logo, (px, py), logo)
    else:
        canvas.paste(logo, (px, py))

    try:
        font = ImageFont.truetype("arialbd.ttf", size=80)
        bbox = draw.textbbox((0, 0), sub_text, font=font)
        text_w = bbox[2] - bbox[0]
        sub_x = (VIDEO_W - text_w) // 2

        for dx in (-subtitle_borderw, subtitle_borderw):
            for dy in (-subtitle_borderw, subtitle_borderw):
                draw.text((sub_x + dx, subtitle_y + dy), sub_text, font=font, fill=subtitle_bordercolor)
        draw.text((sub_x, subtitle_y), sub_text, font=font, fill=subtitle_fontcolor)
    except:
        pass

    st.image(canvas, caption="Logo + Subtitle Preview", use_container_width=True)
else:
    st.info("No logo uploaded yet.")

# Volume adjustment
st.subheader("Adjust volume")
audio1_vol_percent = st.slider("Audio1 (Background music) volume (%)", min_value=0, max_value=100, value=10 if brand == "BlueStars" else 8)
audio2_vol_percent = st.slider("Audio2 (Main voice) volume (%)", min_value=0, max_value=100, value=100)

# Codec selection
st.subheader("🎞️ Select Render Codec")
if not codecs or len(codecs) <= 1:
    st.warning("No GPU codecs found. Will use CPU (libx264).")
    selected_codec = 'libx264'
    st.write(f"Selected codec: {selected_codec}")
else:
    if 'h264_nvenc' in codecs:
        default_index = codecs.index('h264_nvenc')
    else:
        default_index = 0
    selected_codec = st.selectbox("Select codec for video rendering:", codecs, index=default_index, key="render_codec_select")

# Media2 processing options
st.subheader("Media2 processing options")
cut_media2 = st.checkbox("✂️ Cut 9s from middle of Media2 video (recommended if Media2 is long)", value=True)

if st.button("Render video", key="btn_video"):
    if not os.path.exists(excel_filename):
        st.error(f"Excel file {os.path.basename(excel_filename)} does not exist.")
    else:
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
                st.info(f"Created output folder: {output_folder}")
            except Exception as e:
                st.error(f"Error creating output folder {output_folder}: {e}")
                st.stop()

        add_log_to_sidebar("🚀 Starting video rendering...", "step")
        logs_video, rendered_paths = video.main_web(
            excel_file=excel_filename,
            output_root=output_folder,
            logo_scale_percent=logo_scale_percent,
            logo_x=logo_x,
            logo_y=logo_y,
            brand=brand,
            bluestars_outtro_path=bluestars_outtro_path,
            codecs=selected_codec,
            audio1_volume=audio1_vol_percent / 100,
            audio2_volume=audio2_vol_percent / 100,
            cut_media2=cut_media2,
            subtitle_align=subtitle_align,
            subtitle_y=subtitle_y,
            subtitle_fontsize=subtitle_fontsize,
            subtitle_fontcolor=subtitle_fontcolor,
            subtitle_borderw=subtitle_borderw,
            subtitle_bordercolor=subtitle_bordercolor,
            subtitle_margin=subtitle_margin,
            subtitle_min_fontsize=subtitle_min_fontsize
        )

        success_logs = []
        error_logs = []
        info_logs = []
        
        for msg in logs_video:
            if msg.startswith("✅"):
                success_logs.append(msg)
            elif msg.startswith("❌"):
                error_logs.append(msg)
            else:
                info_logs.append(msg)
        
        # Gửi logs to sidebar theo batch để tăng tốc
        for msg in success_logs:
            add_log_to_sidebar(msg, "success")
        for msg in error_logs:
            add_log_to_sidebar(msg, "error")
        for msg in info_logs:
            add_log_to_sidebar(msg, "info")
    
        # Lưu rendered paths và reset preview state
        st.session_state["rendered_video_paths"] = rendered_paths
        if rendered_paths:
            st.session_state["show_video_preview"] = True

        success_count = len(rendered_paths)
        if success_count:
            add_log_to_sidebar(f"Video rendering completed! {success_count} videos rendered successfully.", "success")
            st.success(f"🎉 Successfully rendered {success_count} videos! Check sidebar for details.")
        else:
            add_log_to_sidebar("Video rendering failed - no videos were rendered successfully.", "error")
            st.error("⚠️ No videos were rendered successfully.")
        
        # Đánh dấu rằng render đã hoàn thành để tránh rerun loop
        st.session_state["render_completed"] = True

    # Preview videos trong expander để tiết kiệm tài nguyên
    rendered_paths = st.session_state.get("rendered_video_paths", [])
    if rendered_paths and st.session_state.get("show_video_preview", False):
        with st.expander("🎬 Preview Rendered Videos", expanded=False):
            if st.button("🗑️ Clear Previews", key="clear_video_preview"):
                st.session_state.rendered_video_paths = []
                st.session_state.show_video_preview = False
                st.rerun()
            
            for path in rendered_paths:
                if os.path.exists(path):
                    asin_preview = os.path.basename(path).split(".")[0]
                    st.markdown(f"**ASIN: {asin_preview}**")
                    st.video(path)
                else:
                    st.warning(f"Video file not found: {path}")

st.markdown("---")
st.header("🚀 9. Run Complete Pipeline")
st.warning("Chọn một quy trình cài đặt sẵn hoặc tùy chỉnh các bước chi tiết bên dưới.")

# 1. Định nghĩa TẤT CẢ các bước trong pipeline và hàm thực thi tương ứng
# Điều này giúp quản lý code tập trung và dễ dàng hơn.
PIPELINE_STEPS = {
    "get_add": {
        "name": "📊 Chuẩn bị",
        "func": lambda: get_add.main_web(
            excel_path=excel_filename,
            asin_folder_root=input_folder,
            static_media1_path=st.session_state.get('logo_filename_session_actual', '')
        )
    },
    "duration": {
        "name": "⏱️ Tính thời lượng", 
        "func": lambda: get_add.calculate_duration(input_excel=excel_filename, output_excel=excel_filename)
    },
    "crawl": {
        "name": "🔍 Info sản phẩm", 
        "func": lambda: prompt.crawl_amazon_data(excel_filename)
    },
    "prompts": {
        "name": "📝 Tạo prompt", 
        "func": lambda: (prompt.generate_base_prompts(excel_filename), prompt.generate_final_prompts(excel_filename))
    },
    "subtitles": {
        "name": "✂️ Tạo sub", 
        "func": lambda: sub.main_web(st.session_state.get("gemini_api_key", ""), excel_filename)
    },
    "scripts": {
        "name": "🤖 Script", 
        "func": lambda: script_gemini.main_web(st.session_state.get("gemini_api_key", ""), excel_file_path=excel_filename)
    },
    "voice": {
        "name": "🔊 Voice", 
        "func": lambda: tts.main_web(excel_path=excel_filename, tts_cred_filename=st.session_state.get("tts_cred_path"), audio2_folder=st.session_state.get("audio_output_folder", "./voice"))
    },
    "render": {
        "name": "🎞️ Render", 
        "func": lambda: video.main_web(
            excel_file=excel_filename,
            output_root=output_folder,
            brand=st.session_state.get('brand_selection', 'Canamax'),
            bluestars_outtro_path=st.session_state.get('bluestars_outtro_filename_session', ''),
            logo_scale_percent=st.session_state.get('logo_scale_slider', 15),
            logo_x=st.session_state.get('logo_x', 50),
            logo_y=st.session_state.get('logo_y', 50),
            audio1_volume=st.session_state.get('audio1_vol_percent', 
                13 if st.session_state.get('brand_selection', 'Canamax') == 'BlueStars' else 8
            ) / 100,
            audio2_volume=st.session_state.get('audio2_vol_percent', 100) / 100,
            cut_media2=st.session_state.get('cut_media2', True),
            subtitle_align=st.session_state.get('subtitle_align', 'center'),
            subtitle_y=st.session_state.get('subtitle_y', VIDEO_H-150),
            subtitle_fontsize=st.session_state.get('subtitle_fontsize', 85),
            subtitle_borderw=st.session_state.get('subtitle_borderw', 2),
            subtitle_fontcolor=st.session_state.get('subtitle_fontcolor', '#000000'),
            subtitle_bordercolor=st.session_state.get('subtitle_bordercolor', '#FFFFFF'),
            subtitle_margin=st.session_state.get('subtitle_margin', 100),
            subtitle_min_fontsize=st.session_state.get('subtitle_min_fontsize', 30)
        )
    }
}

# 2. Định nghĩa các "Gói quy trình" (presets)
PIPELINE_PRESETS = {
    "Chuẩn bị data": ['get_add', 'duration', 'crawl', 'prompts'],
    "Sub + Voice": ['subtitles', 'scripts', 'voice'],
    "Render": ['render'],
    "Full": ['get_add', 'duration', 'crawl', 'prompts', 'subtitles', 'scripts', 'voice', 'render'],
    "Tuỳ chỉnh": []
}

# 3. Các hàm callback để cập nhật giao diện một cách thông minh
def update_steps_from_preset():
    preset = st.session_state.get("pipeline_preset", "Tuỳ chỉnh")
    if preset != "Tuỳ chỉnh":
        steps_to_run = PIPELINE_PRESETS[preset]
        for step_key in PIPELINE_STEPS.keys():
            st.session_state[f"cb_{step_key}"] = (step_key in steps_to_run)

def set_preset_to_custom():
    st.session_state["pipeline_preset"] = "Custom"

# 4. Giao diện người dùng
st.radio(
    "Chọn một gói quy trình:",
    options=PIPELINE_PRESETS.keys(),
    key="pipeline_preset",
    horizontal=True,
    on_change=update_steps_from_preset
)

st.write("**Các bước chi tiết sẽ được thực thi:**")

cols = st.columns(4)
step_keys = list(PIPELINE_STEPS.keys())
for i, key in enumerate(step_keys):
    # Khởi tạo giá trị mặc định cho checkbox nếu chưa có
    if f"cb_{key}" not in st.session_state:
        st.session_state[f"cb_{key}"] = True
    with cols[i % 4]:
        st.checkbox(
            PIPELINE_STEPS[key]['name'], 
            key=f"cb_{key}",
            on_change=set_preset_to_custom
        )

# 5. Nút chạy chính với logic đã được sửa lỗi
if st.button("🏃‍♂️ Chạy các bước đã chọn", key="btn_run_selected", type="primary", use_container_width=True):
    api_key = st.session_state.get("gemini_api_key", "").strip()
    if not api_key:
        st.error("⚠️ Vui lòng nhập Gemini API Key ở mục 1.")
        st.stop()
    if not os.path.exists(excel_filename):
        st.error("⚠️ Vui lòng chuẩn bị media và tạo file Excel ở các bước trên trước.")
        st.stop()

    # Lấy danh sách các bước đã được chọn từ session_state
    steps_to_execute = {}
    for key, step in PIPELINE_STEPS.items():
        if st.session_state.get(f"cb_{key}"):
            steps_to_execute[key] = step
    total_steps = len(steps_to_execute)
    current_step_num = 0

    if total_steps == 0:
        st.warning("Bạn chưa chọn bước nào để chạy.")
        st.stop()

    progress_bar = st.progress(0, text="Bắt đầu pipeline...")
    
    for key, step_info in steps_to_execute.items():
        current_step_num += 1
        current_step_name = step_info['name']
        progress_text = f"({current_step_num}/{total_steps}) Đang chạy: {current_step_name}"
        
        start_log_group(current_step_name)
        add_log_to_sidebar(f"🚀 Starting: {current_step_name}", "step")
        progress_bar.progress(current_step_num / total_steps, text=progress_text)
        
        try:
            # Gọi hàm tương ứng với proper error handling
            result = step_info['func']()
            
            # Phân loại và gửi log sang sidebar
            if isinstance(result, tuple):
                # Handle tuple results (e.g., from video.main_web which returns logs, paths)
                if len(result) >= 1 and isinstance(result[0], list):
                    for log_message in result[0]:
                        if isinstance(log_message, str):
                            if log_message.startswith("✅"):
                                add_log_to_sidebar(log_message, "success")
                            elif log_message.startswith("❌"):
                                add_log_to_sidebar(log_message, "error")
                            elif log_message.startswith("⚠️"):
                                add_log_to_sidebar(log_message, "warning")
                            else:
                                add_log_to_sidebar(log_message, "info")
            elif isinstance(result, list):
                for log_message in result:
                    if isinstance(log_message, str):
                        if log_message.startswith("✅"):
                            add_log_to_sidebar(log_message, "success")
                        elif log_message.startswith("❌"):
                            add_log_to_sidebar(log_message, "error")
                        elif log_message.startswith("⚠️"):
                            add_log_to_sidebar(log_message, "warning")
                        else:
                            add_log_to_sidebar(log_message, "info")
            else:
                add_log_to_sidebar(f"Step {current_step_name} completed", "info")
        
            add_log_to_sidebar(f"✅ Completed: {current_step_name}", "success")
            
        except Exception as e:
            error_msg = f"Error in {current_step_name}: {str(e)}"
            add_log_to_sidebar(error_msg, "error")
            st.error(f"❌ {error_msg}")
            # Continue with next step instead of stopping entire pipeline
        finally:
            end_log_group()

    add_log_to_sidebar("Pipeline execution finished!", "success")
    st.success("🎉 Pipeline execution completed! Check sidebar for detailed results.")
    progress_bar.progress(1.0, text="Hoàn tất!")

    if st.session_state.get("cb_prompts", False) or st.session_state.get("cb_crawl", False) or st.session_state.get("cb_subtitles", False) or st.session_state.get("cb_scripts", False):
        try:
            df_review = pd.read_excel(excel_filename)
            
            if not df_review.empty:
                st.subheader("✏️ Review and Edit All Data")

                # Lọc chỉ những rows có ASIN hợp lệ để edit
                df_review_filtered = df_review[df_review["ASIN"].apply(
                    lambda x: pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
                )].copy()
                
                if not df_review_filtered.empty:
  
                    essential_columns = ["ASIN"]
                    
                    # Kiểm tra và thêm các cột có dữ liệu
                    if "ProductTitle" in df_review_filtered.columns and not df_review_filtered["ProductTitle"].isna().all():
                        essential_columns.append("ProductTitle")
                    
                    if "Bullets" in df_review_filtered.columns and not df_review_filtered["Bullets"].isna().all():
                        essential_columns.append("Bullets")
                    
                    if "Prompt" in df_review_filtered.columns and not df_review_filtered["Prompt"].isna().all():
                        essential_columns.append("Prompt")
                    
                    if "Subtitle" in df_review_filtered.columns and not df_review_filtered["Subtitle"].isna().all():
                        essential_columns.append("Subtitle")
                        
                    if "Script" in df_review_filtered.columns and not df_review_filtered["Script"].isna().all():
                        essential_columns.append("Script")
                    
                    # Chỉ hiển thị các cột có dữ liệu
                    df_display = df_review_filtered[essential_columns].copy()
                    st.info(f"📊 Showing {len(essential_columns)-1} essential columns with data. Click 'Show All Columns' to see everything.")
                
                    column_config = {
                        "ASIN": st.column_config.Column(label="ASIN", disabled=True, width="small")
                    }
                    
                    for col in df_display.columns:
                        if col != "ASIN":
                            if col == "ProductTitle":
                                column_config[col] = st.column_config.Column(label="Product Title", width="medium")
                            elif col == "Bullets":
                                column_config[col] = st.column_config.Column(label="Bullet Points", width="large")
                            elif col == "Prompt":
                                column_config[col] = st.column_config.Column(label="Prompt", width="large")
                            elif col == "Subtitle":
                                column_config[col] = st.column_config.Column(label="Subtitle", width="medium")
                            elif col == "Script":
                                column_config[col] = st.column_config.Column(label="Script", width="large")
                            elif col == "Duration":
                                column_config[col] = st.column_config.Column(label="Duration", width="small")
                            else:
                                column_config[col] = st.column_config.Column(label=col, width="medium")

                    edited = st.data_editor(
                        df_display,
                        column_config=column_config,
                        num_rows="dynamic",
                        use_container_width=True,  # Key khác nhau cho 2 mode
                        disabled=["ASIN"]
                    )
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        if st.button("💾 Save All Changes", key="save_pipeline_reviewed_data", type="primary"):
                            try:
                                # Đọc file Excel gốc
                                original_df = pd.read_excel(excel_filename)
                                
                                # Update dữ liệu từ edited data
                                for _, edited_row in edited.iterrows():
                                    asin = edited_row["ASIN"]
                                    mask = original_df["ASIN"] == asin
                                    
                                    # Update từng cột có trong edited data (trừ ASIN)
                                    for col in edited.columns:
                                        if col != "ASIN" and col in original_df.columns:
                                            original_df.loc[mask, col] = edited_row[col]
                                
                                # Lưu file
                                original_df.to_excel(excel_filename, index=False)
                                
                                st.success("✅ All changes saved successfully!")
                                add_log_to_sidebar("💾 Pipeline review data saved to Excel", "success")
                                
                            except Exception as e:
                                st.error(f"Error saving changes to Excel: {e}")
                                add_log_to_sidebar(f"❌ Save error: {e}", "error")
                    
                    with col2:
                        if st.button("🔄 Reload Data", key="reload_pipeline_data_only"):
                            st.rerun()
                    
                    with st.expander("🔧 Data có lỗi thì dùng các tool sau", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("🧹 Xoá các Title hiện là 'nan'", key="pipeline_clear_titles"):
                                try:
                                    prompt.reset_product_titles(excel_filename)
                                    add_log_to_sidebar("Invalid ProductTitles cleared", "success")
                                    st.success("✅ Invalid titles cleared!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                                    add_log_to_sidebar(f"Clear titles error: {e}", "error")
                        
                        with col2:
                            if st.button("🔁 Cào lại data những ASIN bị fail", key="pipeline_retry_crawl"):
                                try:
                                    logs = prompt.crawl_amazon_data(excel_filename)
                                    for log in logs:
                                        if log.startswith("✅"):
                                            add_log_to_sidebar(log, "success")
                                        elif log.startswith("❌"):
                                            add_log_to_sidebar(log, "error")
                                        else:
                                            add_log_to_sidebar(log, "info")
                                    st.success("✅ Retried failed crawls!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                                    add_log_to_sidebar(f"❌ Lỗi khi cào lại: {e}", "error")
                        
                        with col3:
                            if st.button("🔄 Tải lại Excel", key="reload_pipeline_data"):
                                st.rerun()
                                
                    with st.expander("📁 Export/Import Options", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("📥 Download Excel File", key="download_excel"):
                                with open(excel_filename, "rb") as f:
                                    st.download_button(
                                        label="💾 Download Current Excel",
                                        data=f.read(),
                                        file_name=f"exported_{os.path.basename(excel_filename)}",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                        
                        with col2:
                            uploaded_excel = st.file_uploader(
                                "📤 Upload Excel to Replace", 
                                type=["xlsx"], 
                                key="upload_excel_replace"
                            )
                            if uploaded_excel and st.button("🔄 Replace Current Excel", key="replace_excel"):
                                try:
                                    # Backup current file
                                    backup_name = f"backup_{excel_filename}"
                                    shutil.copy2(excel_filename, backup_name)
                                    
                                    # Save uploaded file
                                    with open(excel_filename, "wb") as f:
                                        f.write(uploaded_excel.getbuffer())
                                    
                                    st.success(f"✅ Excel replaced! Backup saved as {backup_name}")
                                    add_log_to_sidebar("📤 Excel file replaced via upload", "success")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error replacing Excel: {e}")
                                    add_log_to_sidebar(f"❌ Excel replace error: {e}", "error")
                
                else:
                    st.info("No valid data found for review.")
                    
            else:
                st.info("Excel file is empty or could not be read.")
                
        except Exception as e:
            st.error(f"Error loading data for review: {e}")
            add_log_to_sidebar(f"❌ Review data error: {e}", "error")

# Cleanup
st.markdown("---")
st.header("🧹 Clean file thừa sau khi chạy xong")
st.info("**Clean Excel Temp**: Remove the **Excel temp** file to start fresh.")
if st.button("🗑️ Xoá file tạm Excel", key="btn_cleanup_excel_only"):
    clean.manual_cleanup_excel_only()