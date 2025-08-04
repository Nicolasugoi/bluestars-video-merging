import os
import shutil
import subprocess
import shlex
import multiprocessing
import pandas as pd
import traceback
import sys
import platform
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    concatenate_videoclips, concatenate_audioclips,
    CompositeAudioClip, CompositeVideoClip,
    TextClip, vfx
)
import PIL
import librosa
import soundfile as sf
import concurrent.futures
from PIL import ImageFont

# Ensure PIL uses the correct resampling filter if available
if hasattr(PIL.Image, 'Resampling'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

# Video constants
VIDEO_W, VIDEO_H = 1920, 1080
AUDIO_END_OFFSET = 0.15

def get_system_font():
    """Get system font path for different operating systems"""
    system = platform.system().lower()
    
    if system == 'windows':
        # Windows fonts
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/calibri.ttf"
        ]
    elif system == 'darwin':  # macOS
        font_paths = [
            "/System/Library/Fonts/Arial.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
    else:  # Linux and others
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/ubuntu/Ubuntu-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf"
        ]
    
    # Try to find an existing font
    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path
    
    # If no system font found, return None (will use default)
    return None

def get_ffmpeg_font_path():
    """Get font path for FFmpeg with proper escaping for different OS"""
    system = platform.system().lower()
    
    if system == 'windows':
        # Windows - use double backslashes for FFmpeg
        font_paths = [
            'C\\:/Windows/Fonts/arialbd.ttf',
            'C\\:/Windows/Fonts/arial.ttf',
            'C\\:/Windows/Fonts/calibrib.ttf'
        ]
    elif system == 'darwin':  # macOS
        font_paths = [
            '/System/Library/Fonts/Arial.ttc',
            '/System/Library/Fonts/Helvetica.ttc',
            '/Library/Fonts/Arial.ttf'
        ]
    else:  # Linux
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf'
        ]
    
    # For Windows, check actual file existence without escape chars
    if system == 'windows':
        for i, font_path in enumerate(font_paths):
            actual_path = font_path.replace('\\:/', ':/')
            if os.path.exists(actual_path):
                return font_path
    else:
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
    
    # Fallback to a generic font name
    return 'Arial' if system == 'windows' else 'DejaVu Sans'

def get_duration(path: str) -> float:
    """Get duration of media file with cross-platform compatibility"""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ]
    
    # Create subprocess with platform-specific settings
    startupinfo = None
    if platform.system() == 'Windows':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        res = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            startupinfo=startupinfo,
            encoding='utf-8',
            errors='replace'
        )
        return float(res.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0.0

def calculate_body_duration(media_paths: list, cut_media2: bool) -> float:
    total = 0.0
    for i, p in enumerate(media_paths):
        d = get_duration(p)
        if i == 0 and cut_media2:
            total += 5.0
        elif i == 1:
            total += min(d, 38.9)  # ⭐ THAY ĐỔI: 39.0 -> 38.9 để tổng còn 43.9s
        else:
            total += d
    return total

def create_video(
    asin: str,
    media_paths: list,
    audio1: str = None,
    audio2: str = None,
    logo_path: str = None,
    asin_folder: str = ".",
    logo_scale_percent: int = 15,
    logo_x: int = 50,
    logo_y: int = 50,
    brand: str = "Canamax",
    bluestars_outtro_path: str = None,
    codecs: str = "libx264",
    cut_media2: bool = True,
    audio1_volume: float = 0.1,
    audio2_volume: float = 1.0,
    sub_text: str = None,
    subtitle_align: str = "center",
    subtitle_y: int = 100,
    subtitle_fontsize: int = 85,
    subtitle_fontcolor: str = "#000000",
    subtitle_borderw: int = 2,
    subtitle_bordercolor: str = "#FFFFFF",
    subtitle_margin: int = 100,
    subtitle_min_fontsize: int = 30
) -> str:
    try:
        os.makedirs(asin_folder, exist_ok=True)
        out_path = os.path.join(asin_folder, f"{asin}.mp4")

        # Sửa trong hàm create_video, phần trim audio2:
        if audio2 and os.path.exists(audio2):
            body_dur = calculate_body_duration(media_paths, cut_media2)
            t = max(body_dur - 0.1, 0.0)  # ⭐ GIỮ NGUYÊN: vẫn trừ 0.1s
            # Nhưng đảm bảo không vượt quá 44.8s
            t = min(t, 44.8)  # ⭐ THÊM: giới hạn tối đa 44.8s
            a2_trim = os.path.join(asin_folder, f"{asin}_a2.wav")
            startupinfo = None
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.run(
                ["ffmpeg", "-y", "-i", audio2, "-t", f"{t:.3f}", a2_trim],
                check=True, 
                capture_output=True, 
                text=True,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace'
            )
            audio2 = a2_trim

        inputs = []
        idx_map = {"media": []}
        cur = 0

        for p in media_paths:
            inputs += ["-i", p]
            idx_map["media"].append(cur)
            cur += 1
        if bluestars_outtro_path and os.path.exists(bluestars_outtro_path):
            inputs += ["-t", "3", "-i", bluestars_outtro_path]
            idx_map["outtro"] = cur
            cur += 1
        if logo_path and os.path.exists(logo_path):
            inputs += ["-i", logo_path]
            idx_map["logo"] = cur
            cur += 1
        if audio2 and os.path.exists(audio2):
            inputs += ["-i", audio2]
            idx_map["audio2"] = cur
            cur += 1
        if audio1 and os.path.exists(audio1):
            inputs += ["-i", audio1]
            idx_map["audio1"] = cur
            cur += 1
        
        fc = []
        vlabels = []

        # Sửa phần xử lý video media thứ 2:
        for i, p in enumerate(media_paths):
            in_v = f"[{idx_map['media'][i]}:v]"
            out_v = f"[v{i}]"
            d = get_duration(p)
            filt = f"scale={VIDEO_W}:{VIDEO_H}"
            if i == 0 and cut_media2 and d >= 9:
                start = (d - 9) / 2
                filt += (f",trim=start={start}:end={start+9},"
                         "setpts=PTS-STARTPTS,setpts=PTS/(9/5)")
            elif i == 1 and d > 31.9:  # ⭐ THAY ĐỔI: 32 -> 31.9 để video ngắn hơn
                speed = d / 31.9  # ⭐ THAY ĐỔI: chia cho 31.9 thay vì 32
                filt += f",setpts=PTS/{speed:.6f}"
            fc.append(f"{in_v}{filt}{out_v}")
            vlabels.append(out_v)

        n = len(vlabels)
        fc.append(f"{''.join(vlabels)}concat=n={n}:v=1:a=0[vbody]")
        last = "[vbody]"

        if sub_text:
            final_fontsize = subtitle_fontsize
            max_text_width = VIDEO_W - (2 * subtitle_margin)
            
            system_font = get_system_font()
            try:
                if system_font:
                    font = ImageFont.truetype(system_font, size=final_fontsize)
                else:
                    font = ImageFont.load_default()

                while final_fontsize > subtitle_min_fontsize:
                    try:
                        if system_font:
                            font = ImageFont.truetype(system_font, size=final_fontsize)
                        text_width = font.getlength(sub_text) if hasattr(font, 'getlength') else font.getsize(sub_text)[0]
                        if text_width <= max_text_width:
                            break
                    except:
                        break
                    final_fontsize -= 1
            except (IOError, OSError):
                final_fontsize = subtitle_fontsize
                try:
                    font = ImageFont.load_default()
                except:
                    pass

            txt = sub_text.replace("'", r"'").replace(":", r"\:").replace("%", r"\%")
            
            if subtitle_align == 'center':
                 x_expr = "(w-text_w)/2"
            elif subtitle_align == 'left':
                x_expr = str(subtitle_margin)
            else:
                x_expr = f"w-text_w-{subtitle_margin}"
            
            ffmpeg_font = get_ffmpeg_font_path()
            
            draw = (
                f"drawtext=fontfile='{ffmpeg_font}'"
                f":text='{txt}'"
                f":x={x_expr}:y={subtitle_y}"
                f":fontsize={final_fontsize}"
                f":fontcolor={subtitle_fontcolor}"
                f":borderw={subtitle_borderw}:bordercolor={subtitle_bordercolor}"
            )
            fc.append(f"{last}{draw}[vsub]")
            last = "[vsub]"

        if "logo" in idx_map:
            logo_idx = idx_map["logo"]
            logo_w = int(VIDEO_W * logo_scale_percent / 100)
            fc.append(f"[{logo_idx}:v]scale={logo_w}:-1[logo_s]")
            x = f"W-w-{logo_x}" if brand == "BlueStars" else str(logo_x)
            fc.append(f"{last}[logo_s]overlay={x}:{logo_y}[vlogo]")
            last = "[vlogo]"
        if "outtro" in idx_map:
            fc.append(f"[{idx_map['outtro']}:v]setpts=PTS-STARTPTS[outtro_norm]")
            fc.append(f"{last}[outtro_norm]concat=n=2:v=1:a=0[vfinal]")
            last = "[vfinal]"
        
        audio_labels = []
        if "audio2" in idx_map:
            fc.append(f"[{idx_map['audio2']}:a]volume={audio2_volume}[a2v]")
            audio_labels.append("[a2v]")
        if "audio1" in idx_map:
            fc.append(f"[{idx_map['audio1']}:a]volume={audio1_volume}[a1v]")
            audio_labels.append("[a1v]")
        if audio_labels:
            fc.append(f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=first[aout]")

        cmd = ["ffmpeg", "-y", "-hwaccel", "auto"] + inputs + [
            "-filter_complex", ";".join(fc), "-map", last
        ]
        if audio_labels:
            cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "197k", "-ar", "48000", "-ac", "2","-aac_coder", "twoloop","-profile:a", "aac_low"]

        cmd += [
            "-c:v", codecs,
            "-crf", "18",
            "-b:v", "5M",
            "-minrate", "4.5M", 
            "-maxrate", "12M",
            "-bufsize", "20M",
            "-r", "29.97",
            "-preset", "p5" if "nvenc" in codecs else "medium",
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709",
            "-color_primaries", "bt709", 
            "-color_trc", "bt709",
            "-color_range", "tv",
            "-movflags", "+faststart",
            "-shortest",
            out_path
        ]

        startupinfo = None
        if platform.system() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            startupinfo=startupinfo,
            encoding='utf-8',
            errors='replace'
        )
        
        # Clean up temp files
        for temp_audio in [audio2] if audio2 and audio2.endswith("_a2.wav") else []:
            try:
                os.remove(temp_audio)
            except Exception as e:
                print(f"⚠️ Không thể xoá file tạm {temp_audio}: {e}")
        
        return f"✅ [{asin}] {out_path}"
        
    except Exception as e:
        error_details = str(e)
        if isinstance(e, subprocess.CalledProcessError):
            error_details += f"\nFFMPEG STDERR:\n{e.stderr}"
        return f"❌ [{asin}] exception: {error_details}"

# ⭐ GIỮ NGUYÊN HÀM WRAPPER GỐC
def create_video_wrapper(params):
    """Wrapper function for multiprocessing"""
    return create_video(**params)

def main_web(
    excel_file="all.xlsx", output_root=".", logo_scale_percent: int = 15,
    logo_x: int = 50, logo_y: int = 50, brand: str = "BlueStars",
    bluestars_outtro_path: str = None, codecs: str = "libx264", cut_media2: bool = True,
    audio1_volume: float = 0.1, audio2_volume: float = 1.0, subtitle_align: str = "center",
    subtitle_y: int = 100, subtitle_fontsize: int = 85, subtitle_fontcolor: str = "#000000",
    subtitle_borderw: int = 2, subtitle_bordercolor: str = "#FFFFFF",
    subtitle_margin: int = 100,
    subtitle_min_fontsize: int = 30
):
    logs, rendered = [], []
    df = pd.read_excel(excel_file)

    if "ASIN" not in df.columns:
        logs.append("❌ Missing 'ASIN' column")
        return logs, rendered
    if "Final" not in df.columns:
        df["Final"] = ""

    media_cols = [c for c in df.columns if c.startswith("Media") and c != "Media1"]

    # ⭐ GIỮ NGUYÊN MULTIPROCESSING GỐC
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        for idx, row in df.iterrows():
            asin = str(row["ASIN"]).strip()
            media = [row[c] for c in media_cols if pd.notna(row.get(c))]
            
            params = {
                "asin": asin, "media_paths": media,
                "audio1": str(row.get("Audio1", "")) or None,
                "audio2": str(row.get("Audio2", "")) or None,
                "logo_path": str(row.get("Media1", "")) or None,
                "asin_folder": output_root, "logo_scale_percent": logo_scale_percent,
                "logo_x": logo_x, "logo_y": logo_y, "brand": brand,
                "bluestars_outtro_path": bluestars_outtro_path, "codecs": codecs,
                "cut_media2": cut_media2, "audio1_volume": audio1_volume,
                "audio2_volume": audio2_volume, "sub_text": str(row.get("Subtitle", "")) or None,
                "subtitle_align": subtitle_align, "subtitle_y": subtitle_y,
                "subtitle_fontsize": subtitle_fontsize, "subtitle_fontcolor": subtitle_fontcolor,
                "subtitle_borderw": subtitle_borderw, "subtitle_bordercolor": subtitle_bordercolor,
                "subtitle_margin": subtitle_margin,
                "subtitle_min_fontsize": subtitle_min_fontsize,
            }
            
            try:
                result = executor.submit(create_video_wrapper, params).result()
                logs.append(result)
                
                # Check if successful and add to rendered paths
                if result.startswith("✅") and "] " in result:
                    try:
                        path = result.split("] ")[1].strip()
                        if os.path.exists(path):
                            rendered.append(path)
                            df.loc[idx, "Final"] = path
                    except:
                        pass
            except Exception as e:
                logs.append(f"❌ [{asin}] exception: {str(e)}")

    df.to_excel(excel_file, index=False)
    return logs, rendered

if __name__ == '__main__':
    multiprocessing.freeze_support()