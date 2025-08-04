import os
import pandas as pd
import subprocess # Sử dụng subprocess để gọi ffprobe

def get_duration_with_ffprobe(file_path: str) -> float:
    """
    Lấy thời lượng của file media một cách nhanh chóng bằng ffprobe.
    Trả về 0.0 nếu có lỗi hoặc không phải file video/audio.
    """
    # Lệnh ffprobe để lấy duration và chỉ in ra giá trị
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        # Chạy lệnh và lấy output
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, encoding='utf-8', errors='replace')
        return float(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        # Trả về 0 nếu lệnh lỗi, không tìm thấy ffprobe, hoặc output không phải là số
        return 0.0

def main_web(input_excel="all.xlsx", output_excel="all.xlsx"):
    log = []
    df = pd.read_excel(input_excel)
    
    # Giữ nguyên logic tìm các cột media
    media_columns = [col for col in df.columns if col.startswith("Media") and col != "Media1"]
    
    durations = []
    for idx, row in df.iterrows():
        media_paths = [str(row[col]) for col in media_columns if pd.notna(row[col])]
        estimated_duration = 0
        media_info = []
        for p in media_paths:
            if not os.path.exists(p):
                media_info.append(f"{os.path.basename(p)} [Không tìm thấy]")
                continue

            file_ext = os.path.splitext(p)[1].lower()
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                duration = get_duration_with_ffprobe(p)
                if duration > 0:
                    estimated_duration += duration
                    media_info.append(f"{os.path.basename(p)} [{duration:.2f}s]")
                else:
                    media_info.append(f"{os.path.basename(p)} [Lỗi đọc duration]")
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                estimated_duration += 3
                media_info.append(f"{os.path.basename(p)} [Ảnh: 3.00s]")
        durations.append(estimated_duration)
        asin = row.get('ASIN', 'N/A')
        log.append(f"{'+ '.join(media_info)} = {estimated_duration:.2f}s")

    # Cập nhật cột Duration và lưu file
    df['Duration'] = durations
    df.to_excel(output_excel, index=False)
    log.append(f"✅ Update file {output_excel} với cột duration.")
    
    return log