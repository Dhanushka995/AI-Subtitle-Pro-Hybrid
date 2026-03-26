import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import google.generativeai as genai
from openai import OpenAI
from deep_translator import GoogleTranslator
import threading
import time
import re
import os
import requests
import json

# Configuration for saving settings
CONFIG_FILE = "ai_sub_pro_config.json"

class HybridSubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Subtitle Pro v1.0 (Hybrid Tech)")
        self.root.geometry("650x850")
        self.root.configure(bg="#1e272e")

        self.is_running = False
        self.file_path = ""
        self.current_thread = None

        # --- UI ELEMENTS ---
        tk.Label(root, text="AI SUBTITLE PRO - HYBRID", bg="#1e272e", fg="#00d8d6", font=("Arial", 16, "bold")).pack(pady=15)

        tk.Label(root, text="Paste API Key (Slot 1):", bg="#1e272e", fg="#d2dae2").pack(pady=(5, 0))
        self.api1_var = tk.StringVar()
        self.api1_var.trace_add("write", self.on_key1_change)
        self.api1_entry = tk.Entry(root, textvariable=self.api1_var, width=65, show="*", bg="#485460", fg="white", borderwidth=0)
        self.api1_entry.pack(pady=5, ipady=6)

        self.status1_lbl = tk.Label(root, text="Waiting for Key...", bg="#1e272e", fg="#808e9b", font=("Arial", 9, "bold"))
        self.status1_lbl.pack(pady=2)

        # Advanced Settings (Auto-filled)
        self.adv_frame = tk.Frame(root, bg="#2f3640", padx=10, pady=10)
        self.adv_frame.pack(pady=10, fill="x", padx=40)
        
        tk.Label(self.adv_frame, text="Base URL:", bg="#2f3640", fg="white").grid(row=0, column=0, sticky="w")
        self.url1_var = tk.StringVar()
        tk.Entry(self.adv_frame, textvariable=self.url1_var, width=50, bg="#1e272e", fg="white").grid(row=0, column=1, padx=10, pady=2)

        tk.Label(self.adv_frame, text="Model Name:", bg="#2f3640", fg="white").grid(row=1, column=0, sticky="w")
        self.model1_var = tk.StringVar()
        tk.Entry(self.adv_frame, textvariable=self.model1_var, width=50, bg="#1e272e", fg="white").grid(row=1, column=1, padx=10, pady=2)

        tk.Button(root, text="📂 Select English SRT File", command=self.open_file, bg="#0fb9b1", fg="white", font=("Arial", 10, "bold"), width=30).pack(pady=10)
        self.lbl_status_file = tk.Label(root, text="No file selected", bg="#1e272e", fg="#808e9b")
        self.lbl_status_file.pack()

        # Settings
        settings_frame = tk.Frame(root, bg="#1e272e")
        settings_frame.pack(pady=10)
        
        tk.Label(settings_frame, text="Chunk Size:", bg="#1e272e", fg="white").grid(row=0, column=0, padx=5)
        self.chunk_var = tk.StringVar(value="40")
        ttk.Combobox(settings_frame, textvariable=self.chunk_var, values=["10", "20", "30", "40", "50"], width=5).grid(row=0, column=1, padx=5)
        
        tk.Label(settings_frame, text="Language:", bg="#1e272e", fg="white").grid(row=0, column=2, padx=15)
        self.lang_var = tk.StringVar(value="Sinhala")
        ttk.Combobox(settings_frame, textvariable=self.lang_var, values=["Sinhala", "Tamil", "Hindi"], width=10).grid(row=0, column=3, padx=5)

        self.delay_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Enable 15s Delay", variable=self.delay_enabled, bg="#1e272e", fg="#0be881", selectcolor="#1e272e").grid(row=1, column=0, columnspan=4, pady=10)

        # Log Window
        self.log_box = tk.Text(root, height=10, width=75, bg="#000000", fg="#0be881", font=("Consolas", 9))
        self.log_box.pack(pady=5, padx=20)

        # Buttons
        btn_frame = tk.Frame(root, bg="#1e272e")
        btn_frame.pack(pady=15)

        self.btn_start = tk.Button(btn_frame, text="START", command=self.start_process, bg="#0984e3", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = tk.Button(btn_frame, text="STOP", command=self.stop_process, bg="#2d3436", fg="white", font=("Arial", 12, "bold"), width=15, height=2, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.btn_reset = tk.Button(btn_frame, text="Reset", command=self.reset_all, bg="#d63031", fg="white", font=("Arial", 12, "bold"), width=15, height=2)
        self.btn_reset.grid(row=0, column=2, padx=10)

        self.load_settings()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("k1"): self.api1_var.set(data["k1"])
                    if data.get("u1"): self.url1_var.set(data["u1"])
                    if data.get("m1"): self.model1_var.set(data["m1"])
            except: pass

    def save_settings(self):
        data = {"k1": self.api1_var.get(), "u1": self.url1_var.get(), "m1": self.model1_var.get()}
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(data, f)
        except: pass

    def log(self, text):
        self.log_box.insert(tk.END, "> " + text + "\n")
        self.log_box.see(tk.END)

    def on_key1_change(self, *args):
        key = self.api1_var.get().strip()
        if not key: return
        if key.startswith("AIza"):
            self.status1_lbl.config(text="✅ Detected: Google Gemini", fg="#0be881")
            self.url1_var.set("N/A"); self.model1_var.set("gemini-1.5-flash")
        elif key.startswith("sk-or-"):
            self.status1_lbl.config(text="✅ Detected: OpenRouter", fg="#0be881")
            self.url1_var.set("https://openrouter.ai/api/v1"); self.model1_var.set("google/gemini-2.0-flash-lite-preview-02-05:free")
        elif key.startswith("gsk_"):
            self.status1_lbl.config(text="✅ Detected: Groq API", fg="#0be881")
            self.url1_var.set("https://api.groq.com/openai/v1"); self.model1_var.set("llama-3.3-70b-versatile")
        else:
            self.status1_lbl.config(text="⚠️ Unknown Key: Enter URL manually", fg="#ffdd59")

    def open_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if self.file_path:
            self.lbl_status_file.config(text=os.path.basename(self.file_path), fg="white")

    def stop_process(self):
        if self.is_running:
            self.is_running = False
            self.log("🛑 STOPPING... Safely aborting.")
            self.btn_stop.config(state="disabled", text="Stopping...")

    def reset_all(self):
        if self.is_running: return
        self.api1_var.set(""); self.url1_var.set(""); self.model1_var.set(""); self.file_path = ""
        self.lbl_status_file.config(text="No file selected", fg="#808e9b")
        self.log_box.delete('1.0', tk.END)

    def start_process(self):
        if not self.file_path or not self.api1_var.get().strip():
            messagebox.showwarning("Input Error", "Provide Key and File.")
            return
        self.save_settings()
        self.is_running = True
        self.btn_start.config(state="disabled"); self.btn_reset.config(state="disabled"); self.btn_stop.config(state="normal", text="STOP")
        threading.Thread(target=self.translation_thread, daemon=True).start()

    def translation_thread(self):
        try:
            target_lang = self.lang_var.get()
            save_path = filedialog.asksaveasfilename(defaultextension=".srt", initialfile=f"Hybrid_{target_lang}.srt")
            if not save_path: raise Exception("Save cancelled")
            open(save_path, 'w', encoding='utf-8').close()

            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()

            raw_blocks = [b.strip() for b in re.split(r'\n\s*\n', data.strip()) if b.strip()]
            c_size = int(self.chunk_var.get())
            total_chunks = (len(raw_blocks) // c_size) + 1
            
            self.log(f"Starting Hybrid Mode... Total Blocks: {len(raw_blocks)}")

            for i in range(0, len(raw_blocks), c_size):
                if not self.is_running: break
                chunk = raw_blocks[i:i + c_size]
                
                text_payload = ""
                for j, b in enumerate(chunk):
                    lines = b.split('\n')
                    text_payload += f"ID_{j}:: {' '.join(lines[2:])}\n"
                
                prompt = f"""You are a professional movie subtitle simplifier.
1. Rewrite these English subtitles into VERY simple, plain English. Remove slang.
2. Identify names (people/places) and replace with tags like [N1], [N2].
3. Provide Sinhala transliteration for those names.
Format: ID_X::[Simple Text] ||| [N1]=SinhalaName
{text_payload}"""
                
                success = False
                while not success and self.is_running:
                    try:
                        self.log(f"⚙️ Chunk {(i//c_size)+1}: AI Processing...")
                        res_text = ""
                        if self.api1_var.get().startswith("AIza"):
                            genai.configure(api_key=self.api1_var.get())
                            m = genai.GenerativeModel(self.model1_var.get())
                            res_text = m.generate_content(prompt).text
                        else:
                            client = OpenAI(api_key=self.api1_var.get(), base_url=self.url1_var.get() if self.url1_var.get() != "N/A" else None)
                            res_text = client.chat.completions.create(model=self.model1_var.get(), messages=[{"role": "user", "content": prompt}]).choices[0].message.content

                        if res_text:
                            self.log(f"🌍 Chunk {(i//c_size)+1}: Google Translating...")
                            extracted, mappings, ids = [], [], []
                            for line in res_text.strip().split('\n'):
                                if "ID_" in line and "::" in line:
                                    id_p, rest = line.split("::", 1)
                                    t_p, n_p = rest.split("|||", 1) if "|||" in rest else (rest, "NONE")
                                    extracted.append(t_p.strip()); ids.append(int(id_p.replace("ID_", "").strip()))
                                    m_map = {}
                                    if "NONE" not in n_p:
                                        for p in n_p.split(','):
                                            if "=" in p: k, v = p.split('=', 1); m_map[k.strip()] = v.strip()
                                    mappings.append(m_map)

                            translator = GoogleTranslator(source='en', target='si')
                            translations = translator.translate_batch(extracted)
                            
                            srt_out = ""
                            for j, t_text in enumerate(translations):
                                for tag, name in mappings[j].items(): t_text = t_text.replace(tag, name)
                                orig_l = chunk[ids[j]].split('\n')
                                srt_out += f"{orig_l[0]}\n{orig_l[1]}\n{t_text}\n\n"
                            
                            with open(save_path, 'a', encoding='utf-8') as f: f.write(srt_out)
                            self.log(f"✅ Chunk {(i//c_size)+1} success!")
                            success = True
                    except Exception as e:
                        self.log(f"⚠️ Error: {str(e)[:40]}... Retrying")
                        time.sleep(15)

                if self.is_running and self.delay_enabled.get() and i + c_size < len(raw_blocks):
                    self.log("⏳ Delaying 15s...")
                    time.sleep(15)

            if self.is_running: messagebox.showinfo("Done", "Success!")
        except Exception as e: self.log(f"Error: {str(e)}")
        finally:
            self.is_running = False
            self.btn_start.config(state="normal"); self.btn_reset.config(state="normal"); self.btn_stop.config(state="disabled", text="STOP")

if __name__ == "__main__":
    root = tk.Tk(); app = HybridSubtitleApp(root); root.mainloop()
