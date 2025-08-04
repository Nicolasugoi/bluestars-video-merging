import os
import subprocess
import sys
from pathlib import Path

def check_ffmpeg_path():
    """Kiểm tra và sửa lỗi PATH cho FFmpeg"""
    print("FFmpeg PATH Diagnosis")
    print("=" * 40)
    
    # 1. Kiểm tra PATH environment variable
    path_env = os.environ.get('PATH', '')
    print("Current PATH directories:")
    for i, path_dir in enumerate(path_env.split(os.pathsep), 1):
        print(f"  {i}. {path_dir}")
    
    print("\n" + "=" * 40)
    
    # 2. Thử tìm FFmpeg trong PATH
    print("Checking FFmpeg in PATH...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ FFmpeg found in PATH!")
            print(f"First line: {result.stdout.split(chr(10))[0]}")
        else:
            print("✗ FFmpeg command failed")
    except FileNotFoundError:
        print("✗ FFmpeg not found in PATH")
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg command timed out")
    except Exception as e:
        print(f"✗ Error running FFmpeg: {e}")
    
    # 3. Tìm FFmpeg trong các vị trí phổ biến
    print("\nSearching for FFmpeg in common locations...")
    common_locations = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Users\{}\AppData\Local\ffmpeg\bin\ffmpeg.exe".format(os.getenv('USERNAME', '')),
        r".\ffmpeg.exe",
        r".\bin\ffmpeg.exe"
    ]
    
    found_paths = []
    for location in common_locations:
        if os.path.exists(location):
            found_paths.append(location)
            print(f"✓ Found: {location}")
    
    if not found_paths:
        print("✗ No FFmpeg found in common locations")
        
        # Tìm kiếm trên toàn hệ thống (có thể chậm)
        print("\nSearching system-wide (this may take a while)...")
        try:
            result = subprocess.run(['where', 'ffmpeg'], 
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                paths = result.stdout.strip().split('\n')
                for path in paths:
                    if path.strip():
                        found_paths.append(path.strip())
                        print(f"✓ Found: {path.strip()}")
        except:
            pass
    
    # 4. Đề xuất giải pháp
    print("\n" + "=" * 40)
    print("SOLUTIONS:")
    
    if found_paths:
        print(f"1. Use full path to FFmpeg:")
        for path in found_paths:
            print(f"   {path}")
        
        print(f"\n2. Add FFmpeg directory to PATH:")
        unique_dirs = set()
        for path in found_paths:
            ffmpeg_dir = str(Path(path).parent)
            unique_dirs.add(ffmpeg_dir)
        
        for ffmpeg_dir in unique_dirs:
            print(f"   Add this to PATH: {ffmpeg_dir}")
    else:
        print("1. Download FFmpeg from: https://ffmpeg.org/download.html")
        print("2. Extract to C:\\ffmpeg")
        print("3. Add C:\\ffmpeg\\bin to PATH")
        print("4. Restart your IDE/terminal")
    
    print("\n3. Restart your Python environment after adding to PATH")
    print("4. Try running this script again")
    
    return found_paths

def detect_gpu_codecs_with_path(ffmpeg_path=None, debug=False):
    """Phiên bản cải tiến với custom FFmpeg path"""
    potential_codecs = ['libx264']
    hardware_codecs = [
        'h264_nvenc', 'hevc_nvenc', 'av1_nvenc',
        'h264_qsv', 'hevc_qsv', 'av1_qsv',
        'h264_amf', 'hevc_amf', 'av1_amf',
        'h264_mf', 'hevc_mf',
        'h264_vaapi', 'hevc_vaapi', 'av1_vaapi',
    ]
    
    # Xác định command để chạy
    if ffmpeg_path:
        ffmpeg_cmd = ffmpeg_path
    else:
        ffmpeg_cmd = 'ffmpeg'
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        if debug:
            print(f"Using FFmpeg command: {ffmpeg_cmd}")
        
        # Kiểm tra hardware accelerators
        if debug:
            print("Checking hardware accelerators...")
            try:
                hwaccel_result = subprocess.run([ffmpeg_cmd, '-hide_banner', '-hwaccels'], 
                                              capture_output=True, text=True, check=True, startupinfo=startupinfo)
                print("Available hardware accelerators:")
                print(hwaccel_result.stdout)
            except Exception as e:
                print(f"Error checking hwaccels: {e}")
        
        # Kiểm tra encoders
        result = subprocess.run([ffmpeg_cmd, '-hide_banner', '-encoders'], 
                               capture_output=True, text=True, check=True, startupinfo=startupinfo)
        output = result.stdout.lower()
        
        if debug:
            print("\nChecking for hardware encoders:")
            print("=" * 50)
        
        found_codecs = []
        for codec in hardware_codecs:
            if codec.lower() in output:
                if codec not in potential_codecs:
                    potential_codecs.append(codec)
                    found_codecs.append(codec)
                if debug:
                    print(f"✓ Found: {codec}")
            elif debug:
                print(f"✗ Not found: {codec}")
        
        if debug:
            print(f"\nTotal hardware codecs found: {len(found_codecs)}")
            if found_codecs:
                print(f"Hardware codecs: {', '.join(found_codecs)}")
            else:
                print("No hardware codecs detected!")
                print("\nWith RTX 3070 Ti, you should have NVENC support!")
                print("This might be an FFmpeg build issue.")
        
    except subprocess.CalledProcessError as e:
        if debug:
            print(f"FFmpeg command failed: {e}")
            print(f"Return code: {e.returncode}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
    except FileNotFoundError:
        if debug:
            print(f"FFmpeg not found: {ffmpeg_cmd}")
    except Exception as e:
        if debug:
            print(f"Unexpected error: {e}")
    
    return potential_codecs

if __name__ == "__main__":
    # Kiểm tra PATH
    found_paths = check_ffmpeg_path()
    
    # Nếu tìm thấy FFmpeg, thử detect codecs
    if found_paths:
        print("\n" + "=" * 50)
        print("Testing codec detection with found FFmpeg...")
        
        for ffmpeg_path in found_paths:
            print(f"\nTesting with: {ffmpeg_path}")
            print("-" * 30)
            codecs = detect_gpu_codecs_with_path(ffmpeg_path, debug=True)
            print(f"Result: {codecs}")
            
            # Nếu tìm thấy hardware codecs thì dừng
            if len(codecs) > 1:
                break
    else:
        print("\nNo FFmpeg found. Please install FFmpeg first.")