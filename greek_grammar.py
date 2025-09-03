import tkinter as tk
from tkinter import ttk, messagebox, font
import json
import unicodedata
import sys

# Unicode combining characters for Greek diacritics
SMOOTH_BREATHING = '\u0313'  # ᾿
ROUGH_BREATHING = '\u0314'   # ῾
IOTA_SUBSCRIPT = '\u0345'    # ͅ (combines with α, η, ω)

class FontManager:
    """Manage fonts for the application"""
    def __init__(self):
        self.default_font = ('Times New Roman', 12)

    def get_default_font(self):
        return self.default_font

    def set_default_font(self, font_tuple):
        self.default_font = font_tuple

class GreekGrammarApp:
    """Provides an interactive interface for practicing Greek declensions."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ancient Greek Grammar Study")
        
        # Initialize state variables
        self.pending_diacritic = None
        self.table_frame = None
        self.entries = {}
        self.error_labels = {}
        
        # Set up proper Unicode handling for Greek characters
        if sys.platform.startswith('win'):
            try:
                import locale
                locale.setlocale(locale.LC_ALL, 'Greek_Greece.UTF-8')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, 'el_GR.UTF-8')
                except locale.Error:
                    print("Warning: Greek locale not available. Unicode support may be limited.")
        
        # Setup fonts
        self.greek_font = ('Times New Roman', 12)
        self.normal_font = font.Font(family=self.greek_font[0], size=self.greek_font[1])
        self.bold_font = font.Font(family=self.greek_font[0], size=self.greek_font[1], weight='bold')
        
        # Configure styles for better appearance
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 24, 'bold'), padding=(0, 10))
        
        # Configure root window
        self.root.configure(padx=20, pady=20)
        self.root.geometry("900x700")  # Set appropriate window size
        
        # Main container 
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0)  # Title row
        self.main_frame.grid_rowconfigure(1, weight=0)  # Mode row
        self.main_frame.grid_rowconfigure(2, weight=0)  # Word row
        self.main_frame.grid_rowconfigure(3, weight=1)  # Table row - expandable
        self.main_frame.grid_rowconfigure(4, weight=0)  # Button row
        for i in range(3):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Title and Instructions
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        title_frame.grid_columnconfigure(0, weight=1)  # Allow title to expand
        title_frame.grid_columnconfigure(3, weight=0)  # Keep help button fixed
        
        title_label = ttk.Label(
            title_frame, 
            text="Ancient Greek Grammar Study",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, columnspan=3)
        
        # Help button in top right corner
        help_button = ttk.Button(
            title_frame,
            text="Help",
            command=self.show_help,
            width=10
        )
        help_button.grid(row=0, column=3, sticky='ne', padx=(20, 0))

        # Load paradigms
        try:
            with open('paradigms.json', 'r', encoding='utf-8') as f:
                self.paradigms = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "Could not find paradigms.json file")
            root.destroy()
            return
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Could not parse paradigms.json file")
            root.destroy()
            return

        # Create the mode selection frame
        mode_frame = ttk.Frame(self.main_frame)
        mode_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        mode_frame.columnconfigure(1, weight=1)

        ttk.Label(mode_frame, text="Select Study Mode:").grid(
            row=0, column=0, padx=(0, 10)
        )

        # Setup mode selector
        self.mode_var = tk.StringVar(value="First Declension (μουσα)")
        self.modes = [
            "Article (ὁ, ἡ, το)",
            "First Declension (μουσα)",
            "First Declension -η (τιμη)",
            "First Declension Long α (χωρα)",
            "First Declension Masculine (ναύτης)",
            "Second Declension (λογος)",
            "Second Declension Neuter (δωρον)",
            "Third Declension Guard (φύλαξ)",
            "Third Declension Body (σῶμα)",
            "Third Declension Old Man (γέρων)",
            "Third Declension Man (ἀνήρ)",
            "Third Declension Father (πατήρ)",
            "Third Declension Hope (ἐλπίς)",
            "Third Declension Orator (ῥήτωρ)",
            "Third Declension Woman (γυνή)",
            "Third Declension City (πόλις)"
        ]

        # Setup mode selector with clean styling
        mode_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=self.modes,
            font=('Times New Roman', 12),
            width=40
        )
        mode_dropdown.grid(row=0, column=1, sticky='ew', padx=10)
        mode_dropdown.state(['readonly'])
        mode_dropdown.bind('<<ComboboxSelected>>', self.on_mode_change)

        # Word display frame - simplified to remove white patches
        word_frame = ttk.Frame(self.main_frame)
        word_frame.grid(row=2, column=0, columnspan=3, pady=(10, 20))
        
        ttk.Label(
            word_frame,
            text="Decline the word:",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, padx=(0, 10))
        
        self.word_label = ttk.Label(
            word_frame,
            text="—",
            font=('Times New Roman', 16, 'bold'),
            foreground='#2c3e50'
        )
        self.word_label.grid(row=0, column=1)

        # Create declension table
        self.create_declension_table()
        
        # Update word display after creating table
        self.update_word_display()

    def update_word_display(self):
        """Update the word display with the current paradigm."""
        mode = self.mode_var.get()
        # Extract the word from the mode description
        if "μουσα" in mode:
            word = "μούσα"
        elif "τιμη" in mode:
            word = "τιμή"
        elif "χωρα" in mode:
            word = "χώρα"
        elif "ναύτης" in mode:
            word = "ναύτης"
        elif "λογος" in mode:
            word = "λόγος"
        elif "δωρον" in mode:
            word = "δῶρον"
        elif "φύλαξ" in mode:
            word = "φύλαξ"
        elif "σῶμα" in mode:
            word = "σῶμα"
        elif "γέρων" in mode:
            word = "γέρων"
        elif "ἀνήρ" in mode:
            word = "ἀνήρ"
        elif "πατήρ" in mode:
            word = "πατήρ"
        elif "ἐλπίς" in mode:
            word = "ἐλπίς"
        elif "ῥήτωρ" in mode:
            word = "ῥήτωρ"
        elif "γυνή" in mode:
            word = "γυνή"
        elif "πόλις" in mode:
            word = "πόλις"
        elif "ὁ, ἡ, το" in mode:
            word = "ὁ, ἡ, τό"
        else:
            word = "—"
        
        self.word_label.config(text=word)

    def create_declension_table(self):
        """Create the declension table with input fields for each case."""
        if self.table_frame:
            self.table_frame.destroy()
            
        self.table_frame = ttk.Frame(self.main_frame)
        self.table_frame.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(20, 10))
        
        # Configure grid weights for better expansion
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(1, weight=2)
        self.table_frame.grid_columnconfigure(2, weight=2)

        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return

        # Headers with better styling
        ttk.Label(
            self.table_frame,
            text="",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=0, padx=15, pady=15, sticky='e')
        ttk.Label(
            self.table_frame,
            text="Singular",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=1, padx=15, pady=15)
        ttk.Label(
            self.table_frame,
            text="Plural",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=2, padx=15, pady=15)

        # Create input fields for each case with better spacing
        cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
        for i, case in enumerate(cases, 1):
            # Case label with better styling
            ttk.Label(
                self.table_frame,
                text=case,
                font=('Arial', 12, 'bold')
            ).grid(row=i, column=0, padx=15, pady=10, sticky=tk.E)

            # Singular entry - larger and better styled
            entry_sg = tk.Entry(
                self.table_frame,
                width=25,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_sg.grid(row=i, column=1, padx=15, pady=10, sticky='ew')
            self.entries[f"{case}_sg"] = entry_sg
            entry_sg.bind('<Key>', self.handle_key_press)
            
            # Bind additional key events for Enter, arrows, etc.
            entry_sg.bind('<KeyRelease>', lambda e, c=case, s='sg': self.clear_error(f"{c}_{s}"))
            entry_sg.bind('<Return>', lambda e, c=case, s='sg': self.handle_enter(e, f"{c}_{s}"))
            entry_sg.bind('<Up>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'up'))
            entry_sg.bind('<Down>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'down'))

            # Error label for singular
            error_label_sg = ttk.Label(
                self.table_frame,
                text="❌",
                foreground='red'
            )
            error_label_sg.grid(row=i, column=1, sticky='e', padx=15)
            self.error_labels[f"{case}_sg"] = error_label_sg
            error_label_sg.grid_remove()

            # Plural entry - larger and better styled
            entry_pl = tk.Entry(
                self.table_frame,
                width=25,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_pl.grid(row=i, column=2, padx=15, pady=10, sticky='ew')
            self.entries[f"{case}_pl"] = entry_pl
            entry_pl.bind('<Key>', self.handle_key_press)
            
            # Bind additional key events for Enter, arrows, etc.
            entry_pl.bind('<KeyRelease>', lambda e, c=case, s='pl': self.clear_error(f"{c}_{s}"))
            entry_pl.bind('<Return>', lambda e, c=case, s='pl': self.handle_enter(e, f"{c}_{s}"))
            entry_pl.bind('<Up>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'up'))
            entry_pl.bind('<Down>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'down'))

            # Error label for plural
            error_label_pl = ttk.Label(
                self.table_frame,
                text="❌",
                foreground='red'
            )
            error_label_pl.grid(row=i, column=2, sticky='e', padx=15)
            self.error_labels[f"{case}_pl"] = error_label_pl
            error_label_pl.grid_remove()
        
        # Bottom button frame positioned after table
        bottom_button_frame = ttk.Frame(self.main_frame)
        bottom_button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Style for buttons
        button_style = ttk.Style()
        button_style.configure('Large.TButton',
                             font=('Arial', 12),
                             padding=(15, 8))
        
        # Check answers button
        check_button = ttk.Button(
            bottom_button_frame,
            text="Check Answers",
            command=self.check_answers,
            style='Large.TButton',
            width=15
        )
        check_button.grid(row=0, column=0, padx=20)
        
        # Reveal answers button
        reveal_button = ttk.Button(
            bottom_button_frame,
            text="Reveal Answers",
            command=self.reveal_answers,
            style='Large.TButton',
            width=15
        )
        reveal_button.grid(row=0, column=1, padx=20)
        
        # Reset button
        reset_button = ttk.Button(
            bottom_button_frame,
            text="Reset",
            command=self.reset_table,
            style='Large.TButton',
            width=15
        )
        reset_button.grid(row=0, column=2, padx=20)

    def handle_key_press(self, event):
        """Handle special character input."""
        char = event.char
        entry = event.widget
        
        # Handle special diacritic keys
        if char in ['[', ']', '{']:
            print(f"Diacritic key detected: {char}")
            cursor_pos = entry.index(tk.INSERT)
            
            # Get the character before the cursor
            if cursor_pos > 0:
                text = entry.get()
                prev_char = text[cursor_pos-1:cursor_pos]
                print(f"Previous character: {prev_char}")
                
                if prev_char.lower() in 'αεηιουω':
                    result = None
                    if char == '[':
                        result = self.add_smooth_breathing(prev_char)
                    elif char == ']':
                        result = self.add_rough_breathing(prev_char)
                    elif char == '{':
                        result = self.add_iota_subscript(prev_char)
                    
                    if result and result != prev_char:
                        entry.delete(cursor_pos-1, cursor_pos)
                        entry.insert(cursor_pos-1, result)
                        print(f"Inserted character with diacritic: {result}")
            
            return "break"
        
        return None

    def add_smooth_breathing(self, char):
        """Add smooth breathing to a vowel."""
        breathings = {
            'α': 'ἀ', 'ε': 'ἐ', 'η': 'ἠ', 'ι': 'ἰ', 
            'ο': 'ὀ', 'υ': 'ὐ', 'ω': 'ὠ',
            'Α': 'Ἀ', 'Ε': 'Ἐ', 'Η': 'Ἠ', 'Ι': 'Ἰ',
            'Ο': 'Ὀ', 'Υ': 'Υ̓', 'Ω': 'Ὠ'
        }
        result = breathings.get(char, char)
        print(f"Smooth breathing: {char} -> {result}")
        return result
        
    def add_rough_breathing(self, char):
        """Add rough breathing to a vowel."""
        breathings = {
            'α': 'ἁ', 'ε': 'ἑ', 'η': 'ἡ', 'ι': 'ἱ', 
            'ο': 'ὁ', 'υ': 'ὑ', 'ω': 'ὡ',
            'Α': 'Ἁ', 'Ε': 'Ἑ', 'Η': 'Ἡ', 'Ι': 'Ἱ',
            'Ο': 'Ὁ', 'Υ': 'Ὑ', 'Ω': 'Ὡ'
        }
        result = breathings.get(char, char)
        print(f"Rough breathing: {char} -> {result}")
        return result

    def add_iota_subscript(self, char):
        """Add iota subscript to a vowel."""
        subscripts = {
            'α': 'ᾳ', 'η': 'ῃ', 'ω': 'ῳ',
            'Α': 'ᾼ', 'Η': 'ῌ', 'Ω': 'ῼ'
        }
        if char not in subscripts:
            print(f"Cannot add iota subscript to {char}")
            return char
        result = subscripts[char]
        print(f"Iota subscript: {char} -> {result}")
        return result

    def normalize_greek(self, text):
        return unicodedata.normalize('NFC', text)

    def on_mode_change(self, event):
        """Handle mode change in the dropdown."""
        self.reset_table()
        self.update_word_display()

    def get_current_paradigm(self):
        """Get the currently selected paradigm."""
        mode = self.mode_var.get()
        paradigm_map = {
            "Article (ὁ, ἡ, το)": "article",
            "First Declension (μουσα)": "mousa",
            "First Declension -η (τιμη)": "time",
            "First Declension Long α (χωρα)": "chora",
            "First Declension Masculine (ναύτης)": "nautas",
            "Second Declension (λογος)": "logos",
            "Second Declension Neuter (δωρον)": "doron",
            "Third Declension Guard (φύλαξ)": "phylax",
            "Third Declension Body (σῶμα)": "soma",
            "Third Declension Old Man (γέρων)": "geron",
            "Third Declension Man (ἀνήρ)": "aner",
            "Third Declension Father (πατήρ)": "pater",
            "Third Declension Hope (ἐλπίς)": "elpis",
            "Third Declension Orator (ῥήτωρ)": "rhetor",
            "Third Declension Woman (γυνή)": "gyne",
            "Third Declension City (πόλις)": "polis"
        }
        
        paradigm_key = paradigm_map.get(mode)
        return self.paradigms.get(paradigm_key) if paradigm_key else None

    def check_answers(self):
        """Check all answers in the declension table."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            messagebox.showerror("Error", "No paradigm selected")
            return

        for case in ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]:
            if "singular" in current_paradigm and case.lower() in current_paradigm["singular"]:
                self.check_single_answer(f"{case}_sg", current_paradigm["singular"][case.lower()])
            
            if "plural" in current_paradigm and case.lower() in current_paradigm["plural"]:
                self.check_single_answer(f"{case}_pl", current_paradigm["plural"][case.lower()])

    def check_single_answer(self, entry_key, correct_answer):
        """Check a single answer."""
        entry = self.entries[entry_key]
        error_label = self.error_labels[entry_key]
        
        user_answer = self.normalize_greek(entry.get().strip())
        correct = self.normalize_greek(correct_answer)
        
        is_correct = user_answer.lower() == correct.lower()
        if is_correct:
            entry.configure(bg='gold')
            entry.configure(state='readonly')
            error_label.grid_remove()
        else:
            entry.configure(bg='white')
            error_label.grid()
        
        return is_correct

    def clear_error(self, entry_key):
        """Clear error indication for an entry."""
        entry = self.entries[entry_key]
        if entry.cget('state') != 'readonly':
            self.error_labels[entry_key].grid_remove()
            entry.configure(bg='white')

    def reveal_answers(self):
        """Reveal correct answers."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return

        for case in ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]:
            for number, key in [("singular", "sg"), ("plural", "pl")]:
                if number in current_paradigm and case.lower() in current_paradigm[number]:
                    entry_key = f"{case}_{key}"
                    if entry_key in self.entries:
                        entry = self.entries[entry_key]
                        entry.configure(state='normal')
                        entry.delete(0, tk.END)
                        entry.insert(0, current_paradigm[number][case.lower()])
                        entry.configure(state='readonly', bg='lightgray')

    def reset_table(self):
        """Reset the declension table."""
        for key, entry in self.entries.items():
            entry.configure(state='normal')
            entry.delete(0, tk.END)
            entry.configure(bg='white')
            self.error_labels[key].grid_remove()

    def show_help(self):
        """Show help dialog."""
        help_text = '''Ancient Greek Grammar Study

Instructions:
1. Select a declension type from the dropdown menu
2. Enter the correct forms in each field
3. Use Check Answers to verify your entries
4. Use Reveal Answers to see the correct forms
5. Use Reset to clear all entries

Navigation:
• Enter key: Move to next field (only if correct)
• Up/Down arrows: Move between cases
• Tab: Move between fields

Special Characters:
• Type a vowel (α, ε, η, ι, ο, υ, ω) followed by:
  - ] for rough breathing (e.g., o] → ὁ)
  - [ for smooth breathing (e.g., η[ → ἡ)
  - { for iota subscript (e.g., α{ → ᾳ)

Tips:
• The word to decline is shown above the table
• Gold background indicates correct answers
• Red X marks indicate incorrect answers
• Accents are not required'''

        help_window = tk.Toplevel(self.root)
        help_window.title("Greek Grammar Help")
        help_window.geometry("400x500")

        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)

    def handle_enter(self, event, current_key):
        """Handle Enter key press in form fields."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return "break"

        key_parts = current_key.split('_')
        case = key_parts[0]
        number = key_parts[1]
        number_key = 'singular' if number == 'sg' else 'plural'

        if case.lower() in current_paradigm.get(number_key, {}):
            if self.check_single_answer(current_key, current_paradigm[number_key][case.lower()]):
                cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
                current_idx = cases.index(case)
                
                if current_idx < len(cases) - 1:
                    next_key = f"{cases[current_idx + 1]}_{number}"
                else:
                    next_key = f"Nominative_pl" if number == "sg" else f"Nominative_sg"
                
                if next_key in self.entries and self.entries[next_key].cget('state') != 'readonly':
                    self.entries[next_key].focus()

        return "break"

    def handle_arrow(self, event, current_key, direction):
        """Handle arrow key navigation."""
        cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
        case, number = current_key.split('_')
        current_idx = cases.index(case)
        
        if direction == 'up' and current_idx > 0:
            next_key = f"{cases[current_idx - 1]}_{number}"
            self.entries[next_key].focus()
        elif direction == 'down' and current_idx < len(cases) - 1:
            next_key = f"{cases[current_idx + 1]}_{number}"
            self.entries[next_key].focus()
        return "break"

def main():
    try:
        print("Starting application...")
        root = tk.Tk()
        root.title("Ancient Greek Grammar Study")
        
        print("Configuring window...")
        root.minsize(600, 400)
        root.geometry("800x600")
        
        print("Configuring styles...")
        style = ttk.Style()
        style.configure('Content.TFrame', background='white', relief='solid')
        
        print("Creating application...")
        app = GreekGrammarApp(root)
        print("Starting main loop...")
        root.mainloop()
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
