import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import requests
import json
import time
import threading
import os
import re

class SubtitleStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Professional Subtitle Studio - Ultimate Edition")
        self.root.geometry("850x750")
        self.root.configure(bg="#1e2124")

        self.is_running = False
        self.srt_blocks =[]
        self.output_file = ""

        # Style for Tabs
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook.Tab', padding=[20, 5], font=('Arial', 10, 'bold'))
        style.configure('TNotebook', background='#1e2124')
        style.configure('TFrame', background='#1e2124')

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_translator = ttk.Frame(self.notebook)
        self.tab_chat = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_translator, text="🎬 Subtitle Translator")
        self.notebook.add(self.tab_chat, text="💬 Test Chat / Prompt")

        self.setup_translator_ui()
        self.setup_chat_ui()

    def setup_translator_ui(self):
        # --- API Key Pool Section ---
        tk.Label(self.tab_translator, text="API Key Pool (Paste multiple keys, one per line):", bg="#1e2124", fg="white", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        self.api_key_text = tk.Text(self.tab_translator, height=4, width=80, bg="#2c2f33", fg="white", insertbackground="white", font=("Consolas", 9))
        self.api_key_text.pack(pady=5)
        self.api_key_text.bind("<KeyRelease>", self.auto_detect_api)

        self.detect_label = tk.Label(self.tab_translator, text="Waiting for API Keys...", bg="#1e2124", fg="#f1c40f", font=("Arial", 10, "bold"))
        self.detect_label.pack(pady=2)

        # --- URL, Model & Branding Section ---
        frame_settings = tk.Frame(self.tab_translator, bg="#2c2f33", padx=15, pady=10)
        frame_settings.pack(pady=5, fill="x", padx=20)

        tk.Label(frame_settings, text="Base URL:", bg="#2c2f33", fg="white").grid(row=0, column=0, sticky="w", pady=2)
        self.base_url_entry = tk.Entry(frame_settings, width=50, bg="#1e2124", fg="white", insertbackground="white")
        self.base_url_entry.grid(row=0, column=1, pady=2, padx=10)

        tk.Label(frame_settings, text="Model Name:", bg="#2c2f33", fg="white").grid(row=1, column=0, sticky="w", pady=2)
        self.model_entry = tk.Entry(frame_settings, width=50, bg="#1e2124", fg="white", insertbackground="white")
        self.model_entry.grid(row=1, column=1, pady=2, padx=10)

        tk.Label(frame_settings, text="Auto Branding:", bg="#2c2f33", fg="#3498db", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        self.branding_entry = tk.Entry(frame_settings, width=50, bg="#1e2124", fg="#3498db", insertbackground="white")
        self.branding_entry.insert(0, "www.yoursite.com")
        self.branding_entry.grid(row=2, column=1, pady=2, padx=10)

        # --- File Selection ---
        self.btn_select = tk.Button(self.tab_translator, text="📁 Select English SRT File", bg="#1abc9c", fg="white", font=("Arial", 11, "bold"), command=self.select_file, cursor="hand2")
        self.btn_select.pack(pady=10)
        self.file_label = tk.Label(self.tab_translator, text="No file selected", bg="#1e2124", fg="#bdc3c7")
        self.file_label.pack()

        # --- Chunk & Delay Settings ---
        frame_controls = tk.Frame(self.tab_translator, bg="#1e2124")
        frame_controls.pack(pady=5)

        tk.Label(frame_controls, text="Chunk Size:", bg="#1e2124", fg="white").grid(row=0, column=0, padx=5)
        self.chunk_size_var = tk.StringVar(value="15") # Changed default to 15
        tk.Entry(frame_controls, textvariable=self.chunk_size_var, width=5, justify="center").grid(row=0, column=1, padx=5)

        tk.Label(frame_controls, text="Start from Chunk:", bg="#1e2124", fg="#e67e22").grid(row=0, column=2, padx=5)
        self.start_chunk_var = tk.StringVar(value="1")
        tk.Entry(frame_controls, textvariable=self.start_chunk_var, width=5, bg="#e67e22", fg="white", justify="center", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)

        # --- Log Console ---
        self.console = scrolledtext.ScrolledText(self.tab_translator, width=90, height=10, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.console.pack(pady=10, padx=20)

        # --- Buttons ---
        frame_btns = tk.Frame(self.tab_translator, bg="#1e2124")
        frame_btns.pack(pady=5)

        self.btn_start = tk.Button(frame_btns, text="▶ START", width=12, bg="#3498db", fg="white", font=("Arial", 11, "bold"), command=self.start_translation, cursor="hand2")
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = tk.Button(frame_btns, text="⏹ STOP", width=12, bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), command=self.stop_translation, cursor="hand2")
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.btn_reset = tk.Button(frame_btns, text="🔄 RESET", width=12, bg="#95a5a6", fg="white", font=("Arial", 11, "bold"), command=self.reset_all, cursor="hand2")
        self.btn_reset.grid(row=0, column=2, padx=10)

    def setup_chat_ui(self):
        tk.Label(self.tab_chat, text="Test your API Key and Prompt before translating a full movie.", bg="#1e2124", fg="white", font=("Arial", 10)).pack(pady=10)
        
        self.chat_console = scrolledtext.ScrolledText(self.tab_chat, width=90, height=20, bg="#2c2f33", fg="white", font=("Consolas", 10))
        self.chat_console.pack(pady=10, padx=20)
        
        frame_chat_input = tk.Frame(self.tab_chat, bg="#1e2124")
        frame_chat_input.pack(fill="x", padx=20, pady=10)
        
        self.chat_entry = tk.Entry(frame_chat_input, width=75, bg="#1e2124", fg="white", insertbackground="white", font=("Arial", 11))
        self.chat_entry.grid(row=0, column=0, padx=5)
        self.chat_entry.bind("<Return>", lambda event: self.send_chat())
        
        self.btn_send = tk.Button(frame_chat_input, text="Send", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), command=self.send_chat)
        self.btn_send.grid(row=0, column=1, padx=5)

    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def reset_all(self):
        self.api_key_text.delete("1.0", tk.END)
        self.base_url_entry.delete(0, tk.END)
        self.model_entry.delete(0, tk.END)
        self.branding_entry.delete(0, tk.END)
        self.branding_entry.insert(0, "www.yoursite.com")
        self.file_label.config(text="No file selected")
        self.srt_blocks =[]
        self.output_file = ""
        self.chunk_size_var.set("15")
        self.start_chunk_var.set("1")
        self.console.delete("1.0", tk.END)
        self.chat_console.delete("1.0", tk.END)
        self.detect_label.config(text="Waiting for API Keys...", fg="#f1c40f")
        self.log("System Reset Successful.")

    def get_keys(self):
        keys = self.api_key_text.get("1.0", tk.END).split("\n")
        return [k.strip() for k in keys if k.strip()]

    def auto_detect_api(self, event=None):
        keys = self.get_keys()
        if not keys:
            self.detect_label.config(text="Waiting for API Keys...", fg="#f1c40f")
            return
            
        key = keys[0] # Detect based on the first key
        
        if key.lower() == "ollama":
            self.detect_label.config(text="✔ Detected: Ollama (Localhost)", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "http://localhost:11434/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "llama3")
        elif key.startswith("sk-or"):
            self.detect_label.config(text="✔ Detected: OpenRouter", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://openrouter.ai/api/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "qwen/qwen-2.5-72b-instruct:free")
        elif key.startswith("gsk_"):
            self.detect_label.config(text="✔ Detected: Groq", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://api.groq.com/openai/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "llama-3.3-70b-versatile")
        elif key.startswith("hf_"):
            self.detect_label.config(text="✔ Detected: Hugging Face", fg="#9b59b6")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://api-inference.huggingface.co/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "meta-llama/Meta-Llama-3-8B-Instruct")
        elif key.startswith("nvapi-"):
            self.detect_label.config(text="✔ Detected: NVIDIA", fg="#2ecc71")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://integrate.api.nvidia.com/v1")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "meta/llama3-70b-instruct")
        elif key.startswith("ghp_") or key.startswith("github_pat_"):
            self.detect_label.config(text="✔ Detected: GitHub Models", fg="#ffffff")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://models.inference.ai.azure.com")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "Meta-Llama-3-8B-Instruct")
        elif len(key) == 39 and not key.startswith("sk-"): 
            self.detect_label.config(text="✔ Detected: Google AI Studio (Gemini)", fg="#3498db")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://generativelanguage.googleapis.com/v1beta")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "gemini-3-flash-preview")
        elif key.startswith("sk-"):
            self.detect_label.config(text="✔ Detected: DeepSeek / Together AI / OpenAI", fg="#e67e22")
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, "https://api.deepseek.com")
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, "deepseek-chat")

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("SRT Files", "*.srt")])
        if file_path:
            self.file_label.config(text=os.path.basename(file_path))
            self.output_file = file_path.replace(".srt", "_translated.srt")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.srt_blocks =[block.strip() for block in content.split("\n\n") if block.strip()]
                self.log(f"Loaded {len(self.srt_blocks)} subtitle blocks successfully.")
            except Exception as e:
                self.log(f"Error reading file: {e}")

    def call_api(self, text_chunk, api_key, base_url, model):
        # Ultimate Prompt for Conversational Sinhala & Transliteration
        system_prompt = """You are a professional movie subtitle translator. Translate the following English SRT subtitle chunk into natural, conversational, and spoken Sinhala (කතා කරන සිංහල). 
RULES:
1. DO NOT use formal or literary Sinhala. Use everyday spoken language.
2. TRANSLITERATE English names, places, and specific terms into Sinhala script (e.g., 'Army Rangers' -> 'ආමි රේන්ජර්ස්', 'FBI' -> 'එෆ්.බී.අයි'). DO NOT leave any English A-Z letters in the output.
3. STRICTLY maintain the original SRT formatting. Keep the exact sequence numbers and timestamps.
4. Return exactly the same number of subtitle blocks as the input.
5. Output ONLY the translated SRT blocks. No markdown, no extra text."""
        
        headers = {"Content-Type": "application/json"}
        
        try:
            if "generativelanguage.googleapis.com" in base_url:
                url = f"{base_url}/models/{model}:generateContent?key={api_key}"
                payload = {
                    "system_instruction": {"parts":[{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": text_chunk}]}],
                    "generationConfig": {"temperature": 0.4}
                }
            else:
                url = f"{base_url}/chat/completions"
                if api_key.lower() != "ollama":
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
                
                return result.replace("```srt", "").replace("```", "").strip()
                
            elif response.status_code == 429:
                return "ERROR_429"
            else:
                return f"ERROR: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"ERROR: {str(e)}"

    def format_fixer(self, original_chunk, translated_chunk, is_first, is_last, branding):
        # This fixes missing/corrupted timestamps and adds branding
        orig_blocks = original_chunk.strip().split('\n\n')
        trans_blocks = translated_chunk.strip().split('\n\n')
        
        fixed_blocks =[]
        
        # If AI returned the exact number of blocks, we enforce the original timestamps
        if len(orig_blocks) == len(trans_blocks):
            for i, (ob, tb) in enumerate(zip(orig_blocks, trans_blocks)):
                ob_lines = ob.split('\n')
                tb_lines = tb.split('\n')
                
                if len(ob_lines) >= 2:
                    index = ob_lines[0]
                    timestamp = ob_lines[1]
                    
                    # Extract text from translated block safely
                    tb_text = re.sub(r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*\n', '', tb + '\n', flags=re.MULTILINE).strip()
                    if not tb_text: tb_text = tb # Fallback
                    
                    # Add Branding
                    if is_first and i == 0 and branding:
                        tb_text = f"<font color='#f1c40f'>සිංහල උපසිරැසි: {branding}</font>\n" + tb_text
                    if is_last and i == len(orig_blocks) - 1 and branding:
                        tb_text = tb_text + f"\n<font color='#f1c40f'>සිංහල උපසිරැසි: {branding}</font>"
                        
                    fixed_blocks.append(f"{index}\n{timestamp}\n{tb_text}")
                else:
                    fixed_blocks.append(tb)
            return '\n\n'.join(fixed_blocks)
        else:
            # If AI messed up block count, return as is (but try to add branding)
            if is_first and branding: trans_blocks[0] = f"<font color='#f1c40f'>සිංහල උපසිරැසි: {branding}</font>\n" + trans_blocks[0]
            if is_last and branding: trans_blocks[-1] = trans_blocks[-1] + f"\n<font color='#f1c40f'>සිංහල උපසිරැසි: {branding}</font>"
            return '\n\n'.join(trans_blocks)

    def process_translation(self):
        keys = self.get_keys()
        base_url = self.base_url_entry.get().strip()
        model = self.model_entry.get().strip()
        branding = self.branding_entry.get().strip()
        
        if not self.srt_blocks:
            self.log("Error: Please select an SRT file first.")
            self.is_running = False
            return
        if not keys:
            self.log("Error: Please enter at least one API Key.")
            self.is_running = False
            return

        try:
            chunk_size = int(self.chunk_size_var.get())
            start_chunk = int(self.start_chunk_var.get()) - 1
        except ValueError:
            self.log("Error: Chunk size and Start chunk must be numbers.")
            self.is_running = False
            return

        chunks = [self.srt_blocks[i:i + chunk_size] for i in range(0, len(self.srt_blocks), chunk_size)]
        total_chunks = len(chunks)

        self.log(f"Starting translation... Total Chunks: {total_chunks}")
        self.log(f"Loaded {len(keys)} API Keys in the pool.")

        current_key_idx = 0

        for i in range(start_chunk, total_chunks):
            if not self.is_running: break

            chunk_text = "\n\n".join(chunks[i])
            self.log(f"Translating Chunk {i + 1}/{total_chunks}...")

            while True:
                if not self.is_running: break
                
                active_key = keys[current_key_idx]
                result = self.call_api(chunk_text, active_key, base_url, model)

                if result == "ERROR_429":
                    current_key_idx += 1
                    if current_key_idx >= len(keys):
                        self.log("⚠️ All API Keys hit Rate Limit! Smart Delay triggered. Waiting 65 seconds...")
                        time.sleep(65)
                        current_key_idx = 0 # Reset to first key
                    else:
                        self.log(f"🔄 Limit reached. Auto-switching to API Key {current_key_idx + 1}...")
                elif result.startswith("ERROR"):
                    self.log(f"❌ {result}")
                    self.is_running = False
                    break
                else:
                    # Success
                    is_first = (i == 0)
                    is_last = (i == total_chunks - 1)
                    
                    # Apply Format Fixer and Branding
                    final_text = self.format_fixer(chunk_text, result, is_first, is_last, branding)
                    
                    mode = 'w' if (i == 0 and start_chunk == 0) else 'a'
                    with open(self.output_file, mode, encoding='utf-8') as f:
                        f.write(final_text + "\n\n")
                    
                    self.log(f"✔ Chunk {i + 1} translated and saved.")
                    time.sleep(2) # Small delay to prevent spamming
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

    def send_chat(self):
        user_text = self.chat_entry.get().strip()
        if not user_text: return
        
        keys = self.get_keys()
        base_url = self.base_url_entry.get().strip()
        model = self.model_entry.get().strip()
        
        if not keys:
            messagebox.showerror("Error", "Please enter an API Key in the Translator tab first.")
            return

        self.chat_console.insert(tk.END, f"You: {user_text}\n", "user")
        self.chat_entry.delete(0, tk.END)
        self.chat_console.insert(tk.END, "AI is typing...\n")
        self.chat_console.see(tk.END)

        def fetch_chat():
            result = self.call_api(user_text, keys[0], base_url, model)
            self.chat_console.delete("end-2l", "end-1l") # Remove "typing..."
            if result.startswith("ERROR"):
                self.chat_console.insert(tk.END, f"System: {result}\n\n")
            else:
                self.chat_console.insert(tk.END, f"AI: {result}\n\n")
            self.chat_console.see(tk.END)

        threading.Thread(target=fetch_chat, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleStudioApp(root)
    root.mainloop()
