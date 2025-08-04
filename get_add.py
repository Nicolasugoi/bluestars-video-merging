import os
import re
import pandas as pd
from typing import List
import cv2

def get_video_duration(video_path: str) -> float:
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            if fps > 0:
                return frame_count / fps
    except Exception as e:
        print(f"Lỗi đọc video {video_path}: {str(e)}")
    return 0

def get_media_durations(media_paths: List[str]) -> List[float]:
    durations = []
    for p in media_paths:
        if not os.path.exists(p):
            durations.append(0)
            continue
            
        file_ext = os.path.splitext(p)[1].lower()
        if file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            duration = get_video_duration(p)
            durations.append(duration if duration > 0 else 0)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            durations.append(3)  # Default 3s for images
    return durations

def natural_sort_key(s: str): #Hỗ trợ sắp xếp tự nhiên (ví dụ: file_2.mp4 trước file_10.mp4).
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def rename_duplicate_files(media_files: List[str]) -> List[str]:
    """
    Xử lý các file trùng tên dựa trên duration:
    - File ngắn hơn -> Media2
    - File dài hơn -> Media3
    """
    if len(media_files) <= 1:
        return media_files

    # Group files by base name (không có (1))
    file_groups = {}
    for file_path in media_files:
        base_name = re.sub(r'\(1\)', '', os.path.basename(file_path))
        if base_name not in file_groups:
            file_groups[base_name] = []
        file_groups[base_name].append(file_path)

    renamed_files = []
    for base_name, files in file_groups.items():
        if len(files) == 1:
            renamed_files.append(files[0])
            continue

        files_with_duration = [(f, get_video_duration(f)) for f in files]
        files_with_duration.sort(key=lambda x: x[1])  # Sort by duration

        # Rename based on duration
        for i, (file_path, _) in enumerate(files_with_duration):
            dir_path = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            base_name_without_ext, ext = os.path.splitext(file_name)
            
            # Remove any existing (1) from base name
            base_name_without_ext = re.sub(r'\(1\)', '', base_name_without_ext)
            
            # Shorter file -> Media2, Longer file -> Media3
            if i == 0:  # Shorter duration
                new_name = f"{base_name_without_ext}{ext}"
            else:  # Longer duration
                new_name = f"{base_name_without_ext}_longer{ext}"
            
            new_path = os.path.join(dir_path, new_name)
            if file_path != new_path:
                try:
                    os.rename(file_path, new_path)
                    renamed_files.append(new_path)
                except:
                    renamed_files.append(file_path)
            else:
                renamed_files.append(file_path)

    return renamed_files

def calculate_duration(input_excel="all.xlsx", output_excel="all.xlsx") -> List[str]:
    log = []
    df = pd.read_excel(input_excel)
    
    # Tìm các cột media
    media_columns = [col for col in df.columns if col.startswith("Media") and col != "Media1"]
    
    durations = []
    for idx, row in df.iterrows():
        media_paths = [str(row[col]) for col in media_columns if pd.notna(row[col])]
        media_durations = get_media_durations(media_paths)
        estimated_duration = sum(media_durations)
        
        media_info = []
        for p, d in zip(media_paths, media_durations):
            if not os.path.exists(p):
                media_info.append(f"{os.path.basename(p)} [Không tìm thấy]")
                continue

            if d == 0:
                media_info.append(f"{os.path.basename(p)} [Lỗi đọc duration]")
            else:
                is_img = os.path.splitext(p)[1].lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                media_info.append(f"{os.path.basename(p)} [{'Ảnh: ' if is_img else ''}{d:.2f}s]")
                
        durations.append(estimated_duration)
        log.append(f"{'+ '.join(media_info)} = {estimated_duration:.2f}s")

    # Cập nhật cột Duration và lưu file
    df['Duration'] = durations
    df.to_excel(output_excel, index=False)
    log.append(f"✅ Update file {output_excel} với cột duration.")
    
    return log

def main_web(
    excel_path: str,
    asin_folder_root: str,
    static_media1_path: str = ""
) -> List[str]:
    log = []

    # 1. QUÉT ĐĨA VÀ XỬ LÝ TRÙNG TÊN
    if not os.path.isdir(asin_folder_root):
        log.append(f"❌ Lỗi: Không tìm thấy thư mục nguồn '{asin_folder_root}'.")
        return log

    disk_media_map = {}
    valid_extensions = ('.mp4', '.mov', '.avi', '.jpg', '.jpeg', '.png')
    asin_pattern = re.compile(r"([A-Z0-9]{10})")

    # Collect all media files first
    temp_media_map = {}
    for root, _, files in os.walk(asin_folder_root):
        for filename in files:
            if filename.lower().endswith(valid_extensions):
                match = asin_pattern.search(filename.upper())
                if match:
                    asin = match.group(1)
                    if asin not in temp_media_map:
                        temp_media_map[asin] = []
                    temp_media_map[asin].append(os.path.join(root, filename))

    # Process and rename duplicate files
    for asin, media_files in temp_media_map.items():
        # Only process video files for renaming
        video_files = [f for f in media_files if f.lower().endswith(('.mp4', '.mov', '.avi'))]
        other_files = [f for f in media_files if not f.lower().endswith(('.mp4', '.mov', '.avi'))]
        
        if len(video_files) > 1:
            log.append(f"🔄 Xử lý {len(video_files)} file video cho ASIN {asin}")
            renamed_videos = rename_duplicate_files(video_files)
            disk_media_map[asin] = renamed_videos + other_files
        else:
            disk_media_map[asin] = media_files

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
        
    max_media_count = max((len(paths) for paths in disk_media_map.values()), default=0)
    required_media_cols = [f"Media{i}" for i in range(1, max_media_count + 2)]  # +1 cho Media1 (static), +1 cho số lượng file

    for col_name in required_media_cols:
        if col_name not in df.columns:
            df[col_name] = pd.Series(dtype='object')
        else:
            if df[col_name].dtype != 'object':
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