import tkinter as tk
from tkinter import scrolledtext, filedialog, Menu, messagebox
from tkinter import ttk 
import re
import pyperclip
import threading
import time
import nltk
import json
import base64
import urllib.parse
from collections import Counter

# ===================================================================
# PART 0: VISUAL CONSTANTS
# ===================================================================
BG_DARK = "#1e1e1e"
BG_PANEL = "#252526"
BG_TEXT = "#3c3c3c"
FG_TEXT = "#cccccc"
ACCENT_COLOR = "#007acc"
ACCENT_HOVER = "#0098ff"
MODE_COLOR_WEB = "#e06c75"

FONT_MAIN = ("Segoe UI", 10)
FONT_HEADER = ("Segoe UI", 9, "bold")
FONT_MONO = ("Consolas", 10)

# ===================================================================
# PART 1: LOGIC FUNCTIONS
# ===================================================================
def final_text_formatter(text):
    citation_pattern = r'\[cite(?:_start|: [\d, ]+)\]'
    text = re.sub(citation_pattern, '', text)
    text = text.replace('**', '')
    text = text.replace('### ', '')
    return text

def summarize_text(text, num_sentences=3):
    try:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < num_sentences: return text
        return ' '.join(sentences[:num_sentences]) + "..."
    except: return "Summary failed."

def extract_keywords(text, num_keywords=5):
    try:
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = set(nltk.corpus.stopwords.words('english'))
        keywords = Counter(word for word in words if word not in stopwords)
        return ', '.join(word for word, count in keywords.most_common(num_keywords))
    except: return "Keywords failed."

def json_pretty(text):
    try: return json.dumps(json.loads(text), indent=4)
    except: return "Error: Invalid JSON"

def json_minify(text):
    try: return json.dumps(json.loads(text), separators=(',', ':'))
    except: return "Error: Invalid JSON"

def url_encode(text): return urllib.parse.quote(text)
def url_decode(text): return urllib.parse.unquote(text)

def b64_encode(text):
    try: return base64.b64encode(text.encode("utf-8")).decode("utf-8")
    except: return "Error: Encoding failed"

def b64_decode(text):
    try: return base64.b64decode(text.encode("utf-8")).decode("utf-8")
    except: return "Error: Invalid Base64"

def convert_to_html_simple(text):
    text = re.sub(r'^### (.*)', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text

# ===================================================================
# PART 2: MAIN APP
# ===================================================================

class TextToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text-Tool Pro v3.1 (Stable)")
        self.root.geometry("1100x900")
        self.root.configure(bg=BG_DARK)
        
        # State
        self.automate_clipboard = tk.BooleanVar()
        self.current_mode = tk.StringVar(value="Normal Mode")
        self.clipboard_thread = None
        self.is_monitoring = False
        self.last_clipboard_content = ""
        self.word_count_labels = {} 
        
        self.setup_styles()
        self.setup_nltk()
        self.create_menu()
        self.create_widgets()
        self.switch_mode("Normal Mode")

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=BG_DARK)
        self.style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT, font=FONT_MAIN)
        self.style.configure("Header.TLabel", background=BG_DARK, foreground=ACCENT_COLOR, font=FONT_HEADER)
        self.style.configure("TButton", background=BG_PANEL, foreground=FG_TEXT, borderwidth=0)
        self.style.map("TButton", background=[('active', "#444444")])
        self.style.configure("Accent.TButton", background=ACCENT_COLOR, foreground="white", font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", background=[('active', ACCENT_HOVER)])
        self.style.configure("Web.TButton", background="#2d2d2d", foreground="#e06c75", font=("Segoe UI", 9, "bold"))
        self.style.map("Web.TButton", background=[('active', "#3e3e3e")])

    def check_and_download_nltk_data(self):
        try: set(nltk.corpus.stopwords.words('english'))
        except LookupError: nltk.download('stopwords')

    def setup_nltk(self):
        threading.Thread(target=self.check_and_download_nltk_data, daemon=True).start()

    def create_menu(self):
        menubar = Menu(self.root, bg=BG_PANEL, fg=FG_TEXT, relief=tk.FLAT)
        self.root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0, bg=BG_PANEL, fg=FG_TEXT)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save Result", command=lambda: self.save_file(self.cleaned_text))
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. TOP BAR
        top_bar = tk.Frame(main_frame, bg=BG_PANEL, padx=10, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(top_bar, text="MODE:", background=BG_PANEL, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        mode_combo = ttk.Combobox(top_bar, textvariable=self.current_mode, values=["Normal Mode", "Web Helper Mode"], state="readonly", width=20)
        mode_combo.pack(side=tk.LEFT)
        mode_combo.bind("<<ComboboxSelected>>", lambda e: self.switch_mode(self.current_mode.get()))

        ttk.Checkbutton(top_bar, text="Auto-Clipboard", variable=self.automate_clipboard, command=self.toggle_clipboard_monitoring).pack(side=tk.LEFT, padx=20)
        self.action_btn = ttk.Button(top_bar, text="▶ CLEAN TEXT", command=self.process_manual_input, style="Accent.TButton", cursor="hand2")
        self.action_btn.pack(side=tk.RIGHT)

        # 2. INPUT AREA
        self.input_text, self.input_frame = self.create_text_area(main_frame, "INPUT", 8, "input")
        self.input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 3. OUTPUT AREA
        self.cleaned_text, self.output_frame = self.create_text_area(main_frame, "RESULT", 8, "output")
        self.output_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 4. DYNAMIC PANELS
        self.dynamic_frame = ttk.Frame(main_frame)
        self.dynamic_frame.pack(fill=tk.BOTH, expand=True)

        self.normal_tools_frame = ttk.Frame(self.dynamic_frame)
        self.summary_text, _ = self.create_text_area(self.normal_tools_frame, "SUMMARY", 4, "summary")
        self.keywords_text, _ = self.create_text_area(self.normal_tools_frame, "KEYWORDS", 3, "keywords")

        self.web_tools_frame = ttk.Frame(self.dynamic_frame)
        self.create_web_buttons(self.web_tools_frame)

        # 5. STATUS BAR
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 9), anchor="w", padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_web_buttons(self, parent):
        lbl = ttk.Label(parent, text="QUICK WEB ACTIONS", style="Header.TLabel", foreground=MODE_COLOR_WEB)
        lbl.pack(anchor="w", pady=(0, 10))
        grid_frame = ttk.Frame(parent)
        grid_frame.pack(fill=tk.X)
        ttk.Button(grid_frame, text="{ } JSON Format", style="Web.TButton", command=lambda: self.apply_tool(json_pretty)).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="{ } JSON Minify", style="Web.TButton", command=lambda: self.apply_tool(json_minify)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="URL Encode", style="Web.TButton", command=lambda: self.apply_tool(url_encode)).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="URL Decode", style="Web.TButton", command=lambda: self.apply_tool(url_decode)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="Base64 Encode", style="Web.TButton", command=lambda: self.apply_tool(b64_encode)).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="Base64 Decode", style="Web.TButton", command=lambda: self.apply_tool(b64_decode)).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(grid_frame, text="Markdown -> HTML", style="Web.TButton", command=self.export_html).grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

    def switch_mode(self, mode):
        if mode == "Normal Mode":
            self.web_tools_frame.pack_forget()
            self.normal_tools_frame.pack(fill=tk.BOTH, expand=True)
            self.action_btn.config(text="▶ CLEAN & SUMMARIZE")
            self.style.configure("Header.TLabel", foreground=ACCENT_COLOR)
            self.status_bar.config(bg=ACCENT_COLOR)
        elif mode == "Web Helper Mode":
            self.normal_tools_frame.pack_forget()
            self.web_tools_frame.pack(fill=tk.BOTH, expand=True)
            self.action_btn.config(text="▶ RUN CLEANER")
            self.style.configure("Header.TLabel", foreground=MODE_COLOR_WEB)
            self.status_bar.config(bg=MODE_COLOR_WEB)

    def create_text_area(self, parent, label_text, height, area_id):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=label_text, style="Header.TLabel").pack(side=tk.LEFT)
        self.word_count_labels[area_id] = ttk.Label(header, text="0 Words", font=("Segoe UI", 8), foreground="#777")
        self.word_count_labels[area_id].pack(side=tk.LEFT, padx=10)
        
        # --- FIXED: Create text_widget FIRST so we can reference it correctly in buttons
        text_widget = scrolledtext.ScrolledText(frame, height=height, wrap=tk.WORD, font=FONT_MONO, bg=BG_TEXT, fg=FG_TEXT, insertbackground="white", relief=tk.FLAT, padx=10, pady=10)
        
        btns = ttk.Frame(header)
        btns.pack(side=tk.RIGHT)
        # Directly use text_widget variable here
        ttk.Button(btns, text="Copy", command=lambda: self.copy_text(text_widget)).pack(side=tk.LEFT)
        ttk.Button(btns, text="Clear", command=lambda: self.clear_text(text_widget)).pack(side=tk.LEFT)

        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.bind('<KeyRelease>', lambda e: self.update_word_count(text_widget, area_id))
        return text_widget, frame

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.after(3000, lambda: self.status_var.set("Ready"))

    def update_word_count(self, text_widget, area_id):
        content = text_widget.get(1.0, tk.END)
        words = re.findall(r'\b\w+\b', content)
        self.word_count_labels[area_id].config(text=f"{len(words)} Words")

    def apply_tool(self, tool_function):
        content = self.input_text.get(1.0, tk.END).strip()
        if not content: return
        result = tool_function(content)
        self.cleaned_text.delete(1.0, tk.END)
        self.cleaned_text.insert(tk.END, result)
        self.update_word_count(self.cleaned_text, "output")
        self.set_status(f"Applied: {tool_function.__name__}")

    def process_manual_input(self):
        text = self.input_text.get(1.0, tk.END)
        formatted = final_text_formatter(text)
        
        self.cleaned_text.delete(1.0, tk.END)
        self.cleaned_text.insert(tk.END, formatted)
        self.update_word_count(self.cleaned_text, "output")
        
        if self.current_mode.get() == "Normal Mode":
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(tk.END, summarize_text(formatted))
            self.update_word_count(self.summary_text, "summary")
            
            self.keywords_text.delete(1.0, tk.END)
            self.keywords_text.insert(tk.END, extract_keywords(formatted))
            self.update_word_count(self.keywords_text, "keywords")
        
        self.set_status("Processed Input")

    def copy_text(self, widget): 
        try:
            pyperclip.copy(widget.get(1.0, tk.END).strip())
            self.set_status("Copied to Clipboard!")
        except Exception as e:
            self.set_status("Error: Install xclip (sudo pacman -S xclip)")

    def clear_text(self, widget): 
        widget.delete(1.0, tk.END)
        # Find which widget this is to update the correct label
        if widget == self.input_text: self.update_word_count(widget, "input")
        elif widget == self.cleaned_text: self.update_word_count(widget, "output")
        # (Other widgets update automatically on process)

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.input_text.insert(tk.END, f.read())
                self.update_word_count(self.input_text, "input")

    def save_file(self, text_widget):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_widget.get(1.0, tk.END).strip())

    def export_html(self): self.apply_tool(convert_to_html_simple)

    def toggle_clipboard_monitoring(self):
        if self.automate_clipboard.get():
            self.is_monitoring = True
            if self.clipboard_thread is None or not self.clipboard_thread.is_alive():
                self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
                self.clipboard_thread.start()
        else: self.is_monitoring = False

    def monitor_clipboard(self):
        self.last_clipboard_content = pyperclip.paste()
        while self.is_monitoring:
            try:
                curr = pyperclip.paste()
                if curr != self.last_clipboard_content:
                    self.last_clipboard_content = curr
                    self.input_text.delete(1.0, tk.END)
                    self.input_text.insert(tk.END, curr)
                    self.root.after(0, self.process_manual_input) # Safe GUI update
                    self.root.after(0, lambda: self.update_word_count(self.input_text, "input"))
            except Exception:
                # If clipboard fails (no xclip), stop monitoring to prevent spamming errors
                self.is_monitoring = False
                self.root.after(0, lambda: self.set_status("Clipboard Error: Install xclip!"))
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TextToolApp(root)
    root.mainloop()