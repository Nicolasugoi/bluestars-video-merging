# get_add.py (Phiên bản sửa lỗi FutureWarning)

import os
import re
import pandas as pd
from typing import List

def natural_sort_key(s: str):
    """Hỗ trợ sắp xếp tự nhiên (ví dụ: file_2.mp4 trước file_10.mp4)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def main_web(
    excel_path: str,
    asin_folder_root: str,
    static_media1_path: str = ""
) -> List[str]:
    log = []

    # 1. QUÉT ĐĨA
    if not os.path.isdir(asin_folder_root):
        log.append(f"❌ Lỗi: Không tìm thấy thư mục nguồn '{asin_folder_root}'.")
        return log

    disk_media_map = {}
    valid_extensions = ('.mp4', '.mov', '.avi', '.jpg', '.jpeg', '.png')
    asin_pattern = re.compile(r"([A-Z0-9]{10})")

    for root, _, files in os.walk(asin_folder_root):
        for filename in files:
            if filename.lower().endswith(valid_extensions):
                match = asin_pattern.search(filename.upper())
                if match:
                    asin = match.group(1)
                    if asin not in disk_media_map:
                        disk_media_map[asin] = []
                    disk_media_map[asin].append(os.path.join(root, filename))

    if not disk_media_map:
        log.append(f"⚠️ Không tìm thấy file media nào chứa mã ASIN hợp lệ trong '{asin_folder_root}'.")
        if os.path.exists(excel_path):
            pd.DataFrame().to_excel(excel_path, index=False)
            log.append(f"🧹 Đã xóa toàn bộ dữ liệu trong '{excel_path}' cho phiên làm việc mới.")
        return log

    log.append(f"🔎 Đã tìm thấy media cho {len(disk_media_map)} ASIN trên ổ đĩa.")
    asins_on_disk = set(disk_media_map.keys())

    # 2. ĐỌC FILE EXCEL
    try:
        df = pd.read_excel(excel_path)
        if 'ASIN' not in df.columns:
            df = pd.DataFrame(columns=['ASIN'])
        else:
            df['ASIN'] = df['ASIN'].astype(str)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['ASIN'])
        log.append(f"Tạo mới file Excel '{excel_path}'.")
    except Exception as e:
        log.append(f"❌ Lỗi đọc file Excel '{excel_path}': {e}. Sẽ tạo file mới.")
        df = pd.DataFrame(columns=['ASIN'])
        
    # ⭐ SỬA LỖI: Chủ động khai báo kiểu dữ liệu cho các cột Media
    # Điều này sẽ loại bỏ hoàn toàn cảnh báo FutureWarning
    for i in range(1, 50): # Giả định có tối đa 49 file media
        col_name = f"Media{i}"
        if col_name not in df.columns:
            df[col_name] = pd.Series(dtype='object') # Tạo cột mới với kiểu dữ liệu văn bản
        else:
            if df[col_name].dtype != 'object':
                # Ép kiểu cột đã có sang dạng văn bản, điền chuỗi rỗng cho các giá trị NaN
                df[col_name] = df[col_name].astype(str).replace('nan', '')

    # 3. ĐỒNG BỘ HÓA: Xóa các dòng không còn file
    existing_asins_in_excel = set(df['ASIN'].dropna())
    asins_to_remove = existing_asins_in_excel - asins_on_disk

    if asins_to_remove:
        removed_list = sorted(list(asins_to_remove))
        log.append(f"🧹 Sẽ xóa {len(removed_list)} ASIN không còn file trên đĩa: {', '.join(removed_list)}")
        df = df[~df['ASIN'].isin(asins_to_remove)].reset_index(drop=True)

    # 4. CẬP NHẬT VÀ THÊM MỚI
    for asin, media_paths in disk_media_map.items():
        sorted_paths = sorted(media_paths, key=natural_sort_key)
        row_indices = df.index[df['ASIN'] == asin].tolist()

        idx = row_indices[0] if row_indices else len(df)
        if not row_indices:
            df.loc[idx, 'ASIN'] = asin
        
        df.loc[idx, 'Media1'] = static_media1_path
        
        # Xóa dữ liệu Media cũ (từ Media2 trở đi)
        for i in range(2, 50):
            df.loc[idx, f"Media{i}"] = ""
        
        # Điền đường dẫn media mới
        for i, path in enumerate(sorted_paths):
            df.loc[idx, f"Media{i + 2}"] = path
            
    log.append(f"✅ Đã thêm/cập nhật thông tin media cho {len(disk_media_map)} ASIN.")

    # 5. LƯU FILE EXCEL
    try:
        df.dropna(axis=1, how='all', inplace=True)
        df.sort_values(by='ASIN', inplace=True, ignore_index=True)
        df.to_excel(excel_path, index=False)
        log.append(f"✅ Đã đồng bộ và lưu thành công file '{excel_path}'.")
    except Exception as e:
        log.append(f"❌ Lỗi nghiêm trọng khi lưu file Excel: {e}")

    return log