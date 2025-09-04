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
        mode_frame.columnconfigure(3, weight=1)

        # Add type selector (Noun vs Adjective)
        ttk.Label(mode_frame, text="Type:").grid(
            row=0, column=0, padx=(0, 10)
        )
        
        self.type_var = tk.StringVar(value="Noun")
        type_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.type_var,
            values=["Noun", "Adjective", "Pronoun", "Verb"],
            font=('Times New Roman', 12),
            width=12,
            state='readonly'
        )
        type_dropdown.grid(row=0, column=1, sticky='w', padx=(0, 20))
        type_dropdown.bind('<<ComboboxSelected>>', self.on_type_change)

        ttk.Label(mode_frame, text="Select Study Mode:").grid(
            row=0, column=2, padx=(0, 10)
        )

        # Setup mode selector
        self.mode_var = tk.StringVar(value="First Declension (μουσα)")
        
        # Define noun and adjective modes
        self.noun_modes = [
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
        
        self.adjective_modes = [
            "Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)",
            "Three-termination Golden (χρύσεος, χρυσέα, χρύσεον)",
            "Two-termination Unjust (ἄδικος, ἄδικον)",
            "Three-termination Great (μέγας, μεγάλη, μέγα)",
            "Three-termination Much (πολύς, πολλή, πολύ)",
            "Two-termination True (ἀληθής, ἀληθές)",
            "Three-termination Sweet (ἡδύς, ἡδεῖα, ἡδύ)",
            "Three-termination Wretched (τάλας, τάλαινα, τάλαν)",
            "Three-termination Stopping (παύων, παύουσα, παῦον)",
            "Three-termination All (πᾶς, πᾶσα, πᾶν)",
            "Three-termination Having stopped (παύσας, παύσασα, παῦσαν)",
            "Three-termination Graceful (χαρίεις, χαρίεσσα, χαρίεν)",
            "Three-termination Having been stopped (παυσθείς, παυσθεῖσα, παυσθέν)",
            "Three-termination Having stopped perfect (πεπαυκώς, πεπαυκυῖα, πεπαυκός)"
        ]
        
        self.pronoun_modes = [
            "Personal I (ἐγώ)",
            "Personal You (σύ)", 
            "Personal Third Person (αὐτός, αὐτή, αὐτό)",
            "Demonstrative This (οὗτος, αὕτη, τοῦτο)",
            "Relative Who/Which (ὅς, ἥ, ὅ)",
            "Interrogative Who/What (τίς, τί)",
            "Indefinite Someone/Something (τις, τι)"
        ]
        
        self.verb_modes = [
            "Present Indicative Active - Release (λύω)",
            "Present Indicative Active - To Be (εἰμί)",
            "Present Indicative Active - Love (φιλέω)",
            "Present Indicative Active - Honor (τιμάω)",
            "Present Indicative Active - Make Clear (δηλόω)",
            "Present Indicative Active - Throw (βάλλω)",
            "Present Indicative Active - Give (δίδωμι)",
            "Present Indicative Active - Place (τίθημι)",
            "Present Indicative Active - Stand (ἵστημι)",
            "Present Indicative Active - Know (οἶδα)",
            "Present Indicative Active - Go (εἶμι)",
            "Present Indicative Active - Say (φημί)",
            "Present Indicative Active - Send (ἵημι)"
        ]
        
        # Start with noun modes
        self.modes = self.noun_modes.copy()

        # Setup mode selector with clean styling
        self.mode_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=self.modes,
            font=('Times New Roman', 12),
            width=40
        )
        self.mode_dropdown.grid(row=0, column=3, sticky='ew', padx=10)
        self.mode_dropdown.state(['readonly'])
        self.mode_dropdown.bind('<<ComboboxSelected>>', self.on_mode_change)

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
        elif "ἀγαθός" in mode:
            word = "ἀγαθός, ἀγαθή, ἀγαθόν"
        elif "χρύσεος" in mode:
            word = "χρύσεος, χρυσέα, χρύσεον"
        elif "ἄδικος" in mode:
            word = "ἄδικος, ἄδικον"
        elif "μέγας" in mode:
            word = "μέγας, μεγάλη, μέγα"
        elif "πολύς" in mode:
            word = "πολύς, πολλή, πολύ"
        elif "ἀληθής" in mode:
            word = "ἀληθής, ἀληθές"
        elif "ἡδύς" in mode:
            word = "ἡδύς, ἡδεῖα, ἡδύ"
        elif "τάλας" in mode:
            word = "τάλας, τάλαινα, τάλαν"
        elif "παύων" in mode:
            word = "παύων, παύουσα, παῦον"
        elif "πᾶς" in mode:
            word = "πᾶς, πᾶσα, πᾶν"
        elif "παύσας" in mode:
            word = "παύσας, παύσασα, παῦσαν"
        elif "χαρίεις" in mode:
            word = "χαρίεις, χαρίεσσα, χαρίεν"
        elif "παυσθείς" in mode:
            word = "παυσθείς, παυσθεῖσα, παυσθέν"
        elif "πεπαυκώς" in mode:
            word = "πεπαυκώς, πεπαυκυῖα, πεπαυκός"
        elif "ἐγώ" in mode:
            word = "ἐγώ"
        elif "σύ" in mode:
            word = "σύ"
        elif "αὐτός" in mode:
            word = "αὐτός, αὐτή, αὐτό"
        elif "οὗτος" in mode:
            word = "οὗτος, αὕτη, τοῦτο"
        elif "ὅς, ἥ, ὅ" in mode:
            word = "ὅς, ἥ, ὅ"
        elif "τίς, τί" in mode:
            word = "τίς, τί"
        elif "τις, τι" in mode:
            word = "τις, τι"
        elif "λύω" in mode:
            word = "λύω"
        elif "εἰμί" in mode:
            word = "εἰμί"
        elif "φιλέω" in mode:
            word = "φιλέω"
        elif "τιμάω" in mode:
            word = "τιμάω"
        elif "δηλόω" in mode:
            word = "δηλόω"
        elif "βάλλω" in mode:
            word = "βάλλω"
        elif "δίδωμι" in mode:
            word = "δίδωμι"
        elif "τίθημι" in mode:
            word = "τίθημι"
        elif "ἵστημι" in mode:
            word = "ἵστημι"
        elif "οἶδα" in mode:
            word = "οἶδα"
        elif "εἶμι" in mode:
            word = "εἶμι"
        elif "φημί" in mode:
            word = "φημί"
        elif "ἵημι" in mode:
            word = "ἵημι"
        else:
            word = "—"
        
        self.word_label.config(text=word)

    def create_declension_table(self):
        """Create the declension table with input fields for each case."""
        if self.table_frame:
            self.table_frame.destroy()
            
        self.table_frame = ttk.Frame(self.main_frame)
        self.table_frame.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(20, 10))
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return

        # Check if this is an adjective, noun, pronoun, or verb
        current_type = self.type_var.get()
        
        if current_type == "Adjective":
            self.create_adjective_table(current_paradigm)
        elif current_type == "Pronoun":
            self.create_pronoun_table(current_paradigm)
        elif current_type == "Verb":
            self.create_verb_table(current_paradigm)
        else:
            self.create_noun_table(current_paradigm)
        
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

    def create_noun_table(self, current_paradigm):
        """Create table for noun declensions (2 columns: Singular/Plural)."""
        # Configure grid weights for better expansion
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(1, weight=2)
        self.table_frame.grid_columnconfigure(2, weight=2)

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

        # Create input fields for each case with better spacing (British order)
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
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
            entry_sg.bind('<Left>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'left'))
            entry_sg.bind('<Right>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'right'))

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
            entry_pl.bind('<Left>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'left'))
            entry_pl.bind('<Right>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'right'))

            # Error label for plural
            error_label_pl = ttk.Label(
                self.table_frame,
                text="❌",
                foreground='red'
            )
            error_label_pl.grid(row=i, column=2, sticky='e', padx=15)
            self.error_labels[f"{case}_pl"] = error_label_pl
            error_label_pl.grid_remove()

    def create_adjective_table(self, current_paradigm):
        """Create table for adjective declensions (2 or 3 genders based on type)."""
        # Determine if this is a 2-termination or 3-termination adjective
        adjective_type = current_paradigm.get("type", "")
        is_two_termination = adjective_type == "adjective_2termination"
        
        if is_two_termination:
            # 2-termination: Masculine/Feminine + Neuter (4 columns total)
            self.table_frame.grid_columnconfigure(0, weight=1)  # Case column
            for i in range(1, 5):  # Gender columns
                self.table_frame.grid_columnconfigure(i, weight=2)

            # Main headers
            ttk.Label(
                self.table_frame,
                text="",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=0, padx=10, pady=15, sticky='e')
            
            ttk.Label(
                self.table_frame,
                text="Masculine/Feminine",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=1, columnspan=2, padx=10, pady=15)
            
            ttk.Label(
                self.table_frame,
                text="Neuter",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=3, columnspan=2, padx=10, pady=15)

            # Sub-headers (Singular/Plural)
            for i, header in enumerate(["Sg.", "Pl.", "Sg.", "Pl."]):
                ttk.Label(
                    self.table_frame,
                    text=header,
                    font=('Arial', 12)
                ).grid(row=1, column=i + 1, padx=5, pady=5)

            # Create input fields for each case
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for i, case in enumerate(cases, 2):  # Start from row 2
                # Case label
                ttk.Label(
                    self.table_frame,
                    text=case,
                    font=('Arial', 12, 'bold')
                ).grid(row=i, column=0, padx=10, pady=8, sticky=tk.E)

                # Masculine/Feminine columns (use masculine data since they're identical)
                for j, number in enumerate(["sg", "pl"]):
                    entry = tk.Entry(
                        self.table_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=i, column=j + 1, padx=5, pady=8, sticky='ew')
                    entry_key = f"{case}_masculine_{number}"  # Use masculine data
                    self.entries[entry_key] = entry
                    entry.bind('<Key>', self.handle_key_press)
                    
                    # Bind navigation events
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: self.clear_error(k))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))
                    entry.bind('<Left>', lambda e, k=entry_key: self.handle_arrow(e, k, 'left'))
                    entry.bind('<Right>', lambda e, k=entry_key: self.handle_arrow(e, k, 'right'))

                    # Error label
                    error_label = ttk.Label(
                        self.table_frame,
                        text="❌",
                        foreground='red'
                    )
                    error_label.grid(row=i, column=j + 1, sticky='ne', padx=5)
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()

                # Neuter columns
                for j, number in enumerate(["sg", "pl"]):
                    entry = tk.Entry(
                        self.table_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=i, column=j + 3, padx=5, pady=8, sticky='ew')
                    entry_key = f"{case}_neuter_{number}"
                    self.entries[entry_key] = entry
                    entry.bind('<Key>', self.handle_key_press)
                    
                    # Bind navigation events
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: self.clear_error(k))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))
                    entry.bind('<Left>', lambda e, k=entry_key: self.handle_arrow(e, k, 'left'))
                    entry.bind('<Right>', lambda e, k=entry_key: self.handle_arrow(e, k, 'right'))

                    # Error label
                    error_label = ttk.Label(
                        self.table_frame,
                        text="❌",
                        foreground='red'
                    )
                    error_label.grid(row=i, column=j + 3, sticky='ne', padx=5)
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()
        else:
            # 3-termination: Masculine + Feminine + Neuter (7 columns total)
            self.table_frame.grid_columnconfigure(0, weight=1)  # Case column
            for i in range(1, 7):  # Gender columns and spacers
                self.table_frame.grid_columnconfigure(i, weight=2)

            # Main headers
            ttk.Label(
                self.table_frame,
                text="",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=0, padx=10, pady=15, sticky='e')
            
            ttk.Label(
                self.table_frame,
                text="Masculine",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=1, columnspan=2, padx=10, pady=15)
            
            ttk.Label(
                self.table_frame,
                text="Feminine", 
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=3, columnspan=2, padx=10, pady=15)
            
            ttk.Label(
                self.table_frame,
                text="Neuter",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=5, columnspan=2, padx=10, pady=15)

            # Sub-headers (Singular/Plural for each gender)
            genders = ['masculine', 'feminine', 'neuter']
            for i, gender in enumerate(genders):
                base_col = 1 + i * 2
                ttk.Label(
                    self.table_frame,
                    text="Sg.",
                    font=('Arial', 12)
                ).grid(row=1, column=base_col, padx=5, pady=5)
                
                ttk.Label(
                    self.table_frame,
                    text="Pl.",
                    font=('Arial', 12)
                ).grid(row=1, column=base_col + 1, padx=5, pady=5)

            # Create input fields for each case and gender
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for i, case in enumerate(cases, 2):  # Start from row 2
                # Case label
                ttk.Label(
                    self.table_frame,
                    text=case,
                    font=('Arial', 12, 'bold')
                ).grid(row=i, column=0, padx=10, pady=8, sticky=tk.E)

                # Create entries for each gender and number
                for j, gender in enumerate(genders):
                    base_col = 1 + j * 2
                    
                    # Singular entry
                    entry_sg = tk.Entry(
                        self.table_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1
                    )
                    entry_sg.grid(row=i, column=base_col, padx=5, pady=8, sticky='ew')
                    entry_key_sg = f"{case}_{gender}_sg"
                    self.entries[entry_key_sg] = entry_sg
                    entry_sg.bind('<Key>', self.handle_key_press)
                    
                    # Bind navigation events
                    entry_sg.bind('<KeyRelease>', lambda e, k=entry_key_sg: self.clear_error(k))
                    entry_sg.bind('<Return>', lambda e, k=entry_key_sg: self.handle_enter(e, k))
                    entry_sg.bind('<Up>', lambda e, k=entry_key_sg: self.handle_arrow(e, k, 'up'))
                    entry_sg.bind('<Down>', lambda e, k=entry_key_sg: self.handle_arrow(e, k, 'down'))
                    entry_sg.bind('<Left>', lambda e, k=entry_key_sg: self.handle_arrow(e, k, 'left'))
                    entry_sg.bind('<Right>', lambda e, k=entry_key_sg: self.handle_arrow(e, k, 'right'))

                    # Error label for singular
                    error_label_sg = ttk.Label(
                        self.table_frame,
                        text="❌",
                        foreground='red'
                    )
                    error_label_sg.grid(row=i, column=base_col, sticky='ne', padx=5)
                    self.error_labels[entry_key_sg] = error_label_sg
                    error_label_sg.grid_remove()

                    # Plural entry
                    entry_pl = tk.Entry(
                        self.table_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1
                    )
                    entry_pl.grid(row=i, column=base_col + 1, padx=5, pady=8, sticky='ew')
                    entry_key_pl = f"{case}_{gender}_pl"
                    self.entries[entry_key_pl] = entry_pl
                    entry_pl.bind('<Key>', self.handle_key_press)
                    
                    # Bind navigation events
                    entry_pl.bind('<KeyRelease>', lambda e, k=entry_key_pl: self.clear_error(k))
                    entry_pl.bind('<Return>', lambda e, k=entry_key_pl: self.handle_enter(e, k))
                    entry_pl.bind('<Up>', lambda e, k=entry_key_pl: self.handle_arrow(e, k, 'up'))
                    entry_pl.bind('<Down>', lambda e, k=entry_key_pl: self.handle_arrow(e, k, 'down'))
                    entry_pl.bind('<Left>', lambda e, k=entry_key_pl: self.handle_arrow(e, k, 'left'))
                    entry_pl.bind('<Right>', lambda e, k=entry_key_pl: self.handle_arrow(e, k, 'right'))

                    # Error label for plural
                    error_label_pl = ttk.Label(
                        self.table_frame,
                        text="❌",
                        foreground='red'
                    )
                    error_label_pl.grid(row=i, column=base_col + 1, sticky='ne', padx=5)
                    self.error_labels[entry_key_pl] = error_label_pl
                    error_label_pl.grid_remove()

    def create_pronoun_table(self, current_paradigm):
        """Create the pronoun table with appropriate layout based on pronoun type."""
        mode = self.mode_var.get()
        
        # Determine layout based on pronoun type
        if "Personal I" in mode or "Personal You" in mode:
            # Personal pronouns ἐγώ and σύ use noun-style layout (Singular / Plural)
            self.create_personal_pronoun_table(current_paradigm)
        else:
            # Other pronouns use adjective-style layout (Masculine / Feminine / Neuter)
            self.create_gender_pronoun_table(current_paradigm)
    
    def create_personal_pronoun_table(self, current_paradigm):
        """Create table for personal pronouns (ἐγώ, σύ) - similar to noun layout."""
        self.table_frame.grid_columnconfigure(0, weight=1)  # Case column
        self.table_frame.grid_columnconfigure(1, weight=1)  # Singular column
        self.table_frame.grid_columnconfigure(2, weight=1)  # Plural column

        # Headers
        ttk.Label(
            self.table_frame,
            text="Case",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, padx=10, pady=10)

        ttk.Label(
            self.table_frame,
            text="Singular",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(
            self.table_frame,
            text="Plural",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=2, padx=10, pady=10)

        # Create input fields for each case
        cases = ["Nominative", "Accusative", "Genitive", "Dative"]
        for i, case in enumerate(cases, 1):
            # Case label
            ttk.Label(
                self.table_frame,
                text=case,
                font=('Arial', 12, 'bold')
            ).grid(row=i, column=0, padx=10, pady=8, sticky=tk.E)

            # Singular and Plural entries
            for j, number in enumerate(["sg", "pl"], 1):
                entry_key = f"{case}_{number}"
                
                # Check if this form exists in the paradigm
                form_exists = entry_key in current_paradigm
                
                if form_exists:
                    # Create a frame to hold both entry and error label
                    entry_frame = tk.Frame(self.table_frame)
                    entry_frame.grid(row=i, column=j, padx=5, pady=8, sticky='ew')
                    entry_frame.grid_columnconfigure(0, weight=1)
                    
                    # Create the entry in the frame
                    entry = tk.Entry(
                        entry_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=0, column=0, sticky='ew')
                    
                    self.entries[entry_key] = entry
                    entry.bind('<Key>', self.handle_key_press)

                    # Bind navigation events
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: self.clear_error(k))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))
                    entry.bind('<Left>', lambda e, k=entry_key: self.handle_arrow(e, k, 'left'))
                    entry.bind('<Right>', lambda e, k=entry_key: self.handle_arrow(e, k, 'right'))

                    # Create error label in the same frame
                    error_label = ttk.Label(
                        entry_frame,
                        text="❌",
                        foreground='red'
                    )
                    error_label.grid(row=0, column=1, sticky='e', padx=(2, 0))
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()  # Hide initially
                else:
                    # Grey out missing forms - grid directly to table
                    entry = tk.Entry(
                        self.table_frame,
                        width=18,
                        font=('Times New Roman', 12),
                        relief='solid',
                        borderwidth=1,
                        state='disabled',
                        disabledbackground='#f0f0f0'
                    )
                    entry.grid(row=i, column=j, padx=5, pady=8, sticky='ew')

    def create_gender_pronoun_table(self, current_paradigm):
        """Create table for pronouns with gender forms (αὐτός, οὗτος, ὅς, etc.)."""
        # Similar to 3-termination adjectives but account for missing forms
        self.table_frame.grid_columnconfigure(0, weight=1)  # Case column
        for i in range(1, 7):  # Gender columns (1-6)
            self.table_frame.grid_columnconfigure(i, weight=1)

        # Headers
        ttk.Label(
            self.table_frame,
            text="Case",
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, padx=10, pady=10)

        headers = ["Masculine Sg", "Masculine Pl", "Feminine Sg", "Feminine Pl", "Neuter Sg", "Neuter Pl"]
        for i, header in enumerate(headers):
            ttk.Label(
                self.table_frame,
                text=header,
                font=('Arial', 12)
            ).grid(row=0, column=i + 1, padx=5, pady=5)

        # Create input fields for each case
        cases = ["Nominative", "Accusative", "Genitive", "Dative"]
        genders = ["masculine", "feminine", "neuter"]
        
        for i, case in enumerate(cases, 1):
            # Case label
            ttk.Label(
                self.table_frame,
                text=case,
                font=('Arial', 12, 'bold')
            ).grid(row=i, column=0, padx=10, pady=8, sticky=tk.E)

            # Create entries for each gender and number
            for j, gender in enumerate(genders):
                base_col = 1 + j * 2
                
                for k, number in enumerate(["sg", "pl"]):
                    entry_key = f"{case}_{gender}_{number}"
                    col = base_col + k
                    
                    # Check if this form exists in the paradigm
                    form_exists = (gender in current_paradigm and 
                                 f"{case}_{number}" in current_paradigm[gender])
                    
                    if form_exists:
                        # Create a frame to hold both entry and error label
                        entry_frame = tk.Frame(self.table_frame)
                        entry_frame.grid(row=i, column=col, padx=5, pady=8, sticky='ew')
                        entry_frame.grid_columnconfigure(0, weight=1)
                        
                        # Create the entry in the frame
                        entry = tk.Entry(
                            entry_frame,
                            width=18,
                            font=('Times New Roman', 12),
                            relief='solid',
                            borderwidth=1
                        )
                        entry.grid(row=0, column=0, sticky='ew')
                        
                        self.entries[entry_key] = entry
                        entry.bind('<Key>', self.handle_key_press)

                        # Bind navigation events
                        entry.bind('<KeyRelease>', lambda e, k=entry_key: self.clear_error(k))
                        entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                        entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                        entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))
                        entry.bind('<Left>', lambda e, k=entry_key: self.handle_arrow(e, k, 'left'))
                        entry.bind('<Right>', lambda e, k=entry_key: self.handle_arrow(e, k, 'right'))

                        # Create error label in the same frame
                        error_label = ttk.Label(
                            entry_frame,
                            text="❌",
                            foreground='red'
                        )
                        error_label.grid(row=0, column=1, sticky='e', padx=(2, 0))
                        self.error_labels[entry_key] = error_label
                        error_label.grid_remove()  # Hide initially
                    else:
                        # Grey out missing forms - grid directly to table
                        entry = tk.Entry(
                            self.table_frame,
                            width=18,
                            font=('Times New Roman', 12),
                            relief='solid',
                            borderwidth=1,
                            state='disabled',
                            disabledbackground='#f0f0f0'
                        )
                        entry.grid(row=i, column=col, padx=5, pady=8, sticky='ew')

    def create_verb_table(self, current_paradigm):
        """Create the verb conjugation table with input fields for each person/number."""
        
        # Add verb form selectors at the top
        selectors_frame = ttk.Frame(self.table_frame)
        selectors_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        selectors_frame.grid_columnconfigure(0, weight=1)
        selectors_frame.grid_columnconfigure(1, weight=1)
        selectors_frame.grid_columnconfigure(2, weight=1)
        
        # Tense selector
        ttk.Label(selectors_frame, text="Tense:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 5))
        
        # Preserve existing tense selection or default to "Present"
        current_tense = getattr(self, 'tense_var', None)
        try:
            tense_value = current_tense.get() if current_tense else "Present"
        except:
            tense_value = "Present"
        
        # Determine available tenses based on current verb
        mode = self.mode_var.get()
        if "λύω" in mode or "φιλέω" in mode or "τιμάω" in mode or "δηλόω" in mode or "βάλλω" in mode or "δίδωμι" in mode or "τίθημι" in mode or "ἵστημι" in mode or "φημί" in mode or "ἵημι" in mode:
            available_tenses = ["Present", "Imperfect", "Aorist", "Future"]
        elif "εἰμί" in mode:
            available_tenses = ["Present", "Imperfect", "Future"]
            # If user had Aorist selected but switched to εἰμί, default to Present
            if tense_value == "Aorist":
                tense_value = "Present"
        elif "οἶδα" in mode:
            available_tenses = ["Present", "Imperfect"]
            # οἶδα is a perfect with present meaning, limited forms
            if tense_value in ["Aorist", "Future"]:
                tense_value = "Present"
        elif "εἶμι" in mode:
            available_tenses = ["Present", "Imperfect", "Future"]
            # εἶμι (go) has no aorist
            if tense_value == "Aorist":
                tense_value = "Present"
        else:
            available_tenses = ["Present", "Imperfect", "Aorist", "Future"]
        
        self.tense_var = tk.StringVar(value=tense_value)
        
        self.tense_dropdown = ttk.Combobox(
            selectors_frame,
            textvariable=self.tense_var,
            values=available_tenses,
            state="readonly",
            width=12,
            font=('Arial', 10)
        )
        self.tense_dropdown.grid(row=1, column=0, sticky='ew', padx=(0, 10))
        self.tense_dropdown.bind('<<ComboboxSelected>>', self.on_verb_form_change)
        
        # Voice selector
        ttk.Label(selectors_frame, text="Voice:", font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=(0, 5))
        
        # Preserve existing voice selection or default to "Active"
        current_voice = getattr(self, 'voice_var', None)
        try:
            voice_value = current_voice.get() if current_voice else "Active"
        except:
            voice_value = "Active"
        
        # Determine available voices based on current verb
        if "εἰμί" in mode or "εἶμι" in mode:
            available_voices = ["Active"]
            # If user had Middle/Passive selected but switched to εἰμί/εἶμι, default to Active
            if voice_value in ["Middle", "Passive"]:
                voice_value = "Active"
        else:
            available_voices = ["Active", "Middle", "Passive"]
        
        self.voice_var = tk.StringVar(value=voice_value)
        
        self.voice_dropdown = ttk.Combobox(
            selectors_frame,
            textvariable=self.voice_var,
            values=available_voices,
            state="readonly",
            width=12,
            font=('Arial', 10)
        )
        self.voice_dropdown.grid(row=1, column=1, sticky='ew', padx=(0, 10))
        self.voice_dropdown.bind('<<ComboboxSelected>>', self.on_verb_form_change)
        
        # Mood selector
        ttk.Label(selectors_frame, text="Mood:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=(0, 5))
        
        # Preserve existing mood selection or default to "Indicative"
        current_mood = getattr(self, 'mood_var', None)
        try:
            mood_value = current_mood.get() if current_mood else "Indicative"
        except:
            mood_value = "Indicative"
        
        # Determine available moods based on current tense
        tense_value = self.tense_var.get()
        if tense_value == "Present":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative"]
        elif tense_value == "Imperfect":
            available_moods = ["Indicative", "Optative"]
        elif tense_value == "Aorist":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative"]
        elif tense_value == "Future":
            available_moods = ["Indicative", "Optative"]
        else:
            available_moods = ["Indicative"]
        
        # If current mood is not available in this tense, default to Indicative
        if mood_value not in available_moods:
            mood_value = "Indicative"
        
        self.mood_var = tk.StringVar(value=mood_value)
        self.mood_dropdown = ttk.Combobox(
            selectors_frame,
            textvariable=self.mood_var,
            values=available_moods,
            state="readonly",
            width=12,
            font=('Arial', 10)
        )
        self.mood_dropdown.grid(row=1, column=2, sticky='ew')
        self.mood_dropdown.bind('<<ComboboxSelected>>', self.on_verb_form_change)
        
        # Configure main table columns
        self.table_frame.grid_columnconfigure(0, weight=1)  # Person column
        self.table_frame.grid_columnconfigure(1, weight=1)  # Singular column  
        self.table_frame.grid_columnconfigure(2, weight=1)  # Plural column

        # Headers (shifted down to row 2)
        ttk.Label(
            self.table_frame,
            text="Person",
            font=('Arial', 12, 'bold')
        ).grid(row=2, column=0, padx=10, pady=10)

        ttk.Label(
            self.table_frame,
            text="Singular",
            font=('Arial', 12, 'bold')
        ).grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(
            self.table_frame,
            text="Plural",
            font=('Arial', 12, 'bold')
        ).grid(row=2, column=2, padx=10, pady=10)

        # Create input fields for each person (shifted down to start at row 3)
        persons = ["1st", "2nd", "3rd"]
        for i, person in enumerate(persons, 3):
            # Person label
            ttk.Label(
                self.table_frame,
                text=person.replace("st", "st").replace("nd", "nd").replace("rd", "rd"),
                font=('Arial', 12, 'bold')
            ).grid(row=i, column=0, padx=10, pady=8)

            # Singular and plural entry fields for this person
            for j, number in enumerate(["sg", "pl"], 1):
                # Create a frame to hold the entry and error label
                entry_frame = tk.Frame(self.table_frame)
                entry_frame.grid(row=i, column=j, padx=5, pady=8, sticky='ew')
                entry_frame.grid_columnconfigure(0, weight=1)

                entry_key = f"{person}_{number}"
                entry = tk.Entry(
                    entry_frame,
                    width=18,
                    font=('Times New Roman', 12),
                    relief='solid',
                    borderwidth=1
                )
                entry.grid(row=0, column=0, sticky='ew')
                entry.bind('<Key>', self.handle_key_press)
                entry.bind('<Return>', lambda e, key=entry_key: self.handle_enter(e, key))
                entry.bind('<Up>', lambda e, key=entry_key: self.handle_arrow(e, key, 'up'))
                entry.bind('<Down>', lambda e, key=entry_key: self.handle_arrow(e, key, 'down'))
                entry.bind('<Left>', lambda e, key=entry_key: self.handle_arrow(e, key, 'left'))
                entry.bind('<Right>', lambda e, key=entry_key: self.handle_arrow(e, key, 'right'))
                self.entries[entry_key] = entry

                # Create error label positioned to the right of the entry
                error_label = ttk.Label(
                    entry_frame,
                    text="X",
                    foreground='red',
                    font=('Arial', 10, 'bold')
                )
                error_label.grid(row=0, column=1, padx=(5, 0))
                error_label.grid_remove()  # Hide initially
                self.error_labels[entry_key] = error_label

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
    
    def remove_accents(self, text):
        """Remove accents from Greek text while preserving breathing marks and iota subscripts."""
        if not text:
            return text
            
        # Dictionary to map accented characters to their unaccented equivalents
        # while preserving breathing marks and iota subscripts
        accent_map = {
            # Alpha variations
            'ά': 'α', 'ὰ': 'α', 'ᾶ': 'α',
            'ἄ': 'ἀ', 'ἂ': 'ἀ', 'ἆ': 'ἀ',  # smooth breathing variants
            'ἅ': 'ἁ', 'ἃ': 'ἁ', 'ἇ': 'ἁ',  # rough breathing variants
            'ᾴ': 'ᾳ', 'ᾲ': 'ᾳ', 'ᾷ': 'ᾳ',  # iota subscript variants
            'ᾄ': 'ᾀ', 'ᾂ': 'ᾀ', 'ᾆ': 'ᾀ',  # smooth breathing + iota subscript
            'ᾅ': 'ᾁ', 'ᾃ': 'ᾁ', 'ᾇ': 'ᾁ',  # rough breathing + iota subscript
            
            # Epsilon variations
            'έ': 'ε', 'ὲ': 'ε',
            'ἔ': 'ἐ', 'ἒ': 'ἐ',  # smooth breathing variants
            'ἕ': 'ἑ', 'ἓ': 'ἑ',  # rough breathing variants
            
            # Eta variations
            'ή': 'η', 'ὴ': 'η', 'ῆ': 'η',
            'ἤ': 'ἠ', 'ἢ': 'ἠ', 'ἦ': 'ἠ',  # smooth breathing variants
            'ἥ': 'ἡ', 'ἣ': 'ἡ', 'ἧ': 'ἡ',  # rough breathing variants
            'ῄ': 'ῃ', 'ῂ': 'ῃ', 'ῇ': 'ῃ',  # iota subscript variants
            'ᾔ': 'ᾐ', 'ᾒ': 'ᾐ', 'ᾖ': 'ᾐ',  # smooth breathing + iota subscript
            'ᾕ': 'ᾑ', 'ᾓ': 'ᾑ', 'ᾗ': 'ᾑ',  # rough breathing + iota subscript
            
            # Iota variations
            'ί': 'ι', 'ὶ': 'ι', 'ῖ': 'ι',
            'ἴ': 'ἰ', 'ἲ': 'ἰ', 'ἶ': 'ἰ',  # smooth breathing variants
            'ἵ': 'ἱ', 'ἳ': 'ἱ', 'ἷ': 'ἱ',  # rough breathing variants
            'ϊ': 'ι', 'ΐ': 'ι', 'ῒ': 'ι', 'ῗ': 'ι',  # diaeresis variants
            
            # Omicron variations
            'ό': 'ο', 'ὸ': 'ο',
            'ὄ': 'ὀ', 'ὂ': 'ὀ',  # smooth breathing variants
            'ὅ': 'ὁ', 'ὃ': 'ὁ',  # rough breathing variants
            
            # Upsilon variations
            'ύ': 'υ', 'ὺ': 'υ', 'ῦ': 'υ',
            'ὔ': 'ὐ', 'ὒ': 'ὐ', 'ὖ': 'ὐ',  # smooth breathing variants
            'ὕ': 'ὑ', 'ὓ': 'ὑ', 'ὗ': 'ὑ',  # rough breathing variants
            'ϋ': 'υ', 'ΰ': 'υ', 'ῢ': 'υ', 'ῧ': 'υ',  # diaeresis variants
            
            # Omega variations
            'ώ': 'ω', 'ὼ': 'ω', 'ῶ': 'ω',
            'ὤ': 'ὠ', 'ὢ': 'ὠ', 'ὦ': 'ὠ',  # smooth breathing variants
            'ὥ': 'ὡ', 'ὣ': 'ὡ', 'ὧ': 'ὡ',  # rough breathing variants
            'ῴ': 'ῳ', 'ῲ': 'ῳ', 'ῷ': 'ῳ',  # iota subscript variants
            'ᾤ': 'ᾠ', 'ᾢ': 'ᾠ', 'ᾦ': 'ᾠ',  # smooth breathing + iota subscript
            'ᾥ': 'ᾡ', 'ᾣ': 'ᾡ', 'ᾧ': 'ᾡ',  # rough breathing + iota subscript
        }
        
        result = ""
        for char in text:
            result += accent_map.get(char, char)
        
        return result

    def on_type_change(self, event):
        """Handle type change between Noun, Adjective, Pronoun, and Verb."""
        current_type = self.type_var.get()
        
        if current_type == "Noun":
            self.modes = self.noun_modes.copy()
            self.mode_var.set("First Declension (μουσα)")
        elif current_type == "Adjective":
            self.modes = self.adjective_modes.copy()
            self.mode_var.set("Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)")
        elif current_type == "Pronoun":
            self.modes = self.pronoun_modes.copy()
            self.mode_var.set("Personal I (ἐγώ)")
        else:  # Verb
            self.modes = self.verb_modes.copy()
            self.mode_var.set("Present Indicative Active - Release (λύω)")
        
        # Update the dropdown values
        self.mode_dropdown['values'] = self.modes
        
        # Recreate the table for the new type
        self.reset_table()
        self.update_word_display()

    def on_mode_change(self, event):
        """Handle mode change in the dropdown."""
        self.reset_table()
        self.update_word_display()

    def on_verb_form_change(self, event):
        """Handle changes to verb tense, voice, or mood selectors."""
        if self.type_var.get() == "Verb":
            self.reset_table()
            self.update_word_display()

    def get_current_paradigm(self):
        """Get the currently selected paradigm."""
        mode = self.mode_var.get()
        current_type = self.type_var.get()
        
        # For verbs, use dropdown selections to determine paradigm
        if current_type == "Verb":
            # Get the base verb from the mode
            if "λύω" in mode:
                verb_base = "luo"
            elif "εἰμί" in mode:
                verb_base = "eimi"
            elif "φιλέω" in mode:
                verb_base = "phileo"
            elif "τιμάω" in mode:
                verb_base = "timao"
            elif "δηλόω" in mode:
                verb_base = "deloo"
            elif "βάλλω" in mode:
                verb_base = "ballo"
            elif "δίδωμι" in mode:
                verb_base = "didomi"
            elif "τίθημι" in mode:
                verb_base = "tithemi"
            elif "ἵστημι" in mode:
                verb_base = "histemi"
            elif "οἶδα" in mode:
                verb_base = "oida"
            elif "εἶμι" in mode:
                verb_base = "eimi_go"
            elif "φημί" in mode:
                verb_base = "phemi"
            elif "ἵημι" in mode:
                verb_base = "hiemi"
            else:
                return None
            
            # Get tense, voice, mood from dropdowns (if they exist)
            tense = getattr(self, 'tense_var', None)
            voice = getattr(self, 'voice_var', None)
            mood = getattr(self, 'mood_var', None)
            
            if tense and voice and mood:
                tense_val = tense.get().lower()
                voice_val = voice.get().lower()
                mood_val = mood.get().lower()
                
                # Map tense names to paradigm keys
                tense_map = {
                    "present": "pres",
                    "imperfect": "impf",
                    "aorist": "aor",
                    "future": "fut"
                }
                tense_key = tense_map.get(tense_val, tense_val)
                
                # Map mood names to paradigm keys
                mood_map = {
                    "indicative": "ind",
                    "subjunctive": "subj",
                    "optative": "opt",
                    "imperative": "imp"
                }
                mood_key = mood_map.get(mood_val, mood_val)
                
                # Map voice names to paradigm keys  
                voice_map = {
                    "active": "act",
                    "middle": "mid",
                    "passive": "pass"
                }
                voice_key = voice_map.get(voice_val, voice_val)
                
                # Construct paradigm key
                paradigm_key = f"{verb_base}_{tense_key}_{mood_key}_{voice_key}"
                return self.paradigms.get(paradigm_key)
            else:
                # Fallback to present indicative active
                paradigm_key = f"{verb_base}_pres_ind_act"
                return self.paradigms.get(paradigm_key)
        
        # For non-verbs, use the existing paradigm map
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
            "Third Declension City (πόλις)": "polis",
            "Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)": "agathos",
            "Three-termination Golden (χρύσεος, χρυσέα, χρύσεον)": "chryseos",
            "Two-termination Unjust (ἄδικος, ἄδικον)": "adikos",
            "Three-termination Great (μέγας, μεγάλη, μέγα)": "megas",
            "Three-termination Much (πολύς, πολλή, πολύ)": "polys",
            "Two-termination True (ἀληθής, ἀληθές)": "alethes",
            "Three-termination Sweet (ἡδύς, ἡδεῖα, ἡδύ)": "hedys",
            "Three-termination Wretched (τάλας, τάλαινα, τάλαν)": "talas",
            "Three-termination Stopping (παύων, παύουσα, παῦον)": "paon",
            "Three-termination All (πᾶς, πᾶσα, πᾶν)": "pas",
            "Three-termination Having stopped (παύσας, παύσασα, παῦσαν)": "pausas",
            "Three-termination Graceful (χαρίεις, χαρίεσσα, χαρίεν)": "charieis",
            "Three-termination Having been stopped (παυσθείς, παυσθεῖσα, παυσθέν)": "paustheis",
            "Three-termination Having stopped perfect (πεπαυκώς, πεπαυκυῖα, πεπαυκός)": "pepaukos",
            "Personal I (ἐγώ)": "ego",
            "Personal You (σύ)": "sy", 
            "Personal Third Person (αὐτός, αὐτή, αὐτό)": "autos",
            "Demonstrative This (οὗτος, αὕτη, τοῦτο)": "houtos",
            "Relative Who/Which (ὅς, ἥ, ὅ)": "hos",
            "Interrogative Who/What (τίς, τί)": "tis_interrog",
            "Indefinite Someone/Something (τις, τι)": "tis_indef",
            "Present Indicative Active - Release (λύω)": "luo_pres_ind_act",
            "Present Indicative Active - To Be (εἰμί)": "eimi_pres_ind_act"
        }
        
        paradigm_key = paradigm_map.get(mode)
        return self.paradigms.get(paradigm_key) if paradigm_key else None

    def check_answers(self):
        """Check all user inputs against correct answers."""
        # Clear previous error indicators
        for error_label in self.error_labels.values():
            error_label.grid_remove()
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        all_correct = True
        current_type = self.type_var.get()
        
        if current_type == "Adjective":
            # Check adjective answers 
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            
            # Determine which genders to check based on adjective type
            is_two_termination = current_paradigm.get("type") == "adjective_2termination"
            if is_two_termination:
                genders = ["masculine", "neuter"]  # Only check masculine and neuter for 2-termination
            else:
                genders = ["masculine", "feminine", "neuter"]  # Check all three for 3-termination
            
            for case in cases:
                for gender in genders:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{gender}_{number}"
                        
                        if entry_key in self.entries:
                            user_answer = self.entries[entry_key].get().strip()
                            
                            # Navigate to correct answer in nested structure
                            if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                                correct_answer = current_paradigm[gender][f"{case}_{number}"]
                                
                                # Remove accents for comparison
                                user_answer_no_accents = self.remove_accents(user_answer)
                                correct_answer_no_accents = self.remove_accents(correct_answer)
                                
                                if user_answer_no_accents != correct_answer_no_accents:
                                    # Show error indicator
                                    if entry_key in self.error_labels:
                                        self.error_labels[entry_key].grid()
                                    all_correct = False
        elif current_type == "Pronoun":
            # Check pronoun answers (no vocative)
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use simple structure like nouns
                for case in pronoun_cases:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{number}"
                        
                        if entry_key in self.entries:
                            user_answer = self.entries[entry_key].get().strip()
                            correct_answer = current_paradigm.get(entry_key, "")
                            
                            # Remove accents for comparison
                            user_answer_no_accents = self.remove_accents(user_answer)
                            correct_answer_no_accents = self.remove_accents(correct_answer)
                            
                            if user_answer_no_accents != correct_answer_no_accents:
                                # Show error indicator
                                if entry_key in self.error_labels:
                                    self.error_labels[entry_key].grid()
                                all_correct = False
            else:
                # Gender pronouns use structure like adjectives
                genders = ["masculine", "feminine", "neuter"]
                
                for case in pronoun_cases:
                    for gender in genders:
                        for number in ["sg", "pl"]:
                            entry_key = f"{case}_{gender}_{number}"
                            
                            if entry_key in self.entries:
                                user_answer = self.entries[entry_key].get().strip()
                                
                                # Navigate to correct answer in nested structure
                                if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                                    correct_answer = current_paradigm[gender][f"{case}_{number}"]
                                    
                                    # Remove accents for comparison
                                    user_answer_no_accents = self.remove_accents(user_answer)
                                    correct_answer_no_accents = self.remove_accents(correct_answer)
                                    
                                    if user_answer_no_accents != correct_answer_no_accents:
                                        # Show error indicator
                                        if entry_key in self.error_labels:
                                            self.error_labels[entry_key].grid()
                                        all_correct = False
        elif current_type == "Verb":
            # Check verb answers (person/number structure)
            persons = ["1st", "2nd", "3rd"]
            for person in persons:
                for number in ["sg", "pl"]:
                    entry_key = f"{person}_{number}"
                    
                    if entry_key in self.entries:
                        user_answer = self.entries[entry_key].get().strip()
                        correct_answer = current_paradigm.get(entry_key, "")
                        
                        # Remove accents for comparison
                        user_answer_no_accents = self.remove_accents(user_answer)
                        correct_answer_no_accents = self.remove_accents(correct_answer)
                        
                        if user_answer_no_accents != correct_answer_no_accents:
                            # Show error indicator
                            if entry_key in self.error_labels:
                                self.error_labels[entry_key].grid()
                            all_correct = False
        else:
            # Check noun answers (simple structure)
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    
                    if entry_key in self.entries:
                        user_answer = self.entries[entry_key].get().strip()
                        correct_answer = current_paradigm.get(entry_key, "")
                        
                        # Remove accents for comparison
                        user_answer_no_accents = self.remove_accents(user_answer)
                        correct_answer_no_accents = self.remove_accents(correct_answer)
                        
                        if user_answer_no_accents != correct_answer_no_accents:
                            # Show error indicator
                            if entry_key in self.error_labels:
                                self.error_labels[entry_key].grid()
                            all_correct = False
        
        # Show appropriate message
        if all_correct:
            messagebox.showinfo("Results", "🎉 All answers are correct! Well done!")
        else:
            messagebox.showinfo("Results", "Some answers need attention. Check the red X marks.")

    def clear_error(self, entry_key):
        """Clear error indication for an entry."""
        if entry_key in self.entries and entry_key in self.error_labels:
            entry = self.entries[entry_key]
            # Only clear if not in readonly mode (i.e., not marked as correct)
            if entry.cget('state') != 'readonly':
                self.error_labels[entry_key].grid_remove()
                entry.configure(bg='white')

    def reveal_answers(self):
        """Show the correct answers in all fields."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        # Clear error indicators
        for error_label in self.error_labels.values():
            error_label.grid_remove()
        
        current_type = self.type_var.get()
        
        if current_type == "Adjective":
            # Fill adjective answers
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            
            # Determine which genders to fill based on adjective type
            is_two_termination = current_paradigm.get("type") == "adjective_2termination"
            if is_two_termination:
                genders = ["masculine", "neuter"]  # Only fill masculine and neuter for 2-termination
            else:
                genders = ["masculine", "feminine", "neuter"]  # Fill all three for 3-termination
            
            for case in cases:
                for gender in genders:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{gender}_{number}"
                        
                        if entry_key in self.entries and gender in current_paradigm:
                            answer_key = f"{case}_{number}"
                            if answer_key in current_paradigm[gender]:
                                entry = self.entries[entry_key]
                                entry.configure(state='normal')
                                entry.delete(0, tk.END)
                                entry.insert(0, current_paradigm[gender][answer_key])
                                entry.configure(state='readonly', bg='lightgray')
        elif current_type == "Pronoun":
            # Fill pronoun answers (no vocative)
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use simple structure like nouns
                for case in pronoun_cases:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{number}"
                        
                        if entry_key in self.entries and entry_key in current_paradigm:
                            entry = self.entries[entry_key]
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, current_paradigm[entry_key])
                            entry.configure(state='readonly', bg='lightgray')
            else:
                # Gender pronouns use structure like adjectives
                genders = ["masculine", "feminine", "neuter"]
                
                for case in pronoun_cases:
                    for gender in genders:
                        for number in ["sg", "pl"]:
                            entry_key = f"{case}_{gender}_{number}"
                            
                            if entry_key in self.entries and gender in current_paradigm:
                                answer_key = f"{case}_{number}"
                                if answer_key in current_paradigm[gender]:
                                    entry = self.entries[entry_key]
                                    entry.configure(state='normal')
                                    entry.delete(0, tk.END)
                                    entry.insert(0, current_paradigm[gender][answer_key])
                                    entry.configure(state='readonly', bg='lightgray')
        elif current_type == "Verb":
            # Fill verb answers (person/number structure)
            persons = ["1st", "2nd", "3rd"]
            for person in persons:
                for number in ["sg", "pl"]:
                    entry_key = f"{person}_{number}"
                    
                    if entry_key in self.entries and entry_key in current_paradigm:
                        entry = self.entries[entry_key]
                        entry.configure(state='normal')
                        entry.delete(0, tk.END)
                        entry.insert(0, current_paradigm[entry_key])
                        entry.configure(state='readonly', bg='lightgray')
        else:
            # Fill noun answers (simple structure)
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    
                    if entry_key in self.entries and entry_key in current_paradigm:
                        entry = self.entries[entry_key]
                        entry.configure(state='normal')
                        entry.delete(0, tk.END)
                        entry.insert(0, current_paradigm[entry_key])
                        entry.configure(state='readonly', bg='lightgray')

    def reset_table(self):
        """Clear all entries and error indicators."""
        # Reset visual state of existing entries before clearing
        for entry in self.entries.values():
            entry.configure(state='normal')
            entry.configure(bg='white')
            entry.delete(0, tk.END)
        
        # Hide all error indicators
        for error_label in self.error_labels.values():
            error_label.grid_remove()
        
        # Clear dictionaries and recreate the table
        self.entries.clear()
        self.error_labels.clear()
        self.create_declension_table()

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
• Left/Right arrows: Move between singular/plural
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

        # Check if this entry is correct before moving to next
        if self.check_single_entry(current_key):
            self.move_to_next_entry(current_key)

        return "break"

    def check_single_entry(self, entry_key):
        """Check if a single entry is correct and apply visual feedback."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm or entry_key not in self.entries:
            return False
        
        current_type = self.type_var.get()
        user_answer = self.entries[entry_key].get().strip()
        entry = self.entries[entry_key]
        error_label = self.error_labels.get(entry_key)
        
        correct_answer = None
        
        if current_type == "Adjective":
            # Parse adjective entry key: "Case_gender_number"
            parts = entry_key.split('_')
            if len(parts) == 3:
                case, gender, number = parts
                if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                    correct_answer = current_paradigm[gender][f"{case}_{number}"]
        elif current_type == "Pronoun":
            # Handle pronoun entry keys
            mode = self.mode_var.get()
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use "Case_number" format
                if entry_key in current_paradigm:
                    correct_answer = current_paradigm[entry_key]
            else:
                # Gender pronouns use "Case_gender_number" format
                parts = entry_key.split('_')
                if len(parts) == 3:
                    case, gender, number = parts
                    if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                        correct_answer = current_paradigm[gender][f"{case}_{number}"]
        elif current_type == "Verb":
            # Parse verb entry key: "person_number" (e.g., "1st_sg", "3rd_pl")
            if entry_key in current_paradigm:
                correct_answer = current_paradigm[entry_key]
        else:
            # Parse noun entry key: "Case_number"
            if entry_key in current_paradigm:
                correct_answer = current_paradigm[entry_key]
        
        if correct_answer:
            # Remove accents for comparison
            user_clean = self.remove_accents(self.normalize_greek(user_answer))
            correct_clean = self.remove_accents(self.normalize_greek(correct_answer))
            
            is_correct = user_clean.lower() == correct_clean.lower()
            
            if is_correct:
                # Mark as correct with visual feedback
                entry.configure(bg='gold')
                entry.configure(state='readonly')
                if error_label:
                    error_label.grid_remove()
            else:
                # Mark as incorrect
                entry.configure(bg='white')
                entry.configure(state='normal')
                if error_label:
                    error_label.grid()  # Show the error label in its pre-configured position
            
            return is_correct
        
        return False

    def find_next_empty_entry(self, candidates):
        """Find the next empty entry from a list of candidate keys."""
        for key in candidates:
            if key in self.entries:
                entry = self.entries[key]
                # Check if entry is empty and not readonly (not already correct)
                if not entry.get().strip() and str(entry.cget('state')) != 'readonly':
                    return key
        return None

    def move_to_next_entry(self, current_key):
        """Move focus to the next logical entry."""
        current_type = self.type_var.get()
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        
        if current_type == "Adjective":
            # Check if this is 2-termination or 3-termination
            current_paradigm = self.get_current_paradigm()
            is_two_termination = current_paradigm and current_paradigm.get("type") == "adjective_2termination"
            
            # Parse: "Case_gender_number"
            parts = current_key.split('_')
            if len(parts) == 3:
                case, gender, number = parts
                case_idx = cases.index(case)
                
                if is_two_termination:
                    genders = ["masculine", "neuter"]
                else:
                    genders = ["masculine", "feminine", "neuter"]
                
                if gender in genders:
                    gender_idx = genders.index(gender)
                    
                    # Try next case in same gender/number column first (downward movement)
                    if case_idx < len(cases) - 1:
                        candidates = [f"{cases[i]}_{gender}_{number}" for i in range(case_idx + 1, len(cases))]
                        next_key = self.find_next_empty_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we've finished all cases in sg column, move to pl column of same gender
                    if number == "sg":
                        candidates = [f"{cases[i]}_{gender}_pl" for i in range(len(cases))]
                        next_key = self.find_next_empty_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we're in plural and finished all cases, try next gender (start with sg)
                    if gender_idx < len(genders) - 1:
                        for next_gender in genders[gender_idx + 1:]:
                            # Try sg first, then pl for next gender
                            candidates = [f"{cases[i]}_{next_gender}_sg" for i in range(len(cases))]
                            candidates.extend([f"{cases[i]}_{next_gender}_pl" for i in range(len(cases))])
                            next_key = self.find_next_empty_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
                            self.entries[next_key].focus()
                            return
        elif current_type == "Pronoun":
            # Handle pronoun navigation (no vocative)
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use noun-style navigation
                parts = current_key.split('_')
                if len(parts) == 2:
                    case, number = parts
                    case_idx = pronoun_cases.index(case)
                    
                    # Try next case in same number column first (downward movement)
                    if case_idx < len(pronoun_cases) - 1:
                        candidates = [f"{pronoun_cases[i]}_{number}" for i in range(case_idx + 1, len(pronoun_cases))]
                        next_key = self.find_next_empty_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we've finished all cases in sg column, move to pl column
                    if number == "sg":
                        candidates = [f"{pronoun_cases[i]}_pl" for i in range(len(pronoun_cases))]
                        next_key = self.find_next_empty_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
            else:
                # Gender pronouns use adjective-style navigation
                parts = current_key.split('_')
                if len(parts) == 3:
                    case, gender, number = parts
                    case_idx = pronoun_cases.index(case)
                    genders = ["masculine", "feminine", "neuter"]
                    
                    if gender in genders:
                        gender_idx = genders.index(gender)
                        
                        # Try next case in same gender/number column first (downward movement)
                        if case_idx < len(pronoun_cases) - 1:
                            candidates = [f"{pronoun_cases[i]}_{gender}_{number}" for i in range(case_idx + 1, len(pronoun_cases))]
                            next_key = self.find_next_empty_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
                        
                        # If we've finished all cases in sg column, move to pl column of same gender
                        if number == "sg":
                            candidates = [f"{pronoun_cases[i]}_{gender}_pl" for i in range(len(pronoun_cases))]
                            next_key = self.find_next_empty_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
                        
                        # If we're in plural and finished all cases, try next gender (start with sg)
                        if gender_idx < len(genders) - 1:
                            for next_gender in genders[gender_idx + 1:]:
                                candidates = [f"{pronoun_cases[i]}_{next_gender}_sg" for i in range(len(pronoun_cases))]
                                candidates.extend([f"{pronoun_cases[i]}_{next_gender}_pl" for i in range(len(pronoun_cases))])
                                next_key = self.find_next_empty_entry(candidates)
                                if next_key:
                                    self.entries[next_key].focus()
                                    return
        elif current_type == "Verb":
            # Parse: "person_number" (e.g., "1st_sg", "2nd_pl")
            parts = current_key.split('_')
            if len(parts) == 2:
                person, number = parts
                persons = ["1st", "2nd", "3rd"]
                person_idx = persons.index(person)
                
                # Try next person in same number column first (downward movement)
                if person_idx < len(persons) - 1:
                    candidates = [f"{persons[i]}_{number}" for i in range(person_idx + 1, len(persons))]
                    next_key = self.find_next_empty_entry(candidates)
                    if next_key:
                        self.entries[next_key].focus()
                        return
                
                # If we've finished all persons in sg column, move to pl column
                if number == "sg":
                    candidates = [f"{persons[i]}_pl" for i in range(len(persons))]
                    next_key = self.find_next_empty_entry(candidates)
                    if next_key:
                        self.entries[next_key].focus()
                        return
        else:
            # Parse: "Case_number" 
            parts = current_key.split('_')
            if len(parts) == 2:
                case, number = parts
                case_idx = cases.index(case)
                
                # Try next case in same number column first (downward movement)
                if case_idx < len(cases) - 1:
                    candidates = [f"{cases[i]}_{number}" for i in range(case_idx + 1, len(cases))]
                    next_key = self.find_next_empty_entry(candidates)
                    if next_key:
                        self.entries[next_key].focus()
                        return
                
                # If we've finished all cases in sg column, move to pl column
                if number == "sg":
                    candidates = [f"{cases[i]}_pl" for i in range(len(cases))]
                    next_key = self.find_next_empty_entry(candidates)
                    if next_key:
                        self.entries[next_key].focus()
                        return

    def handle_arrow(self, event, current_key, direction):
        """Handle arrow key navigation."""
        current_type = self.type_var.get()
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        
        if current_type == "Adjective":
            # Check if this is 2-termination or 3-termination
            current_paradigm = self.get_current_paradigm()
            is_two_termination = current_paradigm and current_paradigm.get("type") == "adjective_2termination"
            
            # Parse: "Case_gender_number"
            parts = current_key.split('_')
            if len(parts) == 3:
                case, gender, number = parts
                case_idx = cases.index(case)
                
                if is_two_termination:
                    # 2-termination: only masculine and neuter
                    genders = ["masculine", "neuter"]  
                    if gender in genders:
                        gender_idx = genders.index(gender)
                        
                        if direction == 'up' and case_idx > 0:
                            next_key = f"{cases[case_idx - 1]}_{gender}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'down' and case_idx < len(cases) - 1:
                            next_key = f"{cases[case_idx + 1]}_{gender}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'left' and gender_idx > 0:
                            next_key = f"{case}_{genders[gender_idx - 1]}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'right' and gender_idx < len(genders) - 1:
                            next_key = f"{case}_{genders[gender_idx + 1]}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                else:
                    # 3-termination: masculine, feminine, neuter
                    genders = ["masculine", "feminine", "neuter"]
                    gender_idx = genders.index(gender)
                    
                    if direction == 'up' and case_idx > 0:
                        next_key = f"{cases[case_idx - 1]}_{gender}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'down' and case_idx < len(cases) - 1:
                        next_key = f"{cases[case_idx + 1]}_{gender}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'left' and gender_idx > 0:
                        next_key = f"{case}_{genders[gender_idx - 1]}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'right' and gender_idx < len(genders) - 1:
                        next_key = f"{case}_{genders[gender_idx + 1]}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
        elif current_type == "Pronoun":
            # Handle pronoun navigation (no vocative)
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use noun-style navigation
                parts = current_key.split('_')
                if len(parts) == 2:
                    case, number = parts
                    case_idx = pronoun_cases.index(case)
                    
                    if direction == 'up' and case_idx > 0:
                        next_key = f"{pronoun_cases[case_idx - 1]}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'down' and case_idx < len(pronoun_cases) - 1:
                        next_key = f"{pronoun_cases[case_idx + 1]}_{number}"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'left' and number == 'pl':
                        # Move from plural to singular
                        next_key = f"{case}_sg"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
                    elif direction == 'right' and number == 'sg':
                        # Move from singular to plural
                        next_key = f"{case}_pl"
                        if next_key in self.entries:
                            self.entries[next_key].focus()
            else:
                # Gender pronouns use adjective-style navigation
                parts = current_key.split('_')
                if len(parts) == 3:
                    case, gender, number = parts
                    case_idx = pronoun_cases.index(case)
                    genders = ["masculine", "feminine", "neuter"]
                    
                    if gender in genders:
                        gender_idx = genders.index(gender)
                        
                        if direction == 'up' and case_idx > 0:
                            next_key = f"{pronoun_cases[case_idx - 1]}_{gender}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'down' and case_idx < len(pronoun_cases) - 1:
                            next_key = f"{pronoun_cases[case_idx + 1]}_{gender}_{number}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'left':
                            # First try to move from plural to singular in same gender
                            if number == 'pl':
                                next_key = f"{case}_{gender}_sg"
                                if next_key in self.entries:
                                    self.entries[next_key].focus()
                                    return "break"
                            # If that fails or we're in singular, try previous gender with same number
                            if gender_idx > 0:
                                next_key = f"{case}_{genders[gender_idx - 1]}_{number}"
                                if next_key in self.entries:
                                    self.entries[next_key].focus()
                        elif direction == 'right':
                            # First try to move from singular to plural in same gender  
                            if number == 'sg':
                                next_key = f"{case}_{gender}_pl"
                                if next_key in self.entries:
                                    self.entries[next_key].focus()
                                    return "break"
                            # If that fails or we're in plural, try next gender with same number
                            if gender_idx < len(genders) - 1:
                                next_key = f"{case}_{genders[gender_idx + 1]}_{number}"
                                if next_key in self.entries:
                                    self.entries[next_key].focus()
        elif current_type == "Verb":
            # Handle verb navigation (person/number structure)
            parts = current_key.split('_')
            if len(parts) == 2:
                person, number = parts
                persons = ["1st", "2nd", "3rd"]
                person_idx = persons.index(person)
                
                if direction == 'up' and person_idx > 0:
                    next_key = f"{persons[person_idx - 1]}_{number}"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'down' and person_idx < len(persons) - 1:
                    next_key = f"{persons[person_idx + 1]}_{number}"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'left' and number == 'pl':
                    # Move from plural to singular
                    next_key = f"{person}_sg"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'right' and number == 'sg':
                    # Move from singular to plural
                    next_key = f"{person}_pl"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
        else:
            # Parse: "Case_number"
            parts = current_key.split('_')
            if len(parts) == 2:
                case, number = parts
                case_idx = cases.index(case)
                
                if direction == 'up' and case_idx > 0:
                    next_key = f"{cases[case_idx - 1]}_{number}"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'down' and case_idx < len(cases) - 1:
                    next_key = f"{cases[case_idx + 1]}_{number}"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'left' and number == 'pl':
                    # Move from plural to singular
                    next_key = f"{case}_sg"
                    if next_key in self.entries:
                        self.entries[next_key].focus()
                elif direction == 'right' and number == 'sg':
                    # Move from singular to plural
                    next_key = f"{case}_pl"
                    if next_key in self.entries:
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
