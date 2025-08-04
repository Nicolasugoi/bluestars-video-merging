# 🚀 Quick Start Guide - BlueStars Video Tool

> **Hướng dẫn cài đặt và chạy nhanh trong 5 phút**

## 📋 **Yêu cầu trước khi bắt đầu**

### **💻 Hệ điều hành hỗ trợ:**
- ✅ Windows 10/11
- ✅ macOS 10.14+ (Mojave hoặc mới hơn)
- ✅ Linux (Ubuntu 18.04+, Debian 10+, CentOS 8+)

### **🔧 Phần mềm cần thiết:**
- **Python 3.8+** (QUAN TRỌNG!)
- **4GB RAM** (8GB khuyến nghị)
- **2GB dung lượng trống**
- **Kết nối Internet** (để cài đặt packages)

---

## 🎯 **CÁCH CÀI ĐẶT & CHẠY**

### **🪟 CHO WINDOWS**

#### **Bước 1: Kiểm tra Python**
```cmd
python --version
```
*(Nếu báo lỗi, tải Python từ: https://python.org)*

#### **Bước 2: Cài đặt tự động**
1. **Bấm chuột phải** vào `install.bat`
2. **Chọn "Run as Administrator"**
3. **Đợi cài đặt hoàn tất** (5-10 phút)

#### **Bước 3: Chạy ứng dụng**
1. **Bấm đúp** vào `run.bat`
2. **Đợi 30 giây** để Streamlit khởi động
3. **Trình duyệt tự động mở** tại `http://localhost:8501`

---

### **🍎 CHO macOS**

#### **Bước 1: Cài đặt Homebrew (nếu chưa có)**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### **Bước 2: Kiểm tra Python**
```bash
python3 --version
```
*(Nếu chưa có: `brew install python3`)*

#### **Bước 3: Cài đặt tự động**
```bash
chmod +x install.sh
./install.sh
```

#### **Bước 4: Chạy ứng dụng**
```bash
chmod +x run.sh
./run.sh
```

---

### **🐧 CHO LINUX**

#### **Bước 1: Cập nhật hệ thống**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

#### **Bước 2: Cài đặt tự động**
```bash
chmod +x install.sh
./install.sh
```

#### **Bước 3: Chạy ứng dụng**
```bash
chmod +x run.sh
./run.sh
```

---

## 🔧 **XỬ LÝ LỖI THƯỜNG GẶP**

### **❌ "Python not found"**
**Windows:**
- Tải Python từ: https://python.org
- ✅ **QUAN TRỌNG:** Tick "Add Python to PATH"

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt install python3 python3-pip  # Ubuntu/Debian
sudo yum install python3 python3-pip  # CentOS
```

### **❌ "FFmpeg not found"**
**Windows:**
- Script tự động cài FFmpeg qua Chocolatey
- Nếu fail: Tải từ https://ffmpeg.org

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS
```

### **❌ "Permission denied"**
**Windows:**
- Chạy `install.bat` **với quyền Administrator**

**macOS/Linux:**
```bash
chmod +x install.sh run.sh
sudo ./install.sh  # Nếu cần
```

### **❌ "Streamlit command not found"**
```bash
# Thử chạy manual
pip install streamlit
streamlit run webapp.py
```

---

## 🎮 **HƯỚNG DẪN SỬ DỤNG NHANH**

### **Bước 1: Mở ứng dụng**
- Trình duyệt mở tại: `http://localhost:8501`
- Nếu không tự mở, copy link trên vào trình duyệt

### **Bước 2: Cài đặt cơ bản**
1. **Nhập Gemini API Key** ở đầu trang
2. **Upload Excel file** chứa danh sách ASIN
3. **Chọn thư mục input** chứa ASIN folders
4. **Upload logo** (PNG/JPG)

### **Bước 3: Chạy quy trình**
1. Cuộn xuống **"🚀 9. Run Complete Pipeline"**
2. Chọn preset: **"Full"** để chạy toàn bộ
3. Bấm **"🏃‍♂️ Chạy các bước đã chọn"**
4. Theo dõi tiến trình trong **Activity Logs**

### **Bước 4: Lấy kết quả**
- Video hoàn thành sẽ ở thư mục **output**
- Xem preview ngay trong ứng dụng

---

## 📁 **CHUẨN BỊ DỮ LIỆU**

### **File Excel format:**
```csv
ASIN
B08XXXXXXXXX
B09XXXXXXXXX
B10XXXXXXXXX
```

### **Cấu trúc thư mục:**
```
input/
├── B08XXXXXXXXX/
│   ├── Media1.jpg     # Hình sản phẩm (bắt buộc)
│   ├── Media2.mp4     # Video demo (optional)
│   └── Audio1.mp3     # Nhạc nền (optional)
└── B09XXXXXXXXX/
    ├── Media1.png
    ├── Media2.mp4
    └── Audio1.wav
```

---

## 🆘 **HỖ TRỢ NHANH**

### **🔍 Kiểm tra log lỗi:**
- Xem **Activity Logs** trong ứng dụng
- Tìm dòng có icon ❌

### **🔄 Reset khi gặp lỗi:**
1. Đóng trình duyệt
2. Tắt terminal/command prompt
3. Chạy lại `run.bat` hoặc `./run.sh`

### **📞 Liên hệ hỗ trợ:**
- **Email:** support@bluestars.com
- **Telegram:** @bluestars_support

---

## ⚡ **TÓM TẮT LỆNH NHANH**

### **Windows:**
```cmd
# Cài đặt (Run as Administrator)
install.bat

# Chạy
run.bat
```

### **macOS/Linux:**
```bash
# Cài đặt
chmod +x install.sh && ./install.sh

# Chạy
chmod +x run.sh && ./run.sh
```

### **Manual (tất cả OS):**
```bash
pip install -r requirements.txt
streamlit run webapp.py
```

---

<div align="center">

## **🎯 BẮT ĐẦU NGAY**

### **1️⃣ DOWNLOAD → 2️⃣ INSTALL → 3️⃣ RUN → 4️⃣ ENJOY! 🎉**

**💡 Mẹo:** Chuẩn bị sẵn Gemini API Key và ASIN data trước khi chạy

**🌟 Thời gian setup: ~10 phút | Thời gian render 1 video: ~2 phút**

</div>
