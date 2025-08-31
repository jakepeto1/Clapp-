import tkinter as tk
from tkinter import ttk, messagebox
import json
import unicodedata
import webbrowser
from typing import Optional, Tuple

# Unicode combining characters for Greek diacritics
SMOOTH_BREATHING = '\u0313'  # ᾿
ROUGH_BREATHING = '\u0314'   # ῾
IOTA_SUBSCRIPT = '\u0345'    # ͅ (combines with α, η, ω)

# Default font settings
DEFAULT_FONT = None

def select_polytonic_font(root) -> Tuple[str, bool]:
    """
    Check for fonts with polytonic Greek support and select the best available option.
    
    Args:
        root: tk.Tk instance to query font families
        
    Returns:
        tuple: (font_family: str, needs_download: bool)
    """
    from tkinter import font
    
    # Preferred fonts in priority order with their test sizes
    POLYTONIC_FONTS = [
        ("New Athena Unicode", 14),
        ("Gentium", 12),
        ("Times New Roman", 12),
        ("Arial Unicode MS", 12)
    ]
    
    # Get available system fonts
    available_fonts = [f.strip() for f in font.families()]
    print(f"Available fonts: {available_fonts}")
    
    # Test character sequence for polytonic Greek support
    TEST_CHARS = "ἄἀὀῆῇᾳ"  # Extended test characters
    
    for font_name, size in POLYTONIC_FONTS:
        if font_name.strip() in available_fonts:
            try:
                # Create a test label with polytonic characters
                test_label = tk.Label(root, text=TEST_CHARS, font=(font_name, size))
                test_label.destroy()
                print(f"Selected font: {font_name}")
                
                # Font works - set it as default and return
                global DEFAULT_FONT
                DEFAULT_FONT = (font_name, size)
                return font_name, False
                
            except Exception as e:
                print(f"Font test failed for {font_name}: {str(e)}")
                continue
    
    # No polytonic fonts found - use system default but flag for warning
    print("No polytonic fonts found - using system default")
    DEFAULT_FONT = ("TkDefaultFont", 12)
    return "TkDefaultFont", True

class GreekGrammarApp:
    """
    Main application class for the Ancient Greek Grammar Study tool.
    Provides an interactive interface for practicing Greek declensions.
    """
                except Exception as e:
                    print(f"Font test failed for {clean_font_name}: {str(e)}")
                    continue
        return None

    def normalize_greek(self, text: str) -> str:
        """
        Normalize Greek text to ensure consistent handling of combining characters.
        Uses NFC normalization which combines characters and diacritics.
        """
        return unicodedata.normalize('NFC', text)

    def add_breathing(self, char: str, breathing: str) -> str:
        """
        Add a breathing mark to a Greek vowel.
        Args:
            char: The base vowel
            breathing: Either SMOOTH_BREATHING or ROUGH_BREATHING
        Returns:
            Normalized combination of vowel + breathing
        """
        # Make sure we're working with lowercase for consistency
        char = char.lower()
        # Only add breathing to vowels
        if char not in 'αεηιουω':
            return char
        return self.normalize_greek(char + breathing)

    def add_iota_subscript(self, char: str) -> str:
        """
        Add iota subscript to a vowel that can take it (α, η, ω)
        Returns the original character if it can't take iota subscript
        """
        char = char.lower()
        if char not in 'αηω':
            return char
        return self.normalize_greek(char + IOTA_SUBSCRIPT)

    def __init__(self, root):
        self.root = root
        self.root.title("Ancient Greek Grammar Study")
        
        # Initialize dictionaries for entries and error labels
        self.entries = {}
        self.error_labels = {}
        
        print("Initializing application...")
        # Set up fonts that support polytonic Greek
        font_name, needs_download = select_polytonic_font(root)
        print(f"Selected font: {font_name} (needs_download: {needs_download})")
        
        # Create font objects for different uses
        from tkinter import font
        self.greek_font = DEFAULT_FONT  # Store the basic font tuple
        
        # Create specific font configurations
        self.normal_font = font.Font(family=self.greek_font[0], size=self.greek_font[1])
        self.bold_font = font.Font(family=self.greek_font[0], size=self.greek_font[1], weight='bold')
        self.large_font = font.Font(family=self.greek_font[0], size=self.greek_font[1] + 2)
        self.small_font = font.Font(family=self.greek_font[0], size=self.greek_font[1] - 2)
        
        # Configure default fonts for different widget types
        self.root.option_add('*Font', self.normal_font)
        self.root.option_add('*Entry.font', self.normal_font)
        self.root.option_add('*Text.font', self.normal_font)
        self.root.option_add('*Label.font', self.normal_font)
        self.root.option_add('*Button.font', self.normal_font)
        
        # Create a test label with polytonic text
        test_frame = ttk.Frame(root)
        test_frame.grid(row=0, column=0, columnspan=3, pady=(5,15))
        
        test_label = ttk.Label(
            test_frame,
            text="Font Test: ἄνθρωπος • παιδεύω • ψυχή • ὦ φίλε",
            font=self.normal_font
        )
        test_label.grid(row=0, column=0, padx=5)
        
        # Show warning if no polytonic font found
        if needs_download:
            warning_label = ttk.Label(
                test_frame,
                text="⚠️ Limited polytonic support - please install recommended font",
                foreground='red',
                font=self.small_font
            )
            warning_label.grid(row=1, column=0, padx=5)
            
            if messagebox.askyesno(
                "Font Missing",
                "No polytonic Greek font found. Would you like to download New Athena Unicode?",
                icon="warning"
            ):
                webbrowser.open("https://apagreekkeys.org/NAUdownload.html")
        
        # Create a help button
        help_button = ttk.Button(root, text="Help", command=self.show_help, width=5)
        help_button.grid(row=0, column=0, sticky='nw', padx=5, pady=5)
        
        # Set up proper Unicode handling for Greek characters
        import sys
        if sys.platform.startswith('win'):
            import locale
            locale.setlocale(locale.LC_ALL, 'Greek_Greece.UTF-8')
        
        # Initialize paradigms
        self.paradigms = {}
        
        # Load paradigm data
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
            
        # Configure root window
        root.configure(padx=20, pady=20)
        
        # Main container
        self.main_frame = ttk.Frame(root)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(self.main_frame, text="Ancient Greek Grammar Study", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Study mode selection frame
        mode_frame = ttk.Frame(self.main_frame)
        mode_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        mode_frame.columnconfigure(1, weight=1)
        
        ttk.Label(mode_frame, text="Select Study Mode:").grid(row=0, column=0, padx=(0, 10))
        self.mode_var = tk.StringVar(value="First Declension (μουσα)")
        modes = [
            "Article (ὁ, ἡ, το)",
            "First Declension (μουσα)",
            "First Declension -η (τιμη)",
            "First Declension Long α (χωρα)",
            "First Declension Masculine (ναύτης)",
            "Second Declension (λογος)",
            "Second Declension Neuter (δωρον)",
            "Mixed Declension Son (υἱός)",
            "Third Declension Guard (φύλαξ)",
            "Third Declension Body (σῶμα)",
            "Third Declension Old Man (γέρων)",
            "Third Declension Man (ἀνήρ)",
            "Third Declension Father (πατήρ)",
            "Third Declension Hope (ἐλπίς)",
            "Third Declension Orator (ῥήτωρ)",
            "Third Declension Woman (γυνή)",
            "Third Declension City (πόλις)",
            "Third Declension Town (ἄστυ)",
            "Third Declension King (βασιλεύς)",
            "Third Declension Ox (βοῦς)",
            "Third Declension Ship (ναῦς)",
            "Third Declension Race (γένος)",
            "Third Declension Trireme (τριήρης)"
        ]
        mode_dropdown = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=modes, font=self.greek_font)
        mode_dropdown.grid(row=0, column=1, sticky='ew')
        mode_dropdown.state(['readonly'])
        mode_dropdown.bind('<<ComboboxSelected>>', self.on_mode_change)
        
        # Current word frame
        word_frame = ttk.Frame(self.main_frame)
        word_frame.grid(row=2, column=0, columnspan=3, pady=(0, 20))
        ttk.Label(word_frame, text="Decline the word:", font=('Arial', 12)).grid(row=0, column=0, padx=(0, 10))
        self.word_label = ttk.Label(word_frame, font=self.greek_font)
        self.word_label.grid(row=0, column=1)
        
        # Create declension table
        self.create_declension_table()
        
        # Buttons frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)  # Moved to row 4, after table
        
        check_button = ttk.Button(button_frame, text="Check Answers", command=self.check_answers, width=15)
        check_button.grid(row=0, column=0, padx=10)
        
        reveal_button = ttk.Button(button_frame, text="Reveal Answers", command=self.reveal_answers, width=15)
        reveal_button.grid(row=0, column=1, padx=10)
        
        reset_button = ttk.Button(button_frame, text="Reset", command=self.reset_table, width=15)
        reset_button.grid(row=0, column=2, padx=10)

    def create_declension_table(self):
        """Create the appropriate declension table based on the selected mode"""
        # Clear existing entries and error labels
        for key in list(self.entries.keys()):
            if key in self.entries:
                self.entries[key].destroy()
        for key in list(self.error_labels.keys()):
            if key in self.error_labels:
                self.error_labels[key].destroy()
        
        self.entries.clear()
        self.error_labels.clear()

        # Table frame
        table_frame = ttk.Frame(self.main_frame)
        table_frame.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(0, 20))
        
        # Get current paradigm to determine table type
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
            
        # Use gendered table for articles and any other paradigms with gender-specific forms
        if current_paradigm['type'] == 'article':
            self.create_gendered_table(table_frame)
        else:
            self.create_regular_table(table_frame)
            
    def create_regular_table(self, table_frame):
        # Configure table grid weights
        for i in range(5):  # Columns: Label, Sg Error, Sg Entry, Pl Error, Pl Entry
            table_frame.columnconfigure(i, weight=1 if i in [2, 4] else 0)
        
        # Table headers
        ttk.Label(table_frame, text="", width=15).grid(row=0, column=0)
        ttk.Label(table_frame, text="", width=2).grid(row=0, column=1)
        ttk.Label(table_frame, text="Singular", font=('Arial', 10, 'bold')).grid(row=0, column=2, pady=(0, 10))
        ttk.Label(table_frame, text="", width=2).grid(row=0, column=3)
        ttk.Label(table_frame, text="Plural", font=('Arial', 10, 'bold')).grid(row=0, column=4, pady=(0, 10))
        
        # Create input fields
        cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
        
        for i, case in enumerate(cases):
            # Case label
            ttk.Label(table_frame, text=case, width=15).grid(row=i+1, column=0, sticky='e', padx=(0, 10))
            
            # Singular
            self.error_labels[f"{case}_sg"] = ttk.Label(table_frame, text="❌", foreground='red')
            self.error_labels[f"{case}_sg"].grid(row=i+1, column=1, padx=5)
            self.error_labels[f"{case}_sg"].grid_remove()
            
            entry_sg = tk.Entry(table_frame, width=20, font=self.greek_font)
            self.entries[f"{case}_sg"] = entry_sg
            entry_sg.grid(row=i+1, column=2, padx=5, pady=5)
            
            entry_sg.bind('<Key>', lambda e, case=case: self.clear_error(f"{case}_sg"))
            entry_sg.bind('<Return>', lambda e, case=case: self.handle_enter(e, f"{case}_sg"))
            entry_sg.bind('<Up>', lambda e, case=case: self.handle_arrow(e, f"{case}_sg", 'up'))
            entry_sg.bind('<Down>', lambda e, case=case: self.handle_arrow(e, f"{case}_sg", 'down'))
            
            # Plural
            self.error_labels[f"{case}_pl"] = ttk.Label(table_frame, text="❌", foreground='red')
            self.error_labels[f"{case}_pl"].grid(row=i+1, column=3, padx=5)
            self.error_labels[f"{case}_pl"].grid_remove()
            
            entry_pl = tk.Entry(table_frame, width=20, font=self.greek_font)
            self.entries[f"{case}_pl"] = entry_pl
            entry_pl.grid(row=i+1, column=4, padx=5, pady=5)
            
            entry_pl.bind('<Key>', lambda e, case=case: self.clear_error(f"{case}_pl"))
            entry_pl.bind('<Return>', lambda e, case=case: self.handle_enter(e, f"{case}_pl"))
            entry_pl.bind('<Up>', lambda e, case=case: self.handle_arrow(e, f"{case}_pl", 'up'))
            entry_pl.bind('<Down>', lambda e, case=case: self.handle_arrow(e, f"{case}_pl", 'down'))
        
    def create_gendered_table(self, table_frame):
        """Create a table with masculine, feminine, and neuter columns for articles"""
        # Configure weights for 7 columns: label + (m, f, n) genders
        for i in range(7):  # Columns: Label, M, Error, F, Error, N
            table_frame.columnconfigure(i, weight=1 if i in [1, 3, 5] else 0)
        
        # Headers
        ttk.Label(table_frame, text="", width=15).grid(row=0, column=0)
        ttk.Label(table_frame, text="Masculine", font=('Arial', 10, 'bold')).grid(row=0, column=1, pady=(0, 10))
        ttk.Label(table_frame, text="Feminine", font=('Arial', 10, 'bold')).grid(row=0, column=3, pady=(0, 10))
        ttk.Label(table_frame, text="Neuter", font=('Arial', 10, 'bold')).grid(row=0, column=5, pady=(0, 10))
        
        # Create entries for singular and plural
        sections = ["Singular", "Plural"]
        cases = ["Nominative", "Genitive", "Dative", "Accusative"]  # Vocative is same as nominative for articles
        genders = ["masc", "fem", "neut"]
        
        for section_idx, section in enumerate(sections):
            # Section header
            ttk.Label(table_frame, text=section, font=('Arial', 10, 'bold')).grid(
                row=section_idx * (len(cases) + 1) + 1,
                column=0,
                columnspan=7,
                sticky='w',
                pady=(10, 5)
            )
            
            # Create entries for each case and gender
            for case_idx, case in enumerate(cases):
                row = section_idx * (len(cases) + 1) + case_idx + 2
                
                # Case label
                ttk.Label(table_frame, text=case, width=15).grid(row=row, column=0, sticky='e', padx=(0, 10))
                
                # Create entries for each gender
                for gender_idx, gender in enumerate(genders):
                    col = gender_idx * 2 + 1  # Column for entry
                    entry_key = f"{case}_{section.lower()}_{gender}"
                    
                    # Error label
                    self.error_labels[entry_key] = ttk.Label(table_frame, text="❌", foreground='red')
                    self.error_labels[entry_key].grid(row=row, column=col+1, padx=2)
                    self.error_labels[entry_key].grid_remove()
                    
                    # Entry field
                    entry = tk.Entry(table_frame, width=10, font=self.greek_font)
                    self.entries[entry_key] = entry
                    entry.grid(row=row, column=col, padx=5, pady=2)
                    
                    # Event bindings
                    entry.bind('<Key>', lambda e, key=entry_key: self.clear_error(key))
                    entry.bind('<Return>', lambda e, key=entry_key: self.handle_enter(e, key))
                    entry.bind('<Up>', lambda e, key=entry_key: self.handle_arrow(e, key, 'up'))
                    entry.bind('<Down>', lambda e, key=entry_key: self.handle_arrow(e, key, 'down'))
                    
                    # Error label column
                    self.error_labels[entry_key] = ttk.Label(table_frame, text="❌", foreground='red')
                    self.error_labels[entry_key].grid(row=row, column=gender_idx*2, padx=2)
                    self.error_labels[entry_key].grid_remove()
                    
                    # Entry column
                    entry = tk.Entry(table_frame, width=10, font=self.greek_font)
                    self.entries[entry_key] = entry
                    entry.grid(row=row, column=gender_idx*2 + 1, padx=5, pady=2)
                    
                    # Make a copy of the current key for the lambda functions
                    current_key = entry_key  # This is crucial for proper event binding
                    
                    # Bindings
                    entry.bind('<Key>', lambda e, key=current_key: self.clear_error(key))
                    entry.bind('<Return>', lambda e, key=current_key: self.handle_enter(e, key))
                    entry.bind('<Up>', lambda e, key=current_key: self.handle_arrow(e, key, 'up'))
                    entry.bind('<Down>', lambda e, key=current_key: self.handle_arrow(e, key, 'down'))
        
        # Create input fields
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]  # British order
        self.entries = {}
        self.error_labels = {}
        
        for i, case in enumerate(cases):
            # Case label with consistent width
            ttk.Label(table_frame, text=case, width=15).grid(row=i+1, column=0, sticky='e', padx=(0, 10))
            
            # Singular entry and error mark
            self.error_labels[f"{case}_sg"] = ttk.Label(table_frame, text="❌", foreground='red')
            self.error_labels[f"{case}_sg"].grid(row=i+1, column=1, padx=5)
            self.error_labels[f"{case}_sg"].grid_remove()  # Hide initially
            
            # Create entry with explicit Greek font and Unicode support
            entry_sg = tk.Entry(table_frame, width=20, 
                              font=self.greek_font,  # Use the detected font
                              bg='white', fg='black')
            self.entries[f"{case}_sg"] = entry_sg
            entry_sg.grid(row=i+1, column=2, padx=5, pady=5)
            
            # Basic navigation and validation bindings
            entry_sg.bind('<Key>', lambda e, case=case: self.clear_error(f"{case}_sg"))
            entry_sg.bind('<Return>', lambda e, case=case: self.handle_enter(e, f"{case}_sg"))
            entry_sg.bind('<Up>', lambda e, case=case: self.handle_arrow(e, f"{case}_sg", 'up'))
            entry_sg.bind('<Down>', lambda e, case=case: self.handle_arrow(e, f"{case}_sg", 'down'))
            
            # TODO: Re-enable these once breathing/subscript issues are resolved
            # entry_sg.bind('<KeyPress-colon>', lambda e: self.handle_special_input(e, SMOOTH_BREATHING))
            # entry_sg.bind('<KeyPress-at>', lambda e: self.handle_special_input(e, ROUGH_BREATHING))
            # entry_sg.bind('<KeyPress-braceleft>', lambda e: self.handle_special_input(e, IOTA_SUBSCRIPT))
            
            # Create invisible spacer label to maintain layout
            spacer_sg = ttk.Label(table_frame, text="❌", foreground='red')
            spacer_sg.grid(row=i+1, column=1, padx=5)
            spacer_sg.grid_remove()
            
            # Plural entry and error mark
            self.error_labels[f"{case}_pl"] = ttk.Label(table_frame, text="❌", foreground='red')
            self.error_labels[f"{case}_pl"].grid(row=i+1, column=3, padx=5)
            self.error_labels[f"{case}_pl"].grid_remove()  # Hide initially
            
            # Create entry with explicit Greek font and Unicode support
            entry_pl = tk.Entry(table_frame, width=20,
                              font=self.greek_font,  # Use the detected font
                              bg='white', fg='black')
            self.entries[f"{case}_pl"] = entry_pl
            entry_pl.grid(row=i+1, column=4, padx=5, pady=5)
            
            # Basic navigation and validation bindings
            entry_pl.bind('<Key>', lambda e, case=case: self.clear_error(f"{case}_pl"))
            entry_pl.bind('<Return>', lambda e, case=case: self.handle_enter(e, f"{case}_pl"))
            entry_pl.bind('<Up>', lambda e, case=case: self.handle_arrow(e, f"{case}_pl", 'up'))
            entry_pl.bind('<Down>', lambda e, case=case: self.handle_arrow(e, f"{case}_pl", 'down'))
            # TODO: Re-enable these once breathing/subscript issues are resolved
            # entry_pl.bind('<KeyPress-colon>', lambda e: self.handle_special_input(e, SMOOTH_BREATHING))
            # entry_pl.bind('<KeyPress-at>', lambda e: self.handle_special_input(e, ROUGH_BREATHING))
            # entry_pl.bind('<KeyPress-braceleft>', lambda e: self.handle_special_input(e, IOTA_SUBSCRIPT))
            
            # Create invisible spacer label to maintain layout
            spacer_pl = ttk.Label(table_frame, text="❌", foreground='red')
            spacer_pl.grid(row=i+1, column=3, padx=5)
            spacer_pl.grid_remove()

    def check_answers(self):
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            messagebox.showerror("Error", "No paradigm selected")
            return
            
        for case in ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]:
            # Check singular
            if "singular" in current_paradigm and case.lower() in current_paradigm["singular"]:
                self.check_single_answer(f"{case}_sg", current_paradigm["singular"][case.lower()])
            
            # Check plural
            if "plural" in current_paradigm and case.lower() in current_paradigm["plural"]:
                self.check_single_answer(f"{case}_pl", current_paradigm["plural"][case.lower()])

    def check_single_answer(self, entry_key, correct_answer):
        entry = self.entries[entry_key]
        error_label = self.error_labels[entry_key]
        
        # Remove accents from both the user's answer and correct answer for comparison
        user_answer = self.remove_accents(entry.get().strip().lower())
        correct = self.remove_accents(correct_answer.lower())
        
        if user_answer == correct:
            entry.configure(style='Correct.TEntry')
            entry.configure(state='readonly')  # Make it unchangeable
            error_label.grid_remove()  # Hide the error mark
        else:
            entry.configure(style='Wrong.TEntry')
            error_label.grid()  # Show the error mark
            
    def handle_enter(self, event, current_key):
        """Handle enter key press - check answer and if correct, move to next field"""
        # Get the current paradigm
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return "break"
            
        # Get the current answer and entry
        entry = self.entries[current_key]
        user_answer = entry.get().strip()
        
        # For regular nouns (non-article)
        if "_sg" in current_key or "_pl" in current_key:
            # Parse key (format: case_number - e.g., "Nominative_sg")
            case, number = current_key.split('_')
            paradigm_section = "singular" if number == "sg" else "plural"
            correct_answer = current_paradigm[paradigm_section][case.lower()]
            
            # Check if correct
            is_correct = user_answer.lower() == correct_answer.lower()
            if is_correct:
                # Mark as correct and make readonly
                entry.configure(bg='gold')
                entry.configure(state='readonly')
                self.error_labels[current_key].grid_remove()
                
                # Navigate to next field
                cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
                numbers = ["sg", "pl"]
                
                # Find current position
                current_case_idx = cases.index(case)
                current_number_idx = numbers.index(number)
                
                # Try to move to next field in this order:
                # 1. Next case in same number (sg/pl)
                # 2. First case in other number
                next_case_idx = current_case_idx + 1
                next_number = number
                
                if next_case_idx >= len(cases):
                    if number == "sg":
                        next_case_idx = 0
                        next_number = "pl"
                    else:
                        # Stay in the last field if we're at the end
                        return "break"
                        
                next_key = f"{cases[next_case_idx]}_{next_number}"
                if next_key in self.entries and self.entries[next_key].cget('state') != 'readonly':
                    self.entries[next_key].focus()
            else:
                # Show error but keep focus
                entry.configure(bg='white')
                self.error_labels[current_key].grid()
                
        # For article and other gendered words
        else:
            # Parse key (format: case_number_gender - e.g., "Nominative_singular_masc")
            case, number, gender = current_key.split('_')
            gender_index = {"masc": 0, "fem": 1, "neut": 2}[gender]
            correct_answer = current_paradigm[number][case.lower()][gender_index]
            
            # Check if correct
            is_correct = user_answer.lower() == correct_answer.lower()
            if is_correct:
                # Mark as correct and make readonly
                entry.configure(bg='gold')
                entry.configure(state='readonly')
                self.error_labels[current_key].grid_remove()
                
                # Navigate in order: masc → fem → neut, then next case
                cases = ["Nominative", "Genitive", "Dative", "Accusative"]
                genders = ["masc", "fem", "neut"]
                numbers = ["singular", "plural"]
                
                # Find current positions
                current_case_idx = cases.index(case)
                current_gender_idx = genders.index(gender)
                current_number_idx = numbers.index(number)
                
                # Try to move to next gender
                next_gender_idx = current_gender_idx + 1
                next_case_idx = current_case_idx
                next_number_idx = current_number_idx
                
                if next_gender_idx >= len(genders):
                    next_gender_idx = 0
                    next_case_idx += 1
                    if next_case_idx >= len(cases):
                        next_case_idx = 0
                        next_number_idx += 1
                        if next_number_idx >= len(numbers):
                            return "break"
                            
                next_key = f"{cases[next_case_idx]}_{numbers[next_number_idx]}_{genders[next_gender_idx]}"
                if next_key in self.entries and self.entries[next_key].cget('state') != 'readonly':
                    self.entries[next_key].focus()
            else:
                # Show error but keep focus
                entry.configure(bg='white')
                self.error_labels[current_key].grid()
                
        return "break"
            
    def strip_to_base_with_breathing_and_iota(self, text):
        """Strip everything except base letters, breathings, and iota subscripts"""
        # Dictionary to map characters with accents to their base + breathing/iota form
        replacements = {
            # Alpha variations
            'ά': 'α', 'ὰ': 'α', 'ᾶ': 'α',
            'ἀ': 'ἀ', 'ἁ': 'ἁ',  # Keep breathings
            'ᾳ': 'ᾳ',  # Keep iota subscript
            
            # Epsilon variations
            'έ': 'ε', 'ὲ': 'ε',
            'ἐ': 'ἐ', 'ἑ': 'ἑ',  # Keep breathings
            
            # Eta variations
            'ή': 'η', 'ὴ': 'η', 'ῆ': 'η',
            'ἠ': 'ἠ', 'ἡ': 'ἡ',  # Keep breathings
            'ῃ': 'ῃ',  # Keep iota subscript
            
            # Iota variations
            'ί': 'ι', 'ὶ': 'ι', 'ῖ': 'ι',
            'ἰ': 'ἰ', 'ἱ': 'ἱ',  # Keep breathings
            
            # Omicron variations
            'ό': 'ο', 'ὸ': 'ο',
            'ὀ': 'ὀ', 'ὁ': 'ὁ',  # Keep breathings
            
            # Upsilon variations
            'ύ': 'υ', 'ὺ': 'υ', 'ῦ': 'υ',
            'ὐ': 'ὐ', 'ὑ': 'ὑ',  # Keep breathings
            
            # Omega variations
            'ώ': 'ω', 'ὼ': 'ω', 'ῶ': 'ω',
            'ὠ': 'ὠ', 'ὡ': 'ὡ',  # Keep breathings
            'ῳ': 'ῳ',  # Keep iota subscript
        }
        
        result = text.lower()
        for accented, base in replacements.items():
            result = result.replace(accented.lower(), base)
        return result

    def check_single_answer(self, entry_key, correct_answer):
        """Check if the user's answer matches the correct answer, handling both single forms and arrays"""
        entry = self.entries[entry_key]
        error_label = self.error_labels[entry_key]
        
        user_answer = self.strip_to_base_with_breathing_and_iota(entry.get().strip())
        
        # Handle array of correct answers (for articles with multiple gender forms)
        if isinstance(correct_answer, list):
            # Extract gender index from the entry key
            if "_masc" in entry_key:
                gender_idx = 0
            elif "_fem" in entry_key:
                gender_idx = 1
            elif "_neut" in entry_key:
                gender_idx = 2
            else:
                return False
            
            correct = self.strip_to_base_with_breathing_and_iota(correct_answer[gender_idx])
        else:
            correct = self.strip_to_base_with_breathing_and_iota(correct_answer)
        
        # Compare answers
        is_correct = user_answer == correct
        if is_correct:
            entry.configure(bg='gold')
            entry.configure(state='readonly')
            error_label.grid_remove()
        else:
            entry.configure(bg='white')
            error_label.grid()
            
        return is_correct
            
    def clear_error(self, entry_key):
        entry = self.entries[entry_key]
        if entry.cget('state') != 'readonly':  # Only clear if not correct
            self.error_labels[entry_key].grid_remove()
            entry.configure(bg='white')

    def reveal_answers(self):
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
            
        for case in ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]:
            # Fill singular
            if "singular" in current_paradigm and case.lower() in current_paradigm["singular"]:
                entry_key = f"{case}_sg"
                if entry_key in self.entries:
                    entry = self.entries[entry_key]
                    entry.delete(0, tk.END)
                    entry.insert(0, current_paradigm["singular"][case.lower()])
                    entry.configure(state='readonly', bg='lightgray')
                    
            # Fill plural
            if "plural" in current_paradigm and case.lower() in current_paradigm["plural"]:
                entry_key = f"{case}_pl"
                if entry_key in self.entries:
                    entry = self.entries[entry_key]
                    entry.delete(0, tk.END)
                    entry.insert(0, current_paradigm["plural"][case.lower()])
                    entry.configure(state='readonly', bg='lightgray')
    
    def reset_table(self):
        for key, entry in self.entries.items():
            entry.configure(state='normal')  # Reset to editable
            entry.delete(0, tk.END)  # Clear the content
            entry.configure(bg='white')  # Reset background color
            self.error_labels[key].grid_remove()  # Hide error mark
            
    def show_help(self):
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

Tips:
• The word to decline is shown above the table
• Gold background indicates correct answers
• Red X marks indicate incorrect answers
• Accents are not required'''
   
        help_window = tk.Toplevel(self.root)
        help_window.title("Greek Grammar Help")
        help_window.geometry("400x300")
        
        help_text = '''How to enter Greek characters:
        
1. Type any vowel (α, ε, η, ι, ο, υ, ω)
2. Then type:
   • ] for rough breathing (example: o] → ὁ)
   • [ for smooth breathing (example: η[ → ἡ)

Note: Accents are not required for this exercise.'''
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)

        help_window = tk.Toplevel(self.root)
        help_window.title("Typing Help")
        help_window.geometry("400x500")
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state='disabled')
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        def on_key(event):
            if event.char == '[':  # Smooth breathing
                entry = event.widget
                text = entry.get()
                if text:
                    last_char = text[-1]
                    with_breathing = self.add_smooth_breathing(last_char)
                    entry.delete(len(text)-1, tk.END)
                    entry.insert(tk.END, with_breathing)
                return "break"
            elif event.char == ']':  # Rough breathing
                entry = event.widget
                text = entry.get()
                if text:
                    last_char = text[-1]
                    with_breathing = self.add_rough_breathing(last_char)
                    entry.delete(len(text)-1, tk.END)
                    entry.insert(tk.END, with_breathing)
                return "break"
            elif event.char == '|':  # Iota subscript
                entry = event.widget
                text = entry.get()
                if text:
                    last_char = text[-1]
                    with_iota = self.add_iota_subscript(last_char)
                    entry.delete(len(text)-1, tk.END)
                    entry.insert(tk.END, with_iota)
                return "break"
                
    def add_smooth_breathing(self, char):
        breathings = {
            'α': 'ἀ', 'ε': 'ἐ', 'η': 'ἠ', 'ι': 'ἰ', 
            'ο': 'ὀ', 'υ': 'ὐ', 'ω': 'ὠ'
        }
        return breathings.get(char, char)
        
    def add_rough_breathing(self, char):
        breathings = {
            'α': 'ἁ', 'ε': 'ἑ', 'η': 'ἡ', 'ι': 'ἱ', 
            'ο': 'ὁ', 'υ': 'ὑ', 'ω': 'ὡ'
        }
        return breathings.get(char, char)
        
    def add_iota_subscript(self, char):
        subscripts = {
            'α': 'ᾳ', 'η': 'ῃ', 'ω': 'ῳ'
        }
        return subscripts.get(char, char)
            
    def handle_enter(self, event, current_key):
        """Handle Enter key press in form fields"""
        # Get current paradigm and validate input
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return "break"

        # Parse key components
        key_parts = current_key.split('_')
        case = key_parts[0]
        number = key_parts[1]
        number_key = 'singular' if number == 'sg' else 'plural'

        # Check answer
        if self.check_single_answer(current_key, current_paradigm[number_key][case.lower()]):
            # Answer is correct, determine next field
            cases = ["Nominative", "Genitive", "Dative", "Accusative", "Vocative"]
            current_idx = cases.index(case)
            
            # Determine next field to focus
            if current_idx < len(cases) - 1:
                next_key = f"{cases[current_idx + 1]}_{number}"
            else:  # At end of cases
                if number == "sg":
                    next_key = f"Nominative_pl"  # Move to plural
                else:
                    next_key = f"Nominative_sg"  # Wrap around
            
            # Focus next field if it exists and isn't readonly
            if next_key in self.entries and self.entries[next_key].cget('state') != 'readonly':
                self.entries[next_key].focus()

        return "break"
        
    def handle_arrow(self, event, current_key, direction):
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        case, number = current_key.split('_')
        current_idx = cases.index(case)
        
        if direction == 'up' and current_idx > 0:
            next_key = f"{cases[current_idx - 1]}_{number}"
            self.entries[next_key].focus()
        elif direction == 'down' and current_idx < len(cases) - 1:
            next_key = f"{cases[current_idx + 1]}_{number}"
            self.entries[next_key].focus()
        return "break"  # Prevent default arrow behavior
        
    def get_current_paradigm(self):
        """Get the currently selected paradigm based on the dropdown selection."""
        mode = self.mode_var.get() if hasattr(self, 'mode_var') else ""
        
        # Map dropdown selections to paradigm keys
        paradigm_map = {
            "Article (ὁ, ἡ, το)": "article",
            "First Declension (μουσα)": "mousa",
            "First Declension -η (τιμη)": "time",
            "First Declension Long α (χωρα)": "chora",
            "First Declension Masculine (ναύτης)": "nautas",
            "Second Declension (λογος)": "logos",
            "Second Declension Neuter (δωρον)": "doron",
            "Mixed Declension Son (υἱός)": "huios",
            "Third Declension Guard (φύλαξ)": "phylax",
            "Third Declension Body (σῶμα)": "soma",
            "Third Declension Old Man (γέρων)": "geron",
            "Third Declension Man (ἀνήρ)": "aner",
            "Third Declension Father (πατήρ)": "pater",
            "Third Declension Hope (ἐλπίς)": "elpis",
            "Third Declension Orator (ῥήτωρ)": "rhetor",
            "Third Declension Woman (γυνή)": "gyne",
            "Third Declension City (πόλις)": "polis",
            "Third Declension Town (ἄστυ)": "asty",
            "Third Declension King (βασιλεύς)": "basileus",
            "Third Declension Ox (βοῦς)": "bous",
            "Third Declension Ship (ναῦς)": "naus",
            "Third Declension Race (γένος)": "genos",
            "Third Declension Trireme (τριήρης)": "trieres"
        }
        
        # Get the paradigm key directly from the map
        paradigm_key = paradigm_map.get(mode)
        if paradigm_key and paradigm_key in self.paradigms:
            return self.paradigms[paradigm_key]
        
        # If no valid paradigm found, return None
        return None
            
    def on_mode_change(self, event):
        self.reset_table()
        paradigm = self.get_current_paradigm()
        if not paradigm:
            messagebox.showerror("Error", "Could not find paradigm data")
            return
            
        # Update the word to decline
        self.word_label.configure(text=paradigm["lemma"])
        
    def handle_special_input(self, event):
        """Handle special character input for breathings and iota subscript"""
        entry = event.widget
        text = entry.get()
        cursor_pos = entry.index(tk.INSERT)
        
        print(f"Special input handler - char: {event.char}, text: {text}, pos: {cursor_pos}")
        
        # For smooth breathing (:)
        if event.char == ':':
            if cursor_pos > 0:
                char = text[cursor_pos - 1].lower()
                if char in 'αεηιουω':
                    result = self.add_breathing(char, SMOOTH_BREATHING)
                    if result:
                        entry.delete(cursor_pos - 1)
                        entry.insert(cursor_pos - 1, result)
                        print(f"Added smooth breathing: {result}")
                    
        # For rough breathing (@)
        elif event.char == '@':
            entry.rough_breathing_pending = True
            print("Rough breathing pending")
            
        # For iota subscript ({)
        elif event.char == '{':
            entry.iota_subscript_pending = True
            print("Iota subscript pending")
            
        # Handle normal character input when a diacritic is pending
        elif hasattr(entry, 'rough_breathing_pending') and entry.rough_breathing_pending:
            if event.char.lower() in 'αεηιουω':
                result = self.add_breathing(event.char.lower(), ROUGH_BREATHING)
                if result:
                    entry.insert(cursor_pos, result)
                    print(f"Added rough breathing: {result}")
                entry.rough_breathing_pending = False
                return "break"
            entry.rough_breathing_pending = False
            
        elif hasattr(entry, 'iota_subscript_pending') and entry.iota_subscript_pending:
            if event.char.lower() in 'αηω':
                result = self.add_iota_subscript(event.char.lower())
                if result:
                    entry.insert(cursor_pos, result)
                    print(f"Added iota subscript: {result}")
                entry.iota_subscript_pending = False
                return "break"
            entry.iota_subscript_pending = False
            
        return "break"
        entry = event.widget
        text = entry.get()
        
        if not text:
            return
            
        # Get the last character
        base_char = text[-1].lower()
        
        # Define the combinations
        if event.char == '[':  # Smooth breathing
            if base_char == 'α': result = 'ἀ'
            elif base_char == 'ε': result = 'ἐ'
            elif base_char == 'η': result = 'ἠ'
            elif base_char == 'ι': result = 'ἰ'
            elif base_char == 'ο': result = 'ὀ'
            elif base_char == 'υ': result = 'ὐ'
            elif base_char == 'ω': result = 'ὠ'
            else: return
            
        elif event.char == ']':  # Rough breathing
            if base_char == 'α': result = 'ἁ'
            elif base_char == 'ε': result = 'ἑ'
            elif base_char == 'η': result = 'ἡ'
            elif base_char == 'ι': result = 'ἱ'
            elif base_char == 'ο': result = 'ὁ'
            elif base_char == 'υ': result = 'ὑ'
            elif base_char == 'ω': result = 'ὡ'
            else: return
            
        elif event.char == '|':  # Iota subscript
            if base_char == 'α': result = 'ᾳ'
            elif base_char == 'η': result = 'ῃ'
            elif base_char == 'ω': result = 'ῳ'
            else: return
        else:
            return
            
        # Apply the change
        entry.delete(len(text)-1, tk.END)
        entry.insert(tk.END, result)
        return "break"  # Prevent default handling

    def insert_char(self, char):
        """Insert a character at the current cursor position in the focused entry"""
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry)):
            # Always normalize the character before inserting
            normalized_char = self.normalize_greek(char)
            pos = focused.index(tk.INSERT)
            focused.insert(pos, normalized_char)
            focused.focus()  # Ensure focus remains on the entry
            
    def handle_special_input(self, event, diacritic):
        """
        Handle special character input for breathings and iota subscript.
        Args:
            event: The key event
            diacritic: The diacritic to add (SMOOTH_BREATHING, ROUGH_BREATHING, or IOTA_SUBSCRIPT)
        """
        entry = event.widget
        text = entry.get()
        
        # Do nothing if there's no text
        if not text:
            return "break"
            
        # Get the last character typed
        last_char = text[-1].lower()
        result = None
        
        # Apply the appropriate diacritic
        if diacritic in (SMOOTH_BREATHING, ROUGH_BREATHING):
            if last_char in 'αεηιουω':
                result = self.normalize_greek(last_char + diacritic)
        elif diacritic == IOTA_SUBSCRIPT:
            if last_char in 'αηω':
                result = self.normalize_greek(last_char + diacritic)
            
        # If we successfully created a combined character, replace the last character
        if result:
            entry.delete(len(text)-1, tk.END)
            entry.insert(tk.END, result)
            
        # Always return "break" to prevent the special character from being inserted
        return "break"

if __name__ == "__main__":
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.configure('Correct.TEntry', fieldbackground='light green')
    style.configure('Incorrect.TEntry', fieldbackground='light coral')
    
    app = GreekGrammarApp(root)
    root.mainloop()
