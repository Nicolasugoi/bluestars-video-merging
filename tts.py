import os
import time
import shutil
import pandas as pd
from pathlib import Path
from queue import Queue
import concurrent.futures
import traceback
import soundfile as sf
from google.cloud import texttospeech
from google.api_core.exceptions import ResourceExhausted

def get_audio_duration_sf(audio_path):
    """Get audio duration using soundfile."""
    try:
        # Convert to string and check if file exists
        audio_path = str(audio_path)
        if not os.path.exists(audio_path):
            return 0
            
        with sf.SoundFile(audio_path) as f:
            return f.frames / f.samplerate
    except Exception:
        return 0

def tts_synthesize(client, text, file_path, log_queue, max_retry=3):
    """Synthesize speech to file_path, retry on 429 up to max_retry."""
    text = str(text).strip()
    if not text or text.lower() in ['nan', 'none', '']:
        log_queue.put(f"⚠️ Empty text, skipping voice generation for {os.path.basename(file_path)}.")
        return False, "Skipped: Empty text"

    # Ensure file_path is string
    file_path = str(file_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp-HD-D"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.05
    )

    for attempt in range(1, max_retry+1):
        try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            with open(file_path, "wb") as out_f:
                out_f.write(response.audio_content)
            log_queue.put(f"✅ [TTS] Saved: {file_path}")
            return True, str(file_path)

        except ResourceExhausted as e:
            if attempt < max_retry:
                wait = 2 ** attempt
                log_queue.put(f"⚠️ [TTS] Quota exhausted, retry {attempt}/{max_retry} in {wait}s")
                time.sleep(wait)
                continue
            else:
                log_queue.put(f"❌ [TTS] Quota exhausted after {max_retry} tries: {e}")
                return False, f"Quota exhausted"

        except Exception as e:
            log_queue.put(f"❌ [TTS] Error: {e}")
            return False, str(e)

    return False, "Unknown TTS error"

def main_web(excel_path="all.xlsx", tts_cred_filename=None, audio2_folder="./voice", retry_mode=False):
    log = []
    
    # Setup credentials
    if tts_cred_filename and os.path.exists(tts_cred_filename):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(tts_cred_filename)
    else:
        log.append("⚠️ Missing TTS credentials file.")
        return log

    # Create audio2_folder if it doesn't exist
    if not os.path.exists(audio2_folder):
        os.makedirs(audio2_folder)
        log.append(f"📁 Created voice folder: {audio2_folder}")

    # Initialize client
    try:
        client = texttospeech.TextToSpeechClient()
    except Exception as e:
        log.append(f"❌ Failed to init TTS client: {e}")
        return log

    # Read Excel with proper data type handling
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        log.append(f"❌ Cannot read Excel '{excel_path}': {e}")
        return log

    # Ensure columns exist with proper data types
    required_columns = {
        "ASIN": str,
        "Script": str, 
        "Duration": float,
        "Audio2": str,
        "VoiceDurationCheck": str
    }
    
    for col, dtype in required_columns.items():
        if col not in df.columns:
            if dtype == str:
                df[col] = ""
            elif dtype == float:
                df[col] = 0.0
            else:
                df[col] = ""
    
    # Ensure proper data types to avoid FutureWarning
    df["Duration"] = pd.to_numeric(df["Duration"], errors='coerce').fillna(0.0)
    df["Script"] = df["Script"].astype(str).replace('nan', '')
    df["Audio2"] = df["Audio2"].astype(str).replace('nan', '')
    df["VoiceDurationCheck"] = df["VoiceDurationCheck"].astype(str).replace('nan', '')

    # Prepare output folder - use the custom audio2_folder instead of hardcoded path
    audio2_folder_path = Path(audio2_folder)
    audio2_folder_path.mkdir(exist_ok=True, parents=True)
    log.append(f"ℹ️ Voice files → folder: {audio2_folder_path}")

    # Build tasks
    tasks = []
    for idx, row in df.iterrows():
        asin = str(row["ASIN"]).strip()
        script = str(row["Script"]).strip()
        vdur = float(row.get("Duration", 0))
        status = str(row.get("VoiceDurationCheck", "")).strip().lower()

        # Skip if no valid ASIN
        if not asin or asin.lower() in ['nan', 'none', '']:
            log.append(f"⏩ [Row {idx}] Skip, no valid ASIN.")
            continue

        if retry_mode:
            if script and script != "nan" and status != "ok":
                out_fp = audio2_folder_path / f"{asin}_voice.mp3"
                tasks.append((idx, asin, script, vdur, str(out_fp)))
            else:
                if not script or script == "nan":
                    df.at[idx, "VoiceDurationCheck"] = "Skipped: No Script"
                    log.append(f"⏩ [ASIN {asin}] Skip, no script.")
                else:
                    log.append(f"⏭️ [ASIN {asin}] Already OK, skipping.")
        else:
            if script and script != "nan":
                out_fp = audio2_folder_path / f"{asin}_voice.mp3"
                tasks.append((idx, asin, script, vdur, str(out_fp)))
            else:
                df.at[idx, "VoiceDurationCheck"] = "Skipped: No Script"
                log.append(f"⏩ [ASIN {asin}] Skip, no script.")

    if not tasks:
        log.append("❗ No TTS tasks.")
        df.to_excel(excel_path, index=False)
        log.append("✅ Excel updated.")
        return log

    # Use fewer threads to avoid quota issues
    n_threads = min(4, len(tasks))
    log.append(f"🚀 Synthesizing {len(tasks)} voices with {n_threads} threads.")

    q = Queue()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
        future_to_task = {
            ex.submit(tts_synthesize, client, script, fp, q): (idx, asin, vdur, fp)
            for idx, asin, script, vdur, fp in tasks
        }
        
        for fut in concurrent.futures.as_completed(future_to_task):
            idx, asin, vdur, fp = future_to_task[fut]
            try:
                success, res = fut.result()
                
                if success:
                    # Ensure proper string assignment to avoid dtype warnings
                    df.at[idx, "Audio2"] = str(res)
                    
                    aud_dur = get_audio_duration_sf(res)
                    log.append(f"[ASIN {asin}] Voice {aud_dur:.2f}s vs Video {vdur:.2f}s")
                    
                    if vdur > 0 and aud_dur > vdur * 1.15:
                        df.at[idx, "VoiceDurationCheck"] = "Failed: too long"
                        log.append(f"⚠️ [ASIN {asin}] Voice >115% video.")
                    else:
                        df.at[idx, "VoiceDurationCheck"] = "OK"
                        log.append(f"✅ [ASIN {asin}] Voice duration OK.")
                else:
                    df.at[idx, "VoiceDurationCheck"] = f"Failed: {res}"
                    log.append(f"❌ [ASIN {asin}] TTS failed: {res}")
            except Exception as e:
                log.append(f"❌ [ASIN {asin}] Unexpected error: {e}")
                df.at[idx, "VoiceDurationCheck"] = f"Failed: {str(e)}"

    # Collect internal logs
    while not q.empty():
        log.append(q.get())

    # Save back with proper data types
    try:
        df.to_excel(excel_path, index=False)
        log.append(f"✅ Excel '{excel_path}' updated with VoiceDurationCheck.")
    except Exception as e:
        log.append(f"⚠️ Error saving Excel: {e}")

    return log