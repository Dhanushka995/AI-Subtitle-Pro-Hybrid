import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
import json
import time
import threading
import os

class SubtitleTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Subtitle Translator Pro - Anti Limit Edition")
        self.root.geometry("750x700")
        self.root.configure(bg="#1e2124")

        self.is_running = False
        self.srt_blocks =[]
        self.output_file = ""

        self.setup_ui()

    def setup_ui(self):
        # --- API Key Section ---
        tk.Label(self.root, text="Paste API Key (Google, Groq, OpenRouter):", bg="#1e2124", fg="white", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.api_key_entry = tk.Entry(self.root, width=75, bg="#2c2f33", fg="white", insertbackground="white", font=("Consolas", 10))
        self.api_key_entry.pack(pady=5)
        self.api_key_entry.bind("<KeyRelease>", self.auto_detect_api)

        self.detect_label = tk.Label(self.root, text="Waiting for API Key...", bg="#1e2124", fg="#f1c40f", font=("Arial", 10, "bold"))
        self.detect_label.pack(pady=5)

        # --- URL and Model Section ---
        frame_url = tk.Frame(self.root, bg="#2c2f33", padx=15, pady=15)
        frame_url.pack(pady=10, fill="x", padx=25)

        tk.Label(frame_url, text="Base URL:", bg="#2c2f33", fg="white", font=("Arial", 9)).grid(row=0, column=0, sticky="w", pady=5)
        self.base_url_entry = tk.Entry(frame_url, width=60, bg="#1e2124", fg="white", insertbackground="white")
        self.base_url_entry.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(frame_url, text="Model Name:", bg="#2c2f33", fg="white", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=5)
        self.model_entry = tk.Entry(frame_url, width=60, bg="#1e2124", fg="white", insertbackground="white")
        self.model_entry.grid(row=1, column=1, pady=5, padx=10)

        # --- File Selection ---
        self.btn_select = tk.Button(self.root, text="📁 Select English SRT File", bg="#1abc9c", fg="white", font=("Arial", 11, "bold"), command=self.select_file, cursor="hand2")
        self.btn_select.pack(pady=15)
        self.file_label = tk.Label(self.root, text="No file selected", bg="#1e2124", fg="#bdc3c7")
        self.file_label.pack()

        # --- Settings Section ---
        frame_settings = tk.Frame(self.root, bg="#1e2124")
        frame_settings.pack(pady=10)

        tk.Label(frame_settings, text="Chunk Size:", bg="#1e2124", fg="white").grid(row=0, column=0, padx=5)
        self.chunk_size_var = tk.StringVar(value="30")
        tk.Entry(frame_settings, textvariable=self.chunk_size_var, width=5, justify="center").grid(row=0, column=1, padx=5)

        tk.Label(frame_settings, text="Start from Chunk:", bg="#1e2124", fg="#e67e22").grid(row=0, column=2, padx=5)
        self.start_chunk_var = tk.StringVar(value="1")
        tk.Entry(frame_settings, textvariable=self.start_chunk_var, width=5, bg="#e67e22", fg="white", justify="center", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)

        self.delay_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame_settings, text="Enable Anti-Limit (Smart Delay)", variable=self.delay_var, bg="#1e2124", fg="#2ecc71", selectcolor="#2c2f33", activebackground="#1e2124", activeforeground="#2ecc71").grid(row=1, column=0, columnspan=4, pady=10)

        # --- Log Console ---
        self.console = scrolledtext.ScrolledText(self.root, width=85, height=10, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.console.pack(pady=10, padx=25)

        # --- Buttons ---
        frame_btns = tk.Frame(self.root, bg="#1e2124")
        frame_btns.pack(pady=10)

        self.btn_start = tk.Button(frame_btns, text="▶ START", width=15, bg="#3498db", fg="white", font=("Arial", 12, "bold"), command=self.start_translation, cursor="hand2")
        self.btn_start.grid(row=0, column=0, padx=15)

        self.btn_stop = tk.Button(frame_btns, text="⏹ STOP", width=15, bg="#e74c3c", fg="white", font=("Arial", 12, "bold"), command=self.stop_translation, cursor="hand2")
        self.btn_stop.grid(row=0, column=1, padx=15)

    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def auto_detect_api(self, event=None):
        key = self.api_key_entry.get().strip()
        if key.startswith("sk-or"):
            self.detect_label.config(text="✔ Detected: OpenRouter", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://openrouter.ai/api/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "google/gemini-2.0-flash-lite-preview-02-05:free")
        elif key.startswith("gsk_"):
            self.detect_label.config(text="✔ Detected: Groq", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://api.groq.com/openai/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "llama3-8b-8192")
        elif len(key) == 39: # Google API keys
            self.detect_label.config(text="✔ Detected: Google AI Studio (Gemini)", fg="#3498db")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://generativelanguage.googleapis.com/v1beta")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "gemini-2.0-flash")
        else:
            self.detect_label.config(text="Waiting for API Key...", fg="#f1c40f")

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("SRT Files", "*.srt")])
        if file_path:
            self.file_label.config(text=os.path.basename(file_path))
            self.output_file = file_path.replace(".srt", "_translated.srt")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into blocks properly
                self.srt_blocks = [block.strip() for block in content.split("\n\n") if block.strip()]
                self.log(f"Loaded {len(self.srt_blocks)} subtitle blocks successfully.")
            except Exception as e:
                self.log(f"Error reading file: {e}")

    def call_api(self, text_chunk, api_key, base_url, model):
        # Super optimized System Prompt for spoken Sinhala and strict formatting
        system_prompt = """You are an expert subtitle translator. Translate the following English SRT subtitle chunk into natural, conversational, and spoken Sinhala (කතා කරන සිංහල). 
RULES:
1. DO NOT use formal or literary Sinhala (සාහිත්‍ය සිංහල). Use the exact words people use in daily conversations.
2. DO NOT translate character names, city names, or specific English terms (e.g., 'Sir', 'Laptop', 'FBI').
3. STRICTLY maintain the original SRT formatting. Do not change the sequence numbers or the timestamps.
4. Output ONLY the translated SRT blocks. No extra text, no markdown code blocks."""
        
        headers = {"Content-Type": "application/json"}
        
        try:
            if "generativelanguage.googleapis.com" in base_url:
                # Google Gemini API Format
                url = f"{base_url}/models/{model}:generateContent?key={api_key}"
                payload = {
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": text_chunk}]}],
                    "generationConfig": {"temperature": 0.4}
                }
            else:
                # OpenAI Compatible Format (OpenRouter, Groq)
                url = f"{base_url}/chat/completions"
                headers["Authorization"] = f"Bearer {api_key}"
                payload = {
                    "model": model,
                    "messages":[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_chunk}
                    ],
                    "temperature": 0.4
                }

            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "generativelanguage.googleapis.com" in base_url:
                    result = data['candidates'][0]['content']['parts'][0]['text']
                else:
                    result = data['choices'][0]['message']['content']
                
                # Clean up markdown code blocks if AI added them
                result = result.replace("```srt", "").replace("```", "").strip()
                return result
                
            elif response.status_code == 429:
                return "ERROR_429"
            else:
                return f"ERROR: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"ERROR: {str(e)}"

    def process_translation(self):
        if not self.srt_blocks:
            self.log("Error: Please select an SRT file first.")
            self.is_running = False
            return

        api_key = self.api_key_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        model = self.model_entry.get().strip()
        
        try:
            chunk_size = int(self.chunk_size_var.get())
            start_chunk = int(self.start_chunk_var.get()) - 1
        except ValueError:
            self.log("Error: Chunk size and Start chunk must be numbers.")
            self.is_running = False
            return

        if not api_key:
            self.log("Error: API Key is missing.")
            self.is_running = False
            return

        # Create chunks
        chunks = [self.srt_blocks[i:i + chunk_size] for i in range(0, len(self.srt_blocks), chunk_size)]
        total_chunks = len(chunks)
        
        if start_chunk < 0 or start_chunk >= total_chunks:
            self.log("Error: Invalid Start Chunk number.")
            self.is_running = False
            return

        self.log(f"Starting translation... Total Chunks: {total_chunks}")
        self.log(f"Saving to: {os.path.basename(self.output_file)}")

        for i in range(start_chunk, total_chunks):
            if not self.is_running:
                self.log("Translation STOPPED by user.")
                break

            chunk_text = "\n\n".join(chunks[i])
            self.log(f"Translating Chunk {i + 1}/{total_chunks}...")

            wait_time = 20 # Start with 20 seconds wait for limits

            while True:
                if not self.is_running: break
                
                result = self.call_api(chunk_text, api_key, base_url, model)

                if result == "ERROR_429":
                    self.log(f"⚠️ Rate Limit Reached (429)! Anti-Limit triggered. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    wait_time += 15 # Exponential backoff (20s, 35s, 50s...)
                elif result.startswith("ERROR"):
                    self.log(f"❌ {result}")
                    self.log("Please check your API Key or Model name. Stopping...")
                    self.is_running = False
                    break
                else:
                    # Success - Save to file immediately
                    mode = 'w' if (i == 0 and start_chunk == 0) else 'a'
                    with open(self.output_file, mode, encoding='utf-8') as f:
                        f.write(result + "\n\n")
                    
                    self.log(f"✔ Chunk {i + 1} translated and saved.")
                    
                    # Normal delay between chunks to avoid hitting limits
                    if self.delay_var.get() and i < total_chunks - 1:
                        time.sleep(4) 
                    break

        if self.is_running:
            self.log("🎉 Translation Completed Successfully!")
            self.is_running = False

    def start_translation(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self.process_translation, daemon=True).start()

    def stop_translation(self):
        self.is_running = False
        self.log("Stopping after current chunk finishes...")

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleTranslatorApp(root)
    root.mainloop()
