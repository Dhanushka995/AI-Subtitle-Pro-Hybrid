import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import google.generativeai as genai
from openai import OpenAI
import threading
import time
import re
import os
import json

CONFIG_FILE = "hybrid_sub_pro_config_v18.json"

LANG_CODES = {
    "Sinhala": "සිංහල",
    "Tamil": "தமிழ்",
    "Hindi": "हिन्दी",
    "French": "français",
    "Spanish": "español",
}

class HybridSubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Subtitle Pro v2.0 (Direct AI Translate)")
        self.root.geometry("700x950")
        self.root.configure(bg="#1e272e")

        self.is_running = False
        self.provider_type = "Unknown"
        self.file_path = ""
        self.auto_filling = False
        self.total_tokens = 0

        # --- HEADER ---
        tk.Label(root, text="AI SUBTITLE TRANSLATOR PRO v2.0", bg="#1e272e", fg="#00d8d6", font=("Arial", 16, "bold")).pack(pady=10)

        # --- API KEY INPUT ---
        tk.Label(root, text="Paste API Key (Google, Groq, OpenRouter, HF, NVIDIA, etc.):", bg="#1e272e", fg="#d2dae2").pack(pady=(5, 0))
        self.api_var = tk.StringVar()
        self.api_var.trace_add("write", self.on_key_change)
        tk.Entry(root, textvariable=self.api_var, width=65, show="*", bg="#485460", fg="white", borderwidth=0, font=("Consolas", 10)).pack(pady=5, ipady=6)

        self.status_lbl = tk.Label(root, text="Waiting for API Key...", bg="#1e272e", fg="#808e9b", font=("Arial", 9, "bold"))
        self.status_lbl.pack(pady=2)

        # --- ADVANCED SETTINGS ---
        self.adv_frame = tk.Frame(root, bg="#2f3640", padx=10, pady=10)
        self.adv_frame.pack(pady=5, fill="x", padx=40)

        tk.Label(self.adv_frame, text="Base URL:", bg="#2f3640", fg="white").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        tk.Entry(self.adv_frame, textvariable=self.url_var, width=50, bg="#1e272e", fg="white").grid(row=0, column=1, padx=10, pady=2)

        tk.Label(self.adv_frame, text="Model Name:", bg="#2f3640", fg="white").grid(row=1, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_var.trace_add("write", self.on_model_manual_change)
        tk.Entry(self.adv_frame, textvariable=self.model_var, width=50, bg="#1e272e", fg="white").grid(row=1, column=1, padx=10, pady=2)

        # --- FILE SELECTION ---
        tk.Button(root, text="📂 Select English SRT File", command=self.open_file, bg="#0fb9b1", fg="white", font=("Arial", 10, "bold"), width=30).pack(pady=10)
        self.lbl_status_file = tk.Label(root, text="No file selected", bg="#1e272e", fg="#808e9b")
        self.lbl_status_file.pack()

        # --- SETTINGS ---
        settings_frame = tk.Frame(root, bg="#1e272e")
        settings_frame.pack(pady=5)

        tk.Label(settings_frame, text="Chunk Size:", bg="#1e272e", fg="white").grid(row=0, column=0, padx=5)
        self.chunk_var = tk.StringVar(value="20")
        ttk.Combobox(settings_frame, textvariable=self.chunk_var, values=["10", "15", "20", "30"], width=5).grid(row=0, column=1, padx=5)

        tk.Label(settings_frame, text="Language:", bg="#1e272e", fg="white").grid(row=0, column=2, padx=15)
        self.lang_var = tk.StringVar(value="Sinhala")
        ttk.Combobox(settings_frame, textvariable=self.lang_var, values=list(LANG_CODES.keys()), width=10).grid(row=0, column=3, padx=5)

        self.delay_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Enable 15s Delay (for free API limits)", variable=self.delay_enabled, bg="#1e272e", fg="#0be881", selectcolor="#1e272e").grid(row=1, column=0, columnspan=4, pady=5)

        self.resume_var = tk.StringVar(value="1")
        tk.Label(settings_frame, text="Start from Chunk:", bg="#1e272e", fg="#ff9f43").grid(row=2, column=0, columnspan=2, sticky="e")
        tk.Entry(settings_frame, textvariable=self.resume_var, width=6, bg="#ff9f43", font=("Arial", 10, "bold")).grid(row=2, column=2, sticky="w", padx=5)

        # --- LOG BOX ---
        self.log_box = tk.Text(root, height=20, width=80, bg="#000000", fg="#0be881", font=("Consolas", 9))
        self.log_box.pack(pady=5, padx=20)

        self.token_usage_lbl = tk.Label(root, text="Total AI Tokens Used: 0", bg="#1e272e", fg="#feca57", font=("Arial", 10, "bold"))
        self.token_usage_lbl.pack(pady=5)

        # --- BUTTONS ---
        btn_frame = tk.Frame(root, bg="#1e272e")
        btn_frame.pack(pady=10)
        self.btn_start = tk.Button(btn_frame, text="START", command=self.start_process, bg="#0984e3", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_start.grid(row=0, column=0, padx=10)
        self.btn_stop = tk.Button(btn_frame, text="STOP", command=self.stop_process, bg="#2d3436", fg="white", font=("Arial", 12, "bold"), width=15, height=2, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=10)
        self.btn_reset = tk.Button(btn_frame, text="Reset", command=self.reset_all, bg="#d63031", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_reset.grid(row=0, column=2, padx=10)

        self.load_settings()

    def on_model_manual_change(self, *args):
        if not self.auto_filling and self.model_var.get().strip():
            self.status_lbl.config(text=f"✅ Using Manual Model: {self.model_var.get()}", fg="#0be881")

    def on_key_change(self, *args):
        key = self.api_var.get().strip()
        if not key:
            self.status_lbl.config(text="Waiting for API Key... (type 'ollama' for local)", fg="#808e9b")
            return
        self.auto_filling = True

        key_lower = key.lower()

        # ── Google Gemini ──────────────────────────────────────────────
        if key.startswith("AIza"):
            self.status_lbl.config(text="✅ Google Gemini — gemini-1.5-flash (Best for Sinhala!)", fg="#0be881")
            self.url_var.set("N/A")
            self.model_var.set("gemini-1.5-flash")
            self.provider_type = "Gemini"

        # ── OpenRouter ─────────────────────────────────────────────────
        elif key.startswith("sk-or-"):
            self.status_lbl.config(text="✅ OpenRouter — gemini-2.0-flash-lite:free", fg="#0be881")
            self.url_var.set("https://openrouter.ai/api/v1")
            self.model_var.set("google/gemini-2.0-flash-lite:free")
            self.provider_type = "OpenAI_Compatible"

        # ── Groq ───────────────────────────────────────────────────────
        elif key.startswith("gsk_"):
            self.status_lbl.config(text="✅ Groq — llama-3.3-70b-versatile", fg="#0be881")
            self.url_var.set("https://api.groq.com/openai/v1")
            self.model_var.set("llama-3.3-70b-versatile")
            self.provider_type = "OpenAI_Compatible"

        # ── Hugging Face ───────────────────────────────────────────────
        elif key.startswith("hf_"):
            self.status_lbl.config(text="✅ Hugging Face — Qwen2.5-72B-Instruct", fg="#0be881")
            self.url_var.set("https://api-inference.huggingface.co/v1")
            self.model_var.set("Qwen/Qwen2.5-72B-Instruct")
            self.provider_type = "OpenAI_Compatible"

        # ── NVIDIA NIM ─────────────────────────────────────────────────
        elif key.startswith("nvapi-"):
            self.status_lbl.config(text="✅ NVIDIA NIM — deepseek-v3", fg="#0be881")
            self.url_var.set("https://integrate.api.nvidia.com/v1")
            self.model_var.set("deepseek-ai/deepseek-v3")
            self.provider_type = "OpenAI_Compatible"

        # ── AIML API ───────────────────────────────────────────────────
        # Keys are long hex/UUID strings, e.g. "abc123ef-..."  or 32+ char random
        elif (
            re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', key_lower)  # UUID format
            or (len(key) >= 32 and re.match(r'^[0-9a-zA-Z_\-]+$', key) and not key.startswith("sk-"))
        ):
            self.status_lbl.config(text="✅ AIML API — Llama-3.3-70B (auto-detected)", fg="#0be881")
            self.url_var.set("https://api.aimlapi.com/v1")
            self.model_var.set("meta-llama/Llama-3.3-70B-Instruct-Turbo")
            self.provider_type = "OpenAI_Compatible"

        # ── Ollama (Local) ─────────────────────────────────────────────
        # User types "ollama" or "local" as the "key" — no real key needed
        elif key_lower in ("ollama", "local", "localhost", "none", "-"):
            self.status_lbl.config(text="✅ Ollama (Local) — llama3.2:3b  |  No key needed!", fg="#0be881")
            self.url_var.set("http://localhost:11434/v1")
            self.model_var.set("llama3.2:3b")
            self.provider_type = "Ollama"

        # ── Unknown ────────────────────────────────────────────────────
        else:
            self.status_lbl.config(
                text="⚠️ Unknown key — set Base URL & Model manually  |  type 'ollama' for local",
                fg="#ffdd59"
            )
            self.provider_type = "OpenAI_Compatible"

        self.auto_filling = False

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.auto_filling = True
                    if data.get("k"): self.api_var.set(data["k"])
                    if data.get("u"): self.url_var.set(data["u"])
                    if data.get("m"): self.model_var.set(data["m"])
                    self.auto_filling = False
            except:
                pass

    def save_settings(self):
        data = {"k": self.api_var.get(), "u": self.url_var.get(), "m": self.model_var.get()}
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except:
            pass

    def log(self, text):
        self.log_box.insert(tk.END, "> " + text + "\n")
        self.log_box.see(tk.END)

    def open_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if self.file_path:
            self.lbl_status_file.config(text=os.path.basename(self.file_path), fg="white")

    def stop_process(self):
        if self.is_running:
            self.is_running = False
            self.log("🛑 STOPPING...")
            self.btn_stop.config(state="disabled", text="Stopping...")

    def reset_all(self):
        if self.is_running:
            return
        self.api_var.set("")
        self.url_var.set("")
        self.model_var.set("")
        self.file_path = ""
        self.lbl_status_file.config(text="No file selected", fg="#808e9b")
        self.resume_var.set("1")
        self.log_box.delete('1.0', tk.END)
        self.total_tokens = 0
        self.token_usage_lbl.config(text="Total AI Tokens Used: 0")

    def start_process(self):
        if not self.file_path or not self.api_var.get().strip():
            messagebox.showwarning("Input Error", "Provide API Key and File.")
            return
        self.save_settings()
        self.is_running = True
        self.btn_start.config(state="disabled")
        self.btn_reset.config(state="disabled")
        self.btn_stop.config(state="normal", text="STOP")
        threading.Thread(target=self.translation_thread, daemon=True).start()

    def build_prompt(self, target_lang, text_payload):
        """
        Build a high-quality direct translation prompt.
        AI translates directly - no Google Translate middleman.
        """
        lang_native = LANG_CODES.get(target_lang, target_lang)

        # Special instructions for Sinhala
        sinhala_note = ""
        if target_lang == "Sinhala":
            sinhala_note = """
SINHALA SPECIFIC RULES:
- Write in natural, everyday spoken Sinhala (කතා බසෙන්).
- Use Sinhala Unicode script (NOT Singlish / romanized).
- Transliterate English character names phonetically into Sinhala script.
  Example: "John" → "ජෝන්", "Sarah" → "සාරා", "Batman" → "බැට්මෑන්"
- Keep sentence length short — suitable for reading on screen in 2-3 seconds.
- Avoid overly formal/literary Sinhala. Use natural everyday words.
- Common words: yes=ඔව්, no=නෑ, I=මම, you=ඔයා/ඔබ, what=මොකද, why=ඇයි, go=යනවා
"""

        prompt = f"""You are a professional subtitle translator. Translate English movie/TV subtitles directly into {target_lang} ({lang_native}).
{sinhala_note}
RULES:
1. Translate EACH line directly into {target_lang}. Do NOT rewrite in English first.
2. Keep character names and proper nouns as transliterations in {target_lang} script.
3. Keep translations short and natural for subtitles.
4. Preserve the meaning, tone and emotion of the original line.
5. Output ONLY the translated lines in this exact format, nothing else:
   ID_X:: [translated text]

INPUT LINES:
{text_payload}

OUTPUT (translate each ID directly to {target_lang}):"""

        return prompt

    def parse_ai_response(self, res_text, chunk_size):
        """Parse AI response and return dict of id -> translated text."""
        results = {}
        for line in res_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Match ID_X:: format
            match = re.match(r'ID_(\d+)\s*::\s*(.+)', line)
            if match:
                idx = int(match.group(1))
                text = match.group(2).strip()
                # Remove any leftover English in parentheses like (translation)
                text = re.sub(r'\s*\(.*?\)\s*$', '', text).strip()
                if 0 <= idx < chunk_size:
                    results[idx] = text
        return results

    def translation_thread(self):
        try:
            target = self.lang_var.get()
            start_chunk = max(1, int(self.resume_var.get()))

            if start_chunk == 1:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".srt",
                    initialfile=f"Translated_{target}.srt"
                )
                if not save_path:
                    raise Exception("Save cancelled")
                open(save_path, 'w', encoding='utf-8').close()
            else:
                save_path = filedialog.askopenfilename(
                    title="Select file to resume",
                    filetypes=[("SRT files", "*.srt")]
                )
                if not save_path:
                    raise Exception("Resume cancelled")

            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()

            raw_blocks = [b.strip() for b in re.split(r'\n\s*\n', data.strip()) if b.strip()]
            parsed_blocks = []
            for b in raw_blocks:
                lines = b.split('\n')
                if len(lines) >= 3:
                    parsed_blocks.append({
                        "index": lines[0].strip(),
                        "time": lines[1].strip(),
                        "text": "\n".join(lines[2:]).strip()
                    })

            c_size = int(self.chunk_var.get())
            total_chunks = (len(parsed_blocks) + c_size - 1) // c_size
            self.log(f"🚀 Started. Blocks: {len(parsed_blocks)} | Chunks: {total_chunks} | Lang: {target}")
            self.log(f"📌 Mode: Direct AI Translation (No Google Translate)")

            for i in range((start_chunk - 1) * c_size, len(parsed_blocks), c_size):
                if not self.is_running:
                    break

                chunk = parsed_blocks[i:i + c_size]
                current_chunk_num = (i // c_size) + 1

                # Build text payload for AI
                text_payload = ""
                for j, b in enumerate(chunk):
                    # Clean HTML tags from source
                    clean_text = re.sub(r'<[^>]+>', '', b['text']).strip()
                    text_payload += f"ID_{j}:: {clean_text}\n"

                prompt = self.build_prompt(target, text_payload)

                success = False
                retry_count = 0

                while not success and self.is_running:
                    try:
                        self.log(f"⚙️ Chunk {current_chunk_num}/{total_chunks}: Translating to {target}...")
                        res_text = ""
                        usage_count = 0
                        api_key = self.api_var.get().strip()

                        if self.provider_type == "Gemini":
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel(
                                self.model_var.get().strip(),
                                generation_config=genai.types.GenerationConfig(
                                    temperature=0.2,
                                    top_p=0.9,
                                )
                            )
                            response = model.generate_content(prompt)
                            res_text = response.text
                            usage_count = response.usage_metadata.total_token_count

                        elif self.provider_type == "Ollama":
                            # Ollama local — no real API key needed
                            client = OpenAI(
                                api_key="ollama",
                                base_url=self.url_var.get().strip()
                            )
                            response = client.chat.completions.create(
                                model=self.model_var.get().strip(),
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.2
                            )
                            res_text = response.choices[0].message.content
                            try:
                                usage_count = response.usage.total_tokens
                            except Exception:
                                usage_count = 0

                        else:
                            # OpenRouter, Groq, HuggingFace, NVIDIA, AIMLAPI
                            client = OpenAI(
                                api_key=api_key,
                                base_url=self.url_var.get().strip() if self.url_var.get() != "N/A" else None
                            )
                            response = client.chat.completions.create(
                                model=self.model_var.get().strip(),
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.2
                            )
                            res_text = response.choices[0].message.content
                            try:
                                usage_count = response.usage.total_tokens
                            except Exception:
                                usage_count = 0

                        if res_text:
                            self.total_tokens += usage_count
                            self.token_usage_lbl.config(text=f"Total AI Tokens Used: {self.total_tokens:,}")

                            # Parse the AI response
                            translations = self.parse_ai_response(res_text, len(chunk))

                            if not translations:
                                self.log(f"⚠️ Parse failed. AI response sample: {res_text[:100]}")
                                raise Exception("Could not parse AI response format")

                            # Build SRT output
                            srt_out = ""
                            for j, orig_b in enumerate(chunk):
                                translated = translations.get(j, "")
                                if not translated:
                                    # Fallback: keep original if translation missing
                                    translated = orig_b['text']
                                    self.log(f"  ⚠️ ID_{j} missing, keeping original")
                                srt_out += f"{orig_b['index']}\n{orig_b['time']}\n{translated}\n\n"

                            with open(save_path, 'a', encoding='utf-8') as f:
                                f.write(srt_out)

                            self.log(f"✅ Chunk {current_chunk_num}/{total_chunks} done! ({len(translations)}/{len(chunk)} lines)")
                            success = True

                    except Exception as e:
                        retry_count += 1
                        err_msg = str(e)[:80]
                        self.log(f"⚠️ Error (retry {retry_count}): {err_msg}")
                        if retry_count >= 5:
                            self.log(f"❌ Chunk {current_chunk_num} failed after 5 retries. Skipping.")
                            # Write originals as fallback
                            srt_out = ""
                            for orig_b in chunk:
                                srt_out += f"{orig_b['index']}\n{orig_b['time']}\n{orig_b['text']}\n\n"
                            with open(save_path, 'a', encoding='utf-8') as f:
                                f.write(srt_out)
                            break
                        wait_time = 20 if "quota" in err_msg.lower() or "429" in err_msg else 10
                        self.log(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)

                if self.is_running and self.delay_enabled.get() and i + c_size < len(parsed_blocks):
                    self.log("⏳ Delaying 15s (free API rate limit protection)...")
                    time.sleep(15)

            if self.is_running:
                messagebox.showinfo("Done!", f"✅ Translation to {target} complete!\nSaved: {save_path}")
                self.log(f"🎉 All done! File saved.")

        except Exception as e:
            if "cancelled" not in str(e).lower():
                self.log(f"❌ CRITICAL ERROR: {str(e)}")
                messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            self.btn_start.config(state="normal")
            self.btn_reset.config(state="normal")
            self.btn_stop.config(state="disabled", text="STOP")


if __name__ == "__main__":
    root = tk.Tk()
    app = HybridSubtitleApp(root)
    root.mainloop()
