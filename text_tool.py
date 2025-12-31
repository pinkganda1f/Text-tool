import tkinter as tk
from tkinter import scrolledtext, Checkbutton, Button, BooleanVar, Frame, Label, messagebox, filedialog
import re
import pyperclip
import threading
import time
import nltk
from collections import Counter
from heapq import nlargest

# ===================================================================
# PART 1: FUNCTIONS
# ===================================================================

def final_text_formatter(text):
    """
    Applies all text cleaning and formatting in one pass.
    """
    citation_pattern = r'\[cite(?:_start|: [\d, ]+)\]'
    text = re.sub(citation_pattern, '', text)
    text = text.replace('**', '')
    text = text.replace('### ', '')

    lines = text.strip().split('\n')
    processed_lines = []
    level_1_counter = 0

    for line in lines:
        stripped_line = line.strip()
        indentation = len(line) - len(line.lstrip(' '))
        
        if stripped_line.startswith('* '):
            if indentation < 8:
                level_1_counter += 1
                new_line = f"    {chr(96 + level_1_counter)}. {stripped_line[2:]}"
                processed_lines.append(new_line)
            else:
                new_line = f"        - {stripped_line[2:]}"
                processed_lines.append(new_line)
        else:
            level_1_counter = 0
            processed_lines.append(line)
            
    final_text = '\n'.join(processed_lines)
    return final_text

def convert_to_html_simple(text):
    """
    Converts basic Markdown to HTML for Web Dev usage.
    """
    # Convert Headers (### Title -> <h3>Title</h3>)
    text = re.sub(r'^### (.*)', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*)', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # Convert Bold (**text** -> <b>text</b>)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # Convert Lists
    lines = text.split('\n')
    in_list = False
    new_lines = []
    
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                new_lines.append("<ul>")
                in_list = True
            content = line.strip()[2:]
            new_lines.append(f"  <li>{content}</li>")
        else:
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(line)
            
    if in_list: new_lines.append("</ul>")
    
    return "<br>\n".join(new_lines)

def summarize_text(text, num_sentences=3):
    try:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < num_sentences: return text
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = set(nltk.corpus.stopwords.words('english'))
        word_frequencies = Counter(word for word in words if word not in stopwords)
        sentence_scores = {}
        for sentence in sentences:
            sentence_words = re.findall(r'\b\w+\b', sentence.lower())
            score = sum(word_frequencies[word] for word in sentence_words if word in word_frequencies)
            sentence_scores[sentence] = score
        summary_sentences = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)
        return ' '.join(summary_sentences)
    except Exception:
        return "Could not generate summary."

def extract_keywords(text, num_keywords=5):
    try:
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = set(nltk.corpus.stopwords.words('english'))
        keywords = Counter(word for word in words if word not in stopwords)
        return ', '.join(word for word, count in keywords.most_common(num_keywords))
    except Exception:
        return "Could not extract keywords."

# ===================================================================
# PART 2: MAIN CLASS
# ===================================================================

class TextToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text-Tool Pro (Web Dev Edition)")
        self.root.geometry("900x750")
        self.automate_clipboard = BooleanVar()
        self.generate_summary = BooleanVar()
        self.extract_keywords = BooleanVar()
        self.clipboard_thread = None
        self.is_monitoring = False
        self.last_clipboard_content = ""
        self.setup_nltk()
        self.create_widgets()
        
    def check_and_download_nltk_data(self):
        try:
            set(nltk.corpus.stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords')
            
    def setup_nltk(self):
        nltk_thread = threading.Thread(target=self.check_and_download_nltk_data, daemon=True)
        nltk_thread.start()
        
    def copy_text(self, text_widget):
        pyperclip.copy(text_widget.get(1.0, tk.END).strip())
        
    def clear_text(self, text_widget):
        text_widget.delete(1.0, tk.END)

    # --- NEW FUNCTIONALITY: SAVE & CONVERT ---
    def save_file(self, text_widget, default_ext=".txt"):
        content = text_widget.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "Nothing to save!")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("Text Files", "*.txt"), ("HTML Files", "*.html"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def export_html(self):
        raw_text = self.cleaned_text.get(1.0, tk.END)
        html_content = convert_to_html_simple(raw_text)
        self.clear_text(self.cleaned_text)
        self.cleaned_text.insert(tk.END, html_content)
        messagebox.showinfo("Converted", "Text converted to HTML! Click 'Save' to save as .html")

    # --- UI CREATION ---
    def create_widgets(self):
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = Frame(main_frame, relief=tk.RIDGE, borderwidth=2, padx=5, pady=5)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        Label(control_frame, text="Settings:", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        Checkbutton(control_frame, text="Automate Clipboard", variable=self.automate_clipboard, command=self.toggle_clipboard_monitoring).pack(side=tk.LEFT)
        Checkbutton(control_frame, text="Generate Summary", variable=self.generate_summary).pack(side=tk.LEFT)
        Checkbutton(control_frame, text="Extract Keywords", variable=self.extract_keywords).pack(side=tk.LEFT)
        
        # New "To HTML" Button
        Button(control_frame, text="to HTML", command=self.export_html, bg="#ffcccb").pack(side=tk.LEFT, padx=15)
        
        Button(control_frame, text="Process Manually", command=self.process_manual_input, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.input_text = self.create_text_area(main_frame, "Input Text", 10)
        self.cleaned_text = self.create_text_area(main_frame, "Cleaned Text", 7)
        self.summary_text = self.create_text_area(main_frame, "Summary", 4)
        self.keywords_text = self.create_text_area(main_frame, "Keywords", 2)

    def create_text_area(self, parent, label_text, height):
        frame = Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        label_frame = Frame(frame)
        label_frame.pack(fill=tk.X)
        
        Label(label_frame, text=label_text, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        
        button_frame = Frame(label_frame)
        button_frame.pack(side=tk.RIGHT)
        
        text_widget = scrolledtext.ScrolledText(frame, height=height, wrap=tk.WORD, padx=5, pady=5, relief=tk.SOLID, borderwidth=1)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Standard Buttons
        Button(button_frame, text="Copy", command=lambda: self.copy_text(text_widget)).pack(side=tk.LEFT, padx=(0,5))
        # New Save Button
        Button(button_frame, text="Save", command=lambda: self.save_file(text_widget)).pack(side=tk.LEFT, padx=(0,5))
        Button(button_frame, text="Clear", command=lambda: self.clear_text(text_widget)).pack(side=tk.LEFT)
        
        return text_widget
        
    def process_text(self, text):
        formatted_text = final_text_formatter(text)
        
        self.clear_text(self.cleaned_text)
        self.cleaned_text.insert(tk.END, formatted_text)

        self.clear_text(self.summary_text)
        if self.generate_summary.get():
            summary = summarize_text(formatted_text)
            self.summary_text.insert(tk.END, summary)

        self.clear_text(self.keywords_text)
        if self.extract_keywords.get():
            keywords = extract_keywords(formatted_text)
            self.keywords_text.insert(tk.END, keywords)
    
    def process_manual_input(self):
        input_content = self.input_text.get(1.0, tk.END)
        self.process_text(input_content)
        
    def toggle_clipboard_monitoring(self):
        if self.automate_clipboard.get():
            self.is_monitoring = True
            if self.clipboard_thread is None or not self.clipboard_thread.is_alive():
                self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
                self.clipboard_thread.start()
        else:
            self.is_monitoring = False
            
    def monitor_clipboard(self):
        self.last_clipboard_content = pyperclip.paste()
        while self.is_monitoring:
            try:
                current_content = pyperclip.paste()
                # CHANGED: Removed "and ('[cite:' in current_content)"
                if current_content != self.last_clipboard_content:
                    self.last_clipboard_content = current_content
                    
                    # Update the GUI safely from the thread
                    self.input_text.delete(1.0, tk.END)
                    self.input_text.insert(tk.END, current_content)
                    self.process_text(current_content)
            except Exception as e:
                print(f"Clipboard error: {e}")
            time.sleep(1)

# ===================================================================
# PART 3: RUNS APP
# ===================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = TextToolApp(root)
    root.mainloop()