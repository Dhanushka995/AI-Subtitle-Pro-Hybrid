import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import google.generativeai as genai
from openai import OpenAI
import threading
import time
import re
import os
import json

CONFIG_FILE = "subtitle_pro_v31_config.json"

LANG_CODES = {
    "Sinhala": "සිංහල",
    "Tamil":   "தமிழ்",
    "Hindi":   "हिन्दी",
    "French":  "français",
    "Spanish": "español",
}

# ── System prompt — sent once as system role (saves tokens every request) ──────
# Model ට කියන්නේ: format ගැන හිතන්නේ නෑ, pure translation only
SYSTEM_SINHALA = """You are a Sinhala subtitle translator. Your only job is to translate English lines into natural spoken Sinhala (සිංහල).

RULES:
1. Output ONLY Sinhala text. Never output English.
2. Use natural everyday spoken Sinhala — NOT formal or literary.
3. Write in Sinhala Unicode script only. Never romanize.
4. Transliterate English names phonetically: John→ජෝන්, Sarah→සාරා, Mike→මයික්, Batman→බැට්මෑන්
5. Keep each translation short — suitable for reading on screen.
6. Preserve the emotion and tone of each line.
7. Output numbered lines ONLY. Example:
   1. සිංහල පරිවර්තනය
   2. සිංහල පරිවර්තනය
   (nothing else — no explanations, no English, no notes)"""

SYSTEM_GENERIC = """You are a professional subtitle translator.
Translate each numbered English line into the target language.
Output numbered lines only — same count as input, nothing else."""


class HybridSubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Subtitle Pro v3.1 — Pure Quality Mode")
        self.root.geometry("720x1000")
        self.root.configure(bg="#1e272e")

        self.is_running      = False
        self.provider_type   = "Unknown"
        self.file_path       = ""
        self.auto_filling    = False
        self.total_tokens    = 0
        self.key_list        = []
        self.current_key_idx = 0

        self._build_ui()
        self.load_settings()

    # ══════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════
    def _build_ui(self):
        r = self.root

        tk.Label(r, text="AI SUBTITLE PRO v3.1  |  Pure Quality Mode",
                 bg="#1e272e", fg="#00d8d6", font=("Arial", 13, "bold")).pack(pady=8)

        # ── API Keys ────────────────────────────────────────────────
        tk.Label(r, text="🔑 Paste API Key(s) — one per line  (multi-key = auto-rotation on limit):",
                 bg="#1e272e", fg="#d2dae2", anchor="w").pack(padx=20, anchor="w")
        tk.Label(r, text="   Gemini · Groq · OpenRouter · HuggingFace · NVIDIA · AIML · Ollama",
                 bg="#1e272e", fg="#808e9b", font=("Arial", 8), anchor="w").pack(padx=20, anchor="w")

        kf = tk.Frame(r, bg="#1e272e")
        kf.pack(padx=20, fill="x")
        self.key_box = tk.Text(kf, height=3, bg="#485460", fg="white",
                               font=("Consolas", 9), insertbackground="white", borderwidth=0)
        self.key_box.pack(fill="x", ipady=5)
        self.key_box.bind("<KeyRelease>", self.on_key_change)

        self.status_lbl = tk.Label(r, text="Waiting for API Key(s)…",
                                   bg="#1e272e", fg="#808e9b", font=("Arial", 9, "bold"),
                                   wraplength=700)
        self.status_lbl.pack(pady=2)

        self.key_indicator = tk.Label(r, text="", bg="#1e272e", fg="#feca57",
                                      font=("Consolas", 7), wraplength=700)
        self.key_indicator.pack()

        # ── Advanced ────────────────────────────────────────────────
        adv = tk.Frame(r, bg="#2f3640", padx=10, pady=8)
        adv.pack(pady=4, fill="x", padx=40)
        tk.Label(adv, text="Base URL:", bg="#2f3640", fg="white").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        tk.Entry(adv, textvariable=self.url_var, width=50,
                 bg="#1e272e", fg="white").grid(row=0, column=1, padx=8, pady=2)
        tk.Label(adv, text="Model:", bg="#2f3640", fg="white").grid(row=1, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_var.trace_add("write", self.on_model_manual_change)
        tk.Entry(adv, textvariable=self.model_var, width=50,
                 bg="#1e272e", fg="white").grid(row=1, column=1, padx=8, pady=2)

        # ── File ────────────────────────────────────────────────────
        tk.Button(r, text="📂  Select English SRT File", command=self.open_file,
                  bg="#0fb9b1", fg="white", font=("Arial", 10, "bold"), width=30).pack(pady=8)
        self.lbl_file = tk.Label(r, text="No file selected", bg="#1e272e", fg="#808e9b")
        self.lbl_file.pack()

        # ── Settings ────────────────────────────────────────────────
        sf = tk.Frame(r, bg="#1e272e")
        sf.pack(pady=4)

        tk.Label(sf, text="Chunk:", bg="#1e272e", fg="white").grid(row=0, column=0, padx=4)
        self.chunk_var = tk.StringVar(value="10")
        ttk.Combobox(sf, textvariable=self.chunk_var,
                     values=["5", "8", "10", "12", "15", "20"], width=5).grid(row=0, column=1, padx=4)

        tk.Label(sf, text="Language:", bg="#1e272e", fg="white").grid(row=0, column=2, padx=12)
        self.lang_var = tk.StringVar(value="Sinhala")
        ttk.Combobox(sf, textvariable=self.lang_var,
                     values=list(LANG_CODES.keys()), width=10).grid(row=0, column=3, padx=4)

        tk.Label(sf, text="Delay (s):", bg="#1e272e", fg="white").grid(row=0, column=4, padx=12)
        self.delay_var = tk.StringVar(value="5")
        ttk.Combobox(sf, textvariable=self.delay_var,
                     values=["0", "3", "5", "10", "15", "20"], width=5).grid(row=0, column=5, padx=4)

        # Quality info label
        tk.Label(sf,
                 text="✅ Pure Quality Mode — model focuses on translation only (no format stress)",
                 bg="#1e272e", fg="#0be881", font=("Arial", 8)).grid(
            row=1, column=0, columnspan=6, pady=4)

        tk.Label(sf, text="Start from Chunk:", bg="#1e272e", fg="#ff9f43").grid(
            row=2, column=0, columnspan=3, sticky="e")
        self.resume_var = tk.StringVar(value="1")
        tk.Entry(sf, textvariable=self.resume_var, width=6,
                 bg="#ff9f43", font=("Arial", 10, "bold")).grid(row=2, column=3, sticky="w", padx=4)

        # ── Log ─────────────────────────────────────────────────────
        self.log_box = tk.Text(r, height=18, width=82, bg="#000", fg="#0be881",
                               font=("Consolas", 9))
        self.log_box.pack(pady=4, padx=16)

        self.token_lbl = tk.Label(r, text="Total AI Tokens Used: 0",
                                  bg="#1e272e", fg="#feca57", font=("Arial", 10, "bold"))
        self.token_lbl.pack(pady=3)

        # ── Buttons ─────────────────────────────────────────────────
        bf = tk.Frame(r, bg="#1e272e")
        bf.pack(pady=8)
        self.btn_start = tk.Button(bf, text="START", command=self.start_process,
                                   bg="#0984e3", fg="white", font=("Arial", 12, "bold"),
                                   width=14, height=2)
        self.btn_start.grid(row=0, column=0, padx=8)
        self.btn_stop = tk.Button(bf, text="STOP", command=self.stop_process,
                                  bg="#2d3436", fg="white", font=("Arial", 12, "bold"),
                                  width=14, height=2, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=8)
        self.btn_reset = tk.Button(bf, text="Reset", command=self.reset_all,
                                   bg="#d63031", fg="white", font=("Arial", 12, "bold"),
                                   width=14, height=2)
        self.btn_reset.grid(row=0, column=2, padx=8)

    # ══════════════════════════════════════════════════════════════════
    # KEY DETECTION
    # ══════════════════════════════════════════════════════════════════
    def detect_provider(self, key):
        """Return (provider_type, base_url, default_model, display_label)."""
        k  = key.strip()
        kl = k.lower()

        if k.startswith("AIza"):
            return ("Gemini",
                    "N/A",
                    "gemini-1.5-flash",
                    "Google Gemini · gemini-1.5-flash")
        if k.startswith("sk-or-"):
            return ("OpenAI_Compatible",
                    "https://openrouter.ai/api/v1",
                    "google/gemini-2.0-flash-lite:free",
                    "OpenRouter · gemini-2.0-flash-lite:free")
        if k.startswith("gsk_"):
            return ("OpenAI_Compatible",
                    "https://api.groq.com/openai/v1",
                    "llama-3.3-70b-versatile",
                    "Groq · llama-3.3-70b-versatile")
        if k.startswith("hf_"):
            return ("OpenAI_Compatible",
                    "https://api-inference.huggingface.co/v1",
                    "Qwen/Qwen2.5-72B-Instruct",
                    "HuggingFace · Qwen2.5-72B")
        if k.startswith("nvapi-"):
            return ("OpenAI_Compatible",
                    "https://integrate.api.nvidia.com/v1",
                    "deepseek-ai/deepseek-v3",
                    "NVIDIA NIM · deepseek-v3")
        if kl in ("ollama", "local", "localhost", "none", "-"):
            return ("Ollama",
                    "http://localhost:11434/v1",
                    "llama3.2:3b",
                    "Ollama LOCAL · llama3.2:3b")
        if (re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', kl)
                or (len(k) >= 32 and re.match(r'^[0-9a-zA-Z_\-]+$', k)
                    and not k.startswith("sk-"))):
            return ("OpenAI_Compatible",
                    "https://api.aimlapi.com/v1",
                    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    "AIML API · Llama-3.3-70B")
        return ("OpenAI_Compatible", "", "", "⚠️ Unknown — set URL & Model manually")

    def parse_all_keys(self):
        raw = self.key_box.get("1.0", tk.END)
        return [k.strip() for k in re.split(r'[\n,]+', raw) if k.strip()]

    def on_key_change(self, *args):
        keys = self.parse_all_keys()
        if not keys:
            self.status_lbl.config(
                text="Waiting for API Key(s)… (type 'ollama' for local)", fg="#808e9b")
            self.key_indicator.config(text="")
            return

        self.key_list        = keys
        self.current_key_idx = 0

        self.auto_filling = True
        ptype, url, model, label = self.detect_provider(keys[0])
        self.provider_type = ptype
        self.url_var.set(url)
        # Only auto-fill model if field is currently EMPTY — never overwrite manual input
        if model and not self.model_var.get().strip():
            self.model_var.set(model)
        self.auto_filling = False

        if len(keys) == 1:
            self.status_lbl.config(text=f"✅  {label}", fg="#0be881")
            self.key_indicator.config(text="")
        else:
            self.status_lbl.config(
                text=f"✅  {len(keys)} keys — auto-rotation when limit hit!", fg="#0be881")
            row = "  |  ".join(
                f"[{i+1}] {self.detect_provider(k)[3]}" for i, k in enumerate(keys))
            self.key_indicator.config(text=row)

    def on_model_manual_change(self, *args):
        if not self.auto_filling and self.model_var.get().strip():
            self.status_lbl.config(
                text=f"✅  Manual model: {self.model_var.get()}", fg="#0be881")

    # ══════════════════════════════════════════════════════════════════
    # SETTINGS
    # ══════════════════════════════════════════════════════════════════
    def load_settings(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.auto_filling = True
            if d.get("keys"):
                self.key_box.delete("1.0", tk.END)
                self.key_box.insert("1.0", "\n".join(d["keys"]))
            if d.get("u"): self.url_var.set(d["u"])
            self.auto_filling = False
            # on_key_change runs first — then restore saved model on top
            self.on_key_change()
            # Saved model always wins — set it LAST so nothing can overwrite it
            if d.get("m"):
                self.model_var.set(d["m"])
        except Exception:
            pass

    def save_settings(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"keys": self.parse_all_keys(),
                           "u":    self.url_var.get(),
                           "m":    self.model_var.get()}, f)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════
    # PROMPT — simple numbered list, zero format pressure on model
    # ══════════════════════════════════════════════════════════════════
    def build_messages(self, target_lang, lines):
        """
        lines = list of plain English strings (already HTML-stripped).
        Returns (system_str, user_str).

        The user message is just a simple numbered list — NO ID_X:: format.
        Model only thinks about translation quality.
        Python code handles the alignment locally after.
        """
        lang_native = LANG_CODES.get(target_lang, target_lang)
        system = SYSTEM_SINHALA if target_lang == "Sinhala" else (
            SYSTEM_GENERIC + f"\nTarget language: {target_lang} ({lang_native}).")

        numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))

        user = (f"Translate these {len(lines)} English subtitle lines into "
                f"{target_lang} ({lang_native}).\n\n"
                f"{numbered}\n\n"
                f"Output {len(lines)} numbered lines in {target_lang} only:")

        return system, user

    # ══════════════════════════════════════════════════════════════════
    # PARSE RESPONSE — extract numbered translations into ordered list
    # ══════════════════════════════════════════════════════════════════
    def parse_response(self, res_text, expected_count):
        """
        Parse '1. translation\n2. translation\n...' into a dict {0: text, 1: text}.
        Very robust — handles missing numbers, extra text, etc.
        """
        results = {}
        for line in res_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Match "1. text" or "1) text" or "1: text"
            m = re.match(r'^(\d+)[.):\-]\s*(.+)', line)
            if m:
                idx  = int(m.group(1)) - 1   # convert 1-based to 0-based
                text = m.group(2).strip()
                # Drop accidental trailing English annotations
                text = re.sub(r'\s*\([A-Za-z][^)]*\)\s*$', '', text).strip()
                if 0 <= idx < expected_count and text:
                    results[idx] = text
        return results

    # ══════════════════════════════════════════════════════════════════
    # AI CALL — with automatic key rotation on rate-limit errors
    # ══════════════════════════════════════════════════════════════════
    def call_ai(self, system_prompt, user_prompt):
        total_keys = len(self.key_list)
        tried      = 0

        while tried < total_keys:
            key   = self.key_list[self.current_key_idx]
            ptype, auto_url, _, _ = self.detect_provider(key)
            url   = self.url_var.get().strip() or auto_url
            model = self.model_var.get().strip()

            try:
                if ptype == "Gemini":
                    genai.configure(api_key=key)
                    gm = genai.GenerativeModel(
                        model,
                        system_instruction=system_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1, top_p=0.95)
                    )
                    resp = gm.generate_content(user_prompt)
                    return resp.text, resp.usage_metadata.total_token_count

                elif ptype == "Ollama":
                    client = OpenAI(api_key="ollama", base_url=url)
                    r = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user",   "content": user_prompt}],
                        temperature=0.1)
                    try:    usage = r.usage.total_tokens
                    except: usage = 0
                    return r.choices[0].message.content, usage

                else:
                    client = OpenAI(api_key=key,
                                    base_url=url if url not in ("N/A", "") else None)
                    r = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user",   "content": user_prompt}],
                        temperature=0.1)
                    try:    usage = r.usage.total_tokens
                    except: usage = 0
                    return r.choices[0].message.content, usage

            except Exception as e:
                err      = str(e)
                is_limit = any(x in err.lower() for x in
                               ["429", "quota", "rate_limit", "rate limit",
                                "exceeded", "too many", "limit"])
                if is_limit and total_keys > 1:
                    next_idx = (self.current_key_idx + 1) % total_keys
                    self.log(f"🔄 Key [{self.current_key_idx+1}] limit → switching to key [{next_idx+1}]…")
                    self.current_key_idx = next_idx
                    tried += 1
                    time.sleep(2)
                    continue
                raise

        raise Exception("All API keys hit rate limits. Wait or add more keys.")

    # ══════════════════════════════════════════════════════════════════
    # UI HELPERS
    # ══════════════════════════════════════════════════════════════════
    def log(self, text):
        self.log_box.insert(tk.END, "> " + text + "\n")
        self.log_box.see(tk.END)

    def open_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if self.file_path:
            self.lbl_file.config(text=os.path.basename(self.file_path), fg="white")

    def stop_process(self):
        if self.is_running:
            self.is_running = False
            self.log("🛑 Stopping after this chunk…")
            self.btn_stop.config(state="disabled", text="Stopping…")

    def reset_all(self):
        if self.is_running:
            return
        self.key_box.delete("1.0", tk.END)
        self.url_var.set("")
        self.model_var.set("")
        self.file_path = ""
        self.lbl_file.config(text="No file selected", fg="#808e9b")
        self.resume_var.set("1")
        self.log_box.delete("1.0", tk.END)
        self.total_tokens = 0
        self.token_lbl.config(text="Total AI Tokens Used: 0")
        self.key_list        = []
        self.current_key_idx = 0
        self.status_lbl.config(text="Waiting for API Key(s)…", fg="#808e9b")
        self.key_indicator.config(text="")

    def start_process(self):
        self.key_list = self.parse_all_keys()
        if not self.file_path or not self.key_list:
            messagebox.showwarning("Input Error",
                                   "Add at least one API key and select an SRT file.")
            return
        self.save_settings()
        self.current_key_idx = 0
        self.is_running      = True
        self.btn_start.config(state="disabled")
        self.btn_reset.config(state="disabled")
        self.btn_stop.config(state="normal", text="STOP")
        threading.Thread(target=self.translation_thread, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════
    # MAIN TRANSLATION THREAD
    # ══════════════════════════════════════════════════════════════════
    def translation_thread(self):
        try:
            target      = self.lang_var.get()
            start_chunk = max(1, int(self.resume_var.get()))
            delay_s     = float(self.delay_var.get())

            # Output file
            if start_chunk == 1:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".srt",
                    initialfile=f"Translated_{target}.srt")
                if not save_path:
                    raise Exception("Save cancelled")
                open(save_path, 'w', encoding='utf-8').close()
            else:
                save_path = filedialog.askopenfilename(
                    title="Select existing SRT to resume/append",
                    filetypes=[("SRT files", "*.srt")])
                if not save_path:
                    raise Exception("Resume cancelled")

            # Parse source SRT
            with open(self.file_path, 'r', encoding='utf-8') as f:
                raw = f.read()

            blocks = [b.strip() for b in re.split(r'\n\s*\n', raw.strip()) if b.strip()]
            parsed = []
            for b in blocks:
                lines = b.split('\n')
                if len(lines) >= 3:
                    parsed.append({
                        "index": lines[0].strip(),
                        "time":  lines[1].strip(),
                        "text":  "\n".join(lines[2:]).strip()
                    })

            c_size       = int(self.chunk_var.get())
            total_chunks = (len(parsed) + c_size - 1) // c_size

            self.log(f"🚀 v3.1 Pure Quality | Blocks: {len(parsed)} | Chunks: {total_chunks} | Lang: {target}")
            self.log(f"🔑 Keys: {len(self.key_list)}  |  Chunk size: {c_size}  |  Delay: {int(delay_s)}s")
            self.log(f"💡 Format: Simple numbered list — model focuses 100% on translation quality")

            for i in range((start_chunk - 1) * c_size, len(parsed), c_size):
                if not self.is_running:
                    break

                chunk     = parsed[i:i + c_size]
                chunk_num = (i // c_size) + 1

                # ── Build plain English lines list (strip HTML tags) ─
                eng_lines = []
                for b in chunk:
                    clean = re.sub(r'<[^>]+>', '', b['text']).strip()
                    # Flatten multi-line subtitles into one line for translation
                    clean = re.sub(r'\s*\n\s*', ' / ', clean)
                    eng_lines.append(clean)

                sys_p, usr_p = self.build_messages(target, eng_lines)

                success = False
                retry   = 0

                while not success and self.is_running:
                    try:
                        # Show actual provider + actual model being used
                        provider_label = self.detect_provider(
                            self.key_list[self.current_key_idx])[3].split("·")[0].strip()
                        actual_model = self.model_var.get().strip()
                        self.log(f"⚙️  Chunk {chunk_num}/{total_chunks}"
                                 f" — [{self.current_key_idx+1}] {provider_label} · {actual_model}")

                        res_text, usage = self.call_ai(sys_p, usr_p)

                        self.total_tokens += usage
                        self.token_lbl.config(
                            text=f"Total AI Tokens Used: {self.total_tokens:,}")

                        # ── Parse numbered response into dict ────────
                        translations = self.parse_response(res_text, len(chunk))

                        if not translations:
                            self.log(f"⚠️  Parse failed. Raw output: {res_text[:150]}")
                            raise Exception("Could not parse AI response")

                        # ── Build SRT output — align by position ─────
                        srt_out = ""
                        ok_count = 0
                        for j, orig in enumerate(chunk):
                            if j in translations:
                                translated = translations[j]
                                ok_count  += 1
                            else:
                                # Fallback: keep original English
                                translated = orig['text']
                                self.log(f"   ⚠️  Line {j+1} missing → kept original")
                            srt_out += f"{orig['index']}\n{orig['time']}\n{translated}\n\n"

                        with open(save_path, 'a', encoding='utf-8') as f:
                            f.write(srt_out)

                        self.log(f"✅  Chunk {chunk_num}/{total_chunks}"
                                 f" — {ok_count}/{len(chunk)} lines translated")
                        success = True

                    except Exception as e:
                        retry += 1
                        self.log(f"⚠️  Error (attempt {retry}/5): {str(e)[:100]}")
                        if retry >= 5:
                            self.log(f"❌  Giving up chunk {chunk_num} → writing originals")
                            srt_out = "".join(
                                f"{b['index']}\n{b['time']}\n{b['text']}\n\n"
                                for b in chunk)
                            with open(save_path, 'a', encoding='utf-8') as f:
                                f.write(srt_out)
                            break
                        time.sleep(15)

                # Delay between chunks
                if self.is_running and delay_s > 0 and i + c_size < len(parsed):
                    self.log(f"⏳  Waiting {int(delay_s)}s…")
                    time.sleep(delay_s)

            if self.is_running:
                self.log("🎉 Translation complete!")
                messagebox.showinfo(
                    "Done!",
                    f"Translation to {target} complete!\nSaved: {save_path}")

        except Exception as e:
            if "cancelled" not in str(e).lower():
                self.log(f"❌ CRITICAL: {e}")
                messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            self.btn_start.config(state="normal")
            self.btn_reset.config(state="normal")
            self.btn_stop.config(state="disabled", text="STOP")


if __name__ == "__main__":
    root = tk.Tk()
    app  = HybridSubtitleApp(root)
    root.mainloop()
