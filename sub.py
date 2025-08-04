import pandas as pd
import google.generativeai as genai
import traceback

def fmt_duration(seconds: float) -> str:
    """
    Convert a float number of seconds into SRT time format: HH:MM:SS,mmm
    """
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def write_srt(sub_text: str, srt_path: str, duration: float) -> None:
    """
    Write a single-cue SRT file covering the full duration of the video.
    Ensures each line is sanitized and that a blank line follows the cue.
    """
    # Normalize line endings and split into lines
    lines = sub_text.replace('\r', '').split('\n')
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write("1\n")
        f.write(f"00:00:00,000 --> {fmt_duration(duration)}\n")
        for line in lines:
            f.write(line + "\n")
        f.write("\n")  # final blank line required by SRT parsers


def main_web(api_key: str, excel_file: str = "all.xlsx") -> list[str]:
    """
    Read product titles from an Excel file, generate clean subtitles via Gemini,
    write them back to the same Excel file, and return a list of log messages.
    """
    log: list[str] = []

    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
    except Exception as e:
        log.append(f"❌ Lỗi cấu hình Gemini: {e}")
        return log

    # Read Excel
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        log.append(f"❌ Lỗi đọc Excel '{excel_file}': {e}")
        return log

    # Validate column
    if "ProductTitle" not in df.columns:
        log.append("❌ Cột 'ProductTitle' không tồn tại.")
        return log

    # Prepare Subtitle column
    df["Subtitle"] = ""

    # Generate subtitles row by row
    for idx, row in df.iterrows():
        title = str(row.get("ProductTitle", "") or "").strip()
        if not title:
            log.append(f"⏩ [row {idx+2}] Bỏ qua: không có ProductTitle")
            continue

        prompt = (
            "help me extract the name of this product, eliminate any redundant information\n"
            "No need to add your comment, such as 'here's the subtitle...' or 'the true name is...'\n"
            "structure includes: product number + product name\n"
            "for example, with the title "
            "'WP3406107 3406107 Dryer Door Switch - Compatible with Whirlpool Maytag Kenmore Dryers "
            "- Replaces 3406109 3405100 3405101 3406100 3406101 AED4475TQ1 MEDC400VW0', "
            "the output should be '3406107 Dryer Door Switch'\n\n"
            f"This is the full product title: {title}"
        )

        try:
            resp = model.generate_content(prompt)
            sub = resp.candidates[0].content.parts[0].text.strip()
            log.append(f"✅ [row {idx+2}] Subtitle: {sub}")
        except Exception as e:
            tb = traceback.format_exc()
            sub = title  # fallback to raw title
            log.append(f"⚠️ [row {idx+2}] Gemini lỗi, fallback to raw title: {e}")
            log.append(tb)

        df.at[idx, "Subtitle"] = sub

    # Write back to Excel
    try:
        df.to_excel(excel_file, index=False)
        log.append("✅ Subtitles saved back to Excel.")
    except Exception as e:
        log.append(f"⚠️ Lỗi lưu Excel: {e}")

    return log
