import pandas as pd
import google.generativeai as genai
import re, os
import concurrent.futures
import time
import traceback
from queue import Queue
from google.generativeai import types as genai_types

def count_words(text):
    """Count English words in text."""
    return len(re.findall(r"\w+", str(text)))

def generate_script_with_retry(model, prompt, word_count, max_retry=10, tol=0.2):
    """Generate script with retries. Designed to be run in a separate thread."""
    local_log = []
    best_script = ""
    best_wc = 0
    best_diff = float("inf")

    generation_config = genai_types.GenerationConfig(temperature=0.0, top_p=1)
    if not prompt:
        local_log.append("⚠️ Missing Prompt – skipping script generation.")
        return "Skipped: No Prompt", 0, 0, False, local_log

    local_log.append(f"Starting (target {word_count} words)...")

    for attempt in range(1, max_retry+1):
        try:
            if attempt > 1:
                time.sleep(1)

            resp = model.generate_content(contents=prompt, generation_config=generation_config)
            script = (
                resp.candidates[0].content.parts[0].text.strip()
                if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts
                else "No script generated."
            )
            if script == "No script generated.":
                local_log.append(f"  Attempt {attempt}/{max_retry}: API returned no script.")
                continue

        except Exception as e:
            script = f"Error: {e}"
            local_log.append(f"  Attempt {attempt}/{max_retry}: Gemini API error: {e}")
            continue

        wc = count_words(script)
        diff = abs(wc - word_count)
        allowed_min = int(word_count * (1 - tol))
        allowed_max = int(word_count * (1 + tol))

        local_log.append(f"  Attempt {attempt}/{max_retry}: Generated {wc} words.")

        if allowed_min <= wc <= allowed_max:
            local_log.append(f"  Meets word count requirement ({wc}).")
            return script, wc, attempt, True, local_log

        if diff < best_diff:
            best_diff = diff
            best_script = script
            best_wc = wc
            local_log.append(f"  Better script than previous ({wc} words, diff {best_diff}). Saving.")
    
    if best_script and best_wc < allowed_min:
        local_log.append(f"Script too short ({best_wc} words < {allowed_min}), adding closing.")
        best_script = best_script.rstrip() + "\nThank you for choosing us!"
        best_wc = count_words(best_script)
        local_log.append(f"➕Word count after addition: {best_wc}.")

    local_log.append(f"Failed to meet word count after {max_retry} attempts. Returning best script ({best_wc} words).")
    return best_script, best_wc, max_retry, False, local_log

def gen_script_gemini(google_api_key: str, excel_file_path: str = "all.xlsx", rewrite: bool = False) -> tuple[list[str], int,int]:
    """Generate scripts using Gemini AI with proper data type handling."""
    tol = 0.2
    log: list[str] = []
    good_script, bad_script = 0, 0

    try:
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
    except Exception as e:
        log.append(f"❌ Error configuring Gemini API or initializing model: {e}")
        return log

    try:
        df = pd.read_excel(excel_file_path)
    except FileNotFoundError:
        log.append(f"❌ Error: Excel file '{excel_file_path}' not found.")
        return log
    except Exception as e:
        log.append(f"❌ Error reading Excel file '{excel_file_path}': {e}")
        return log

    # Ensure necessary columns exist with proper data types
    if "ASIN" not in df.columns:
        log.append("❌ Excel file must have column: 'ASIN'.")
        return log
    if "Prompt" not in df.columns:
        log.append("⚠️ 'Prompt' column doesn't exist. Cannot generate scripts.")
        return log
    if "Duration" not in df.columns:
        log.append("⚠️ 'Duration' column doesn't exist. Cannot calculate word count.")
        df["Duration"] = 0.0
    
    # Initialize columns with proper data types
    if "Script" not in df.columns:
        df["Script"] = ""
    if "Check" not in df.columns:
        df["Check"] = ""
    if "WordsPerSecond" not in df.columns:
        df["WordsPerSecond"] = 155
    
    # Ensure proper data types to avoid FutureWarning
    df["Duration"] = pd.to_numeric(df["Duration"], errors='coerce').fillna(0.0)
    df["WordsPerSecond"] = pd.to_numeric(df["WordsPerSecond"], errors='coerce').fillna(155)
    df["Script"] = df["Script"].astype(str).replace('nan', '')
    df["Check"] = df["Check"].astype(str).replace('nan', '')
    df["Prompt"] = df["Prompt"].astype(str).replace('nan', '')

    # Prepare tasks for the thread pool
    tasks = []
    for idx, row in df.iterrows():
        asin = str(row["ASIN"]).strip()
        prompt = str(row.get("Prompt", "")).strip()
        duration = float(row.get("Duration", 0))
        wps = float(row.get("WordsPerSecond", 160))
        current_check = str(row.get("Check", "")).strip().lower()

        needs_generation = (
            prompt != "" and
            (
                pd.isna(row["Script"]) or 
                str(row["Script"]).strip() == "" or 
                str(row["Script"]).strip() == "nan" or
                current_check != 'ok'
            )
        )

        if needs_generation:
            word_count = round((duration) / 60 * wps)
            tasks.append({
                'idx': idx,
                'asin': asin,
                'prompt': prompt,
                'word_count': word_count,
                'model': model
            })
        elif not prompt:
            log.append(f"⏩ [ASIN {asin}] Skipping script generation: Empty prompt.")
            df.at[idx, "Check"] = "Skipped: No Prompt"
        else:
            log.append(f"⏭️ [ASIN {asin}] Skipping script generation: Script exists and Check is OK.")

    if not tasks:
        log.append("❗ No ASINs need script generation.")
        try:
            df.to_excel(excel_file_path, index=False)
            log.append("✅ Updated 'Check' column in Excel (no scripts generated).")
        except Exception as e:
            log.append(f"⚠️ Error saving Excel file: {e}")
        return log

    num_threads = min(50, max(5, (os.cpu_count() or 2) * 10))
    log.append(f"🚀 Start {len(tasks)} ASINs using ThreadPoolExecutor: {num_threads}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_task = {
            executor.submit(generate_script_with_retry,
                            task['model'],
                            task['prompt'],
                            task['word_count']): task
            for task in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            asin = task['asin']
            idx = task['idx']
            try:
                script, wc, attempts, ok, task_log = future.result()
                
                for m in task_log:
                    log.append(f"[ASIN {asin}] {m}")

                # Ensure proper string assignment
                df.at[idx, "Script"] = str(script)
                if ok:
                    check_note = f"✅ OK: {wc} words ({attempts} attempts)"
                    log.append(f"✅ [ASIN {asin}] Script OK ({wc} words, {attempts} attempts).")
                    good_script += 1
                else:
                    check_note = f"⚠️ Word count not met: {wc} words (required {task['word_count']} ±{tol*100:.0f}%), after {attempts} attempts"
                    log.append(f"⚠️ [ASIN {asin}] Script doesn't meet word count ({wc}/{task['word_count']}) after {attempts} attempts.")
                    bad_script += 1
                df.at[idx, "Check"] = str(check_note)

            except Exception as exc:
                log.append(f'❌ [ASIN {asin}] Error generating script: {exc}')
                df.at[idx, "Script"] = f"Error: {exc}"
                df.at[idx, "Check"] = f"Error: {exc}"

    # Save Excel with proper error handling
    try:
        df.to_excel(excel_file_path, index=False)
    except Exception as e:
        log.append(f"⚠️ Error saving Excel file: {e}")

    return log, good_script, bad_script

def main_web(google_api_key: str, excel_file_path: str = "all.xlsx"):
    return gen_script_gemini(google_api_key, excel_file_path)