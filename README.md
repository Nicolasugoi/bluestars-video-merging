# 🎬 BlueStars Video Tool

> **Công cụ tự động tạo video marketing sản phẩm từ ASIN Amazon**

Ứng dụng Streamlit đa nền tảng giúp tạo video quảng cáo sản phẩm một cách tự động từ danh sách ASIN Amazon, bao gồm crawl thông tin, tạo script, voice-over, và render video hoàn chỉnh.

## 🚀 **Cách chạy ứng dụng (QUAN TRỌNG!)**

### **🪟 Windows**
**Bước 1: Cài đặt lần đầu** 
👆 **Chạy file:** `requirements.bat` với quyền Administrator

**Bước 2: Chạy ứng dụng**
👆 **Bấm đúp vào file:** `run.bat` 

### **🍎 macOS / 🐧 Linux**
**Bước 1: Cài đặt lần đầu**
```bash
chmod +x install.sh
./install.sh
```

**Bước 2: Cấp quyền chạy ứng dụng lần đầu**
```bash
chmod +x run.command
```
**Bước 3: Chạy ứng dụng
👆 **Bấm đúp vào file:** `run.command` 

### **Bước 3: Sử dụng**
- Trình duyệt sẽ tự động mở tại: `http://localhost:8501`
- Nếu không tự mở, nhập link trên vào trình duyệt
---

## ✨ Tính năng chính

### 📊 **Quản lý dữ liệu**
- Import danh sách ASIN từ Excel
- Tự động crawl thông tin sản phẩm từ Amazon
- Tính toán thời lượng video tự động
- Quản lý media files (hình ảnh, video, audio)

### 🤖 **AI-Powered Content Generation**
- **Gemini AI Integration**: Tạo script và subtitle thông minh
- **Google Cloud TTS**: Chuyển đổi text thành voice chất lượng cao
- **Prompt Engineering**: Tạo prompts tối ưu cho từng sản phẩm

### 🎥 **Video Production**
- **MoviePy Engine**: Render video chất lượng cao với cross-platform font support
- **Custom Branding**: Logo, intro/outro tùy chỉnh
- **Flexible Layout**: Điều chỉnh subtitle, logo positioning
- **Batch Processing**: Xử lý hàng loạt video

### 🚀 **Workflow Automation**
- **Pipeline Presets**: Các quy trình được cài đặt sẵn
- **Step-by-step Execution**: Chạy từng bước hoặc tự động
- **Progress Tracking**: Theo dõi tiến trình real-time
- **Error Handling**: Xử lý lỗi thông minh và retry

## 🛠️ Yêu cầu hệ thống

### **🪟 Windows**
- Windows 10/11 
- Python 3.8+ 
- 4GB RAM (8GB khuyến nghị)
- 2GB dung lượng trống

### **🍎 macOS**
- macOS 10.14+ (Mojave)
- Python 3.8+
- Homebrew (để cài FFmpeg)
- 4GB RAM (8GB khuyến nghị)

### **🐧 Linux**
- Ubuntu 18.04+ / Debian 10+ / CentOS 8+
- Python 3.8+
- FFmpeg support
- 4GB RAM (8GB khuyến nghị)

## 🎯 Hướng dẫn sử dụng nhanh

### **🎮 Sử dụng Presets (Khuyến nghị)**

Sau khi ứng dụng mở, cuộn xuống **"🚀 9. Run Complete Pipeline"**:

1. **📊 Chuẩn bị data**: Crawl info + tính duration
2. **🎵 Sub + Voice**: Tạo subtitle + voice-over  
3. **🎬 Render**: Render video cuối cùng
4. **🚀 Full**: Chạy toàn bộ pipeline

### **⚙️ Cấu hình cơ bản**

#### **Bước 1: Upload files**
```
1. Upload file Excel chứa danh sách ASIN
2. Chọn thư mục input chứa ASIN folders
3. Upload logo (PNG/JPG)
4. Upload intro/outro videos (MP4) nếu có
```

#### **Bước 2: API Settings**
```
1. Nhập Gemini API Key (để tạo script)
2. Upload Google Cloud TTS credentials (để tạo voice)
3. Chọn output folder cho video
```

#### **Bước 3: Chạy Pipeline**
```
1. Chọn một preset phù hợp
2. Bấm "🏃‍♂️ Chạy các bước đã chọn"
3. Theo dõi progress trong Activity Logs
```

## 📊 Chuẩn bị dữ liệu

### **Excel File Format**
```csv
ASIN
B08XXXXXXXXX
B09XXXXXXXXX  
B10XXXXXXXXX
```


## 🎨 Tùy chỉnh Video

### **Brand Themes**
- **Canamax**: Theme xanh lá, layout professional
- **BlueStars**: Theme cam, layout dynamic

### **Video Settings**
- **Độ phân giải**: 1080x1920 (9:16 - TikTok/Instagram format)
- **Vị trí logo**: Tùy chỉnh X/Y coordinates
- **Subtitle styling**: Font tự động theo hệ điều hành
- **Audio mixing**: Cân bằng âm lượng background/voice

### **Cross-Platform Font Support**
- **Windows**: Arial Bold, Calibri Bold
- **macOS**: Arial, Helvetica
- **Linux**: DejaVu Sans Bold, Liberation Sans Bold

## 🔧 Xử lý sự cố

### **❌ Lỗi thường gặp**

**Windows: "FFmpeg not found"**
```
→ Chạy lại install.bat với quyền Administrator
→ Hoặc cài thủ công: choco install ffmpeg-full
```

**macOS: "FFmpeg not found"**
```
→ Cài Homebrew: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
→ Chạy: brew install ffmpeg
```

**Linux: "FFmpeg not found"**
```
→ Ubuntu/Debian: sudo apt install ffmpeg
→ CentOS/RHEL: sudo yum install ffmpeg
→ Arch: sudo pacman -S ffmpeg
```

**"Streamlit command not found"**
```
→ Chạy: python3 -m pip install streamlit (macOS/Linux)
→ Chạy: python -m pip install streamlit (Windows)
→ Hoặc sử dụng: python3 -m streamlit run webapp.py
```

**"API Key Invalid"**
```
→ Kiểm tra Gemini API key trong settings
→ Verify Google Cloud TTS credentials file
```

**"Font not found" (chỉ xảy ra trên Linux cũ)**
```
→ Cài font: sudo apt install fonts-dejavu fonts-liberation
→ Hoặc: sudo yum install dejavu-sans-fonts liberation-fonts
```

### **🚀 Tối ưu hiệu suất**
- Sử dụng SSD cho temp files
- 8GB+ RAM cho batch processing  
- Đóng browser tabs không cần thiết
- Cleanup temp files định kỳ

## 🌐 Kiểm tra tương thích

### **Platform Compatibility Matrix**

| Feature | Windows | macOS | Linux | Notes |
|---------|---------|-------|-------|-------|
| **Video Rendering** | ✅ | ✅ | ✅ | FFmpeg required |
| **Font Rendering** | ✅ | ✅ | ✅ | Auto font detection |
| **Web Scraping** | ✅ | ✅ | ✅ | Edge/Chrome required |
| **Audio Processing** | ✅ | ✅ | ✅ | Cross-platform |
| **File Paths** | ✅ | ✅ | ✅ | Pathlib used |
| **Installation** | Auto | Auto | Auto | Package managers |

## 📞 Hỗ trợ

**🆘 Nếu gặp vấn đề:**
1. Kiểm tra Activity Logs trong ứng dụng
2. Chạy lại installation script phù hợp với OS
3. Restart máy tính và thử lại
4. Kiểm tra font system fonts có tồn tại
5. Liên hệ support team

**📧 Liên hệ:** nguyen.ducviet.766@gmail.com

---

<div align="center">

## **🎯 TÓM TẮT NHANH**

### **🪟 WINDOWS:** Bấm đúp `install.bat` → `run.bat` ⚙️
### **🍎 macOS:** `./install.sh` → `./run.sh` 🚀  
### **🐧 LINUX:** `./install.sh` → `./run.sh` 🐧
### **🌐 MANUAL:** `pip install -r requirements.txt` → `streamlit run webapp.py` 🎮

**🌟 Cross-Platform Support - Chạy được trên Windows, macOS và Linux**

**🌟 Được phát triển bởi BlueStars Team**

</div>
