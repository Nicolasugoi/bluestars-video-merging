import os
import pickle
import json
import concurrent.futures
from typing import List, Dict
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- CÁC HÀM XÁC THỰC VÀ TIỆN ÍCH GIỮ NGUYÊN ---
def authenticate_oauth(client_secret_path, token_pickle, scopes=SCOPES):
    creds = None
    if os.path.exists(token_pickle):
        with open(token_pickle, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_pickle, "wb") as f:
            pickle.dump(creds, f)
    return build("drive", "v3", credentials=creds)

def authenticate_sa(credentials_file: str):
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def extract_folder_id(link_or_id: str) -> str:
    import re
    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', link_or_id)
    return m.group(1) if m else link_or_id.strip()

def list_drive_contents(service, folder_id: str) -> List[Dict]:
    query = f"'{folder_id}' in parents and trashed=false"
    result = service.files().list(
        q=query, fields="files(id,name,mimeType)", supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    return result.get('files', [])

def find_existing_file(service, file_name: str, parent_folder_id: str) -> str:
    query = f"name='{file_name}' and '{parent_folder_id}' in parents and trashed=false"
    try:
        result = service.files().list(
            q=query, fields="files(id,name)", supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = result.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"Lỗi khi tìm kiếm file: {e}")
        return None

# --- ⭐ LOGIC DOWNLOAD TỐI ƯU MỚI ---

def _discover_files_recursive(service, item_id: str, item_name: str, current_path: str, files_to_download: list):
    """
    (Hàm nội bộ) Đệ quy để khám phá tất cả các file trong cây thư mục.
    """
    # Tạo đường dẫn cho thư mục hiện tại
    folder_path = os.path.join(current_path, item_name)
    os.makedirs(folder_path, exist_ok=True)
    
    # Lấy danh sách item con
    sub_items = list_drive_contents(service, item_id)
    for sub_item in sub_items:
        if sub_item['mimeType'] == 'application/vnd.google-apps.folder':
            # Nếu là thư mục, tiếp tục đệ quy
            _discover_files_recursive(service, sub_item['id'], sub_item['name'], folder_path, files_to_download)
        else:
            # Nếu là file, thêm vào danh sách cần tải
            file_info = {
                'id': sub_item['id'],
                'name': sub_item['name'],
                'save_path': os.path.join(folder_path, sub_item['name'])
            }
            files_to_download.append(file_info)

def _download_worker(service, file_info: Dict) -> str:
    """
    (Hàm nội bộ) Worker để tải xuống một file duy nhất.
    """
    file_id = file_info['id']
    save_path = file_info['save_path']
    try:
        request = service.files().get_media(fileId=file_id)
        with open(save_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return f"✅ Đã tải xuống: {save_path}"
    except Exception as e:
        return f"❌ Lỗi khi tải {os.path.basename(save_path)}: {e}"

def download_selected(service, items: List[Dict], download_path: str, max_workers: int = 10) -> List[str]:
    """
    Tải xuống các file và thư mục được chọn với hiệu suất cao.
    """
    files_to_download = []
    
    # Bước 1: Khám phá tất cả các file
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            _discover_files_recursive(service, item['id'], item['name'], download_path, files_to_download)
        else:
            # Xử lý các file được chọn ở cấp cao nhất
            file_info = {
                'id': item['id'],
                'name': item['name'],
                'save_path': os.path.join(download_path, item['name'])
            }
            files_to_download.append(file_info)
    
    if not files_to_download:
        return ["Không có file nào để tải."]

    log = [f"🔎 Tìm thấy {len(files_to_download)} file. Bắt đầu tải xuống..."]
    
    # Bước 2: Thực thi tải xuống đồng thời
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Tạo một partial function để truyền 'service' vào worker
        from functools import partial
        worker = partial(_download_worker, service)
        
        # Gửi tất cả các tác vụ download vào pool và thu thập kết quả
        results = list(executor.map(worker, files_to_download))
        log.extend(results)
            
    return log

# --- HÀM UPLOAD GIỮ NGUYÊN NHƯ PHIÊN BẢN TỐI ƯU TRƯỚC ---
def upload_files_to_drive(
    service,
    local_file_paths: List[str],
    parent_folder_id: str,
    overwrite: bool = False,
    max_workers: int = 5
) -> List[str]:
    log = []

    def _upload_file(local_path):
        if not os.path.exists(local_path):
            return f"⚠️ Bỏ qua file không tồn tại: {local_path}"
        
        file_name = os.path.basename(local_path)
        try:
            existing_file_id = None
            if overwrite:
                existing_file_id = find_existing_file(service, file_name, parent_folder_id)

            mimetype = 'video/mp4' if local_path.lower().endswith('.mp4') else None
            media = MediaFileUpload(local_path, mimetype=mimetype, resumable=True)

            if existing_file_id:
                file = service.files().update(
                    fileId=existing_file_id, media_body=media, fields='id, webViewLink', supportsAllDrives=True
                ).execute()
                return f"🔄 Đã ghi đè: {file_name} -> Link: {file.get('webViewLink')}"
            else:
                file_metadata = {'name': file_name, 'parents': [parent_folder_id]}
                file = service.files().create(
                    body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True
                ).execute()
                return f"✅ Đã tải lên: {file_name} -> Link: {file.get('webViewLink')}"
        except Exception as e:
            return f"❌ Lỗi khi tải lên {file_name}: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(_upload_file, path): path for path in local_file_paths}
        
        for future in concurrent.futures.as_completed(future_to_path):
            log.append(future.result())
            
    return log