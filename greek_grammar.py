import tkinter as tk
from tkinter import ttk, messagebox, font
import json
import unicodedata
import sys
from datetime import datetime
from database import DatabaseManager
from learn_mode import UserManager, LearningSession, ProgressTracker

# Unicode combining characters for Greek diacritics
SMOOTH_BREATHING = '\u0313'  # ᾿
ROUGH_BREATHING = '\u0314'   # ῾
IOTA_SUBSCRIPT = '\u0345'    # ͅ (combines with α, η, ω)

class PracticeConfig:
    """Configuration class for practice settings and toggles"""
    def __init__(self):
        # Core practice toggles
        self.ignore_breathings = tk.BooleanVar(value=False)
        self.prefill_stems = tk.BooleanVar(value=False)
        self.randomize_next = tk.BooleanVar(value=False)
        
        # Future toggles can be added here
        # self.ignore_accents = tk.BooleanVar(value=False)
        # self.show_hints = tk.BooleanVar(value=True)
        # self.auto_advance = tk.BooleanVar(value=False)
    
    def get_setting(self, setting_name):
        """Get the value of a specific setting"""
        if hasattr(self, setting_name):
            setting = getattr(self, setting_name)
            if isinstance(setting, tk.BooleanVar):
                return setting.get()
            return setting
        return None
    
    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        self.ignore_breathings.set(False)
        self.prefill_stems.set(False)
        self.randomize_next.set(False)

class GreekGrammarApp:
    """Provides an interactive interface for practicing Greek declensions."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ancient Greek Grammar Study")
        
        # Initialize state variables
        self.table_frame = None
        self.entries = {}
        self.error_labels = {}
        
        # Track reveal/retry state
        self.has_revealed = False
        self.incorrect_entries = set()  # Track which entries were incorrect
        
        # Initialize Learn Mode components
        self.db_manager = DatabaseManager()
        self.user_manager = UserManager(self.db_manager)
        self.current_user = None
        self.current_session = None
        self.learn_mode_enabled = tk.BooleanVar(value=False)
        self.attempt_start_time = None
        self.progress_tracker = None  # Will be initialized after main_frame
        
        # Initialize practice configuration
        self.config = PracticeConfig()
        
        # Initialize starred items system
        self.starred_items = set()  # Set of starred items in format "type:mode"
        self.starred_file = "starred_items.json"
        self.star_button = None  # Will be created in setup_ui
        
        # Load starred items from file
        self.load_starred_items()
        
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
        
        # Configure root window with better sizing and resizing behavior
        self.root.configure(padx=20, pady=20)
        self.root.state('zoomed')  # Start maximized
        self.root.minsize(1000, 700)  # Set minimum size to prevent content from being cut off
        
        # Main container that will expand to fill the window
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        
        # Configure grid weights for proper expansion
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Configure main_frame rows to expand properly
        self.main_frame.grid_rowconfigure(0, weight=0)  # Title - fixed
        self.main_frame.grid_rowconfigure(1, weight=0)  # Type selector - fixed
        self.main_frame.grid_rowconfigure(2, weight=0)  # Mode selector - fixed
        self.main_frame.grid_rowconfigure(3, weight=1)  # Table area - expands
        self.main_frame.grid_rowconfigure(4, weight=0)  # Buttons - fixed
        self.main_frame.grid_columnconfigure(0, weight=1)  # Center everything horizontally
        
        # Configure main_frame grid weights for responsive layout
        self.main_frame.grid_rowconfigure(0, weight=0)  # Title row - fixed
        self.main_frame.grid_rowconfigure(1, weight=0)  # Mode row - fixed
        self.main_frame.grid_rowconfigure(2, weight=0)  # Selector row - fixed
        self.main_frame.grid_rowconfigure(3, weight=1)  # Table row - expandable
        self.main_frame.grid_rowconfigure(4, weight=0)  # Button row - fixed
        self.main_frame.grid_columnconfigure(0, weight=1)  # Center everything horizontally
        self.main_frame.grid_rowconfigure(2, weight=0)  # Word row - fixed
        self.main_frame.grid_rowconfigure(3, weight=1)  # Table row - expandable (moved up)
        self.main_frame.grid_rowconfigure(4, weight=0)  # Button row - fixed
        for i in range(3):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Initialize progress tracker now that main_frame exists
        self.progress_tracker = ProgressTracker(self.main_frame, self.db_manager)

        # Title and Instructions
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        title_frame.grid_columnconfigure(0, weight=1)  # Allow title to expand
        title_frame.grid_columnconfigure(1, weight=0)  # Practice options column
        title_frame.grid_columnconfigure(2, weight=0)  # Help button column
        
        title_label = ttk.Label(
            title_frame, 
            text="Ancient Greek Grammar Study",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, sticky='w')
        
        # Practice options in top corner (simplified)
        practice_options_frame = ttk.Frame(title_frame)
        practice_options_frame.grid(row=0, column=1, sticky='ne', padx=(10, 10))
        
        # Prefill stems checkbox (simplified, no breathing option)
        prefill_stems_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Prefill stems",
            variable=self.config.prefill_stems,
            command=self.on_prefill_stems_toggle
        )
        prefill_stems_cb.grid(row=0, column=0, sticky='e')
        
        # Randomize next checkbox
        randomize_next_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Randomize next",
            variable=self.config.randomize_next
        )
        randomize_next_cb.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        # Learn Mode checkbox
        learn_mode_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Learn Mode",
            variable=self.learn_mode_enabled,
            command=self.toggle_learn_mode
        )
        learn_mode_cb.grid(row=0, column=2, sticky='e', padx=(10, 0))
        
        # Help button in top right corner
        help_button = ttk.Button(
            title_frame,
            text="Help",
            command=self.show_help,
            width=8
        )
        help_button.grid(row=0, column=2, sticky='ne')

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

        # Initialize verb navigation state for complex verb navigation
        self.verb_voice_order = ["Active", "Middle", "Passive"]
        self.verb_tense_order = ["Present", "Imperfect", "Future", "Aorist", "Perfect", "Pluperfect"] 
        self.verb_mood_order = ["Indicative", "Subjunctive", "Optative", "Imperative"]

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
            values=["Starred", "Noun", "Adjective", "Pronoun", "Verb"],
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
            "Article (ὁ, ἡ, τό)",
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
            "Present Indicative Active - Step (βαίνω)",
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

        # Star button for favoriting tables
        self.star_button = tk.Button(
            word_frame,
            text="☆",
            font=('Arial', 16),
            foreground="black",
            background="white",
            activeforeground="black",
            activebackground="#f0f0f0",
            relief="flat",
            borderwidth=0,
            command=self.toggle_star,
            cursor="hand2"
        )
        self.star_button.grid(row=0, column=2, padx=(10, 0))
        
        # Initialize star button state
        self.update_star_button()

        # Create declension table
        self.create_declension_table()
        
        # Update word display after creating table
        self.update_word_display()
        
        # Initialize navigation history with initial state
        self.table_history = []
        self.current_history_index = -1  # Start at -1 since we're about to add first state
        print("Initializing navigation history")
        # Initial state will be saved by save_current_state
        self.save_current_state()

    def on_prefill_stems_toggle(self):
        """Handle the prefill stems toggle change"""
        if self.config.prefill_stems.get():
            # Prefill stems are now enabled, apply to current table
            self.apply_prefill_stems_to_all_entries()
        else:
            # Prefill stems disabled, clear the prefilled content and restore normal state
            for entry_key, entry in self.entries.items():
                if hasattr(entry, '_full_answer'):
                    # Remove the full answer storage
                    delattr(entry, '_full_answer')
                # Clear the field
                entry.delete(0, tk.END)

    def toggle_learn_mode(self):
        """Toggle Learn Mode on/off"""
        if self.learn_mode_enabled.get():
            # Enable Learn Mode
            user = self.user_manager.show_user_selection(self.root)
            if user:
                self.current_user = user
                self.current_session = LearningSession(self.db_manager, user['user_id'])
                self.progress_tracker.set_user(user)
                self.progress_tracker.create_progress_display()
                self.attempt_start_time = None
                messagebox.showinfo("Learn Mode", f"Learn Mode enabled for {user['username']}")
                print(f"Learn Mode enabled for user: {user['username']} ({user['user_id']})")
            else:
                # User cancelled, disable Learn Mode
                self.learn_mode_enabled.set(False)
        else:
            # Disable Learn Mode
            if self.current_session:
                summary = self.current_session.end_session()
                if summary and summary['total_attempts'] > 0:
                    messagebox.showinfo("Session Complete", 
                        f"Session Summary:\n"
                        f"Total Attempts: {summary['total_attempts']}\n"
                        f"Accuracy: {summary['accuracy']:.1f}%\n"
                        f"Duration: {summary['duration_seconds']//60}m {summary['duration_seconds']%60}s\n"
                        f"Paradigms Practiced: {len(summary['paradigms_practiced'])}")
            
            self.current_user = None
            self.current_session = None
            self.progress_tracker.hide_progress_display()
            print("Learn Mode disabled")

    def update_word_display(self):
        """Update the word display by extracting the word from the mode name."""
        mode = self.mode_var.get()
        current_type = self.type_var.get()
        
        # Handle starred items with different format
        if current_type == "Starred":
            # For starred verbs like "λύω - Present Active Indicative"
            if " - " in mode:
                word = mode.split(" - ")[0]
            # For other starred items like "Personal I (ἐγώ)"
            elif "(" in mode and ")" in mode:
                parentheses_content = mode.split("(")[1].split(")")[0]
                if ", " in parentheses_content:
                    word = parentheses_content.split(", ")[0]
                else:
                    word = parentheses_content
            else:
                word = mode
        else:
            # Extract the word from the mode name (usually in parentheses)
            if "(" in mode and ")" in mode:
                # Extract text within parentheses - handle multiple words
                parentheses_content = mode.split("(")[1].split(")")[0]
                
                # For modes with multiple words like "ὁ, ἡ, το", take the first part
                if ", " in parentheses_content:
                    word = parentheses_content.split(", ")[0]
                else:
                    word = parentheses_content
            else:
                # Fallback for modes without parentheses
                word = "—"
        
        # Update the word label
        self.word_label.config(text=word)
        
        # Update star button state
        self.update_star_button()
        
        # Update progress tracker if in Learn Mode
        if self.learn_mode_enabled.get() and self.current_user:
            paradigm_type = current_type
            paradigm_name = mode
            self.progress_tracker.update_current_paradigm(paradigm_type, paradigm_name)

    def save_current_state(self, force=False):
        """Save the current table state to history."""
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
        verb_state = None
        
        # For verbs, also save voice/mood/tense state
        if current_type == "Verb":
            verb_state = (
                self.voice_var.get() if hasattr(self, 'voice_var') else None,
                self.mood_var.get() if hasattr(self, 'mood_var') else None,
                self.tense_var.get() if hasattr(self, 'tense_var') else None
            )
        
        current_state = (current_type, current_mode, verb_state)
        
        # Initialize history if needed
        if not hasattr(self, 'table_history'):
            self.table_history = []
            self.current_history_index = -1
        
        # If we're at the initial state and no history exists, or force is True
        if len(self.table_history) == 0 or force:
            self.table_history.append(current_state)
            self.current_history_index = len(self.table_history) - 1
            print(f"State saved (initial/forced). Total states: {len(self.table_history)}, Current index: {self.current_history_index}")
            return

        # If this state is different from the current one
        if current_state != self.table_history[self.current_history_index]:
            # If we're not at the end of the history, truncate the forward history
            if self.current_history_index < len(self.table_history) - 1:
                self.table_history = self.table_history[:self.current_history_index + 1]
            
            # Add the new state
            self.table_history.append(current_state)
            self.current_history_index = len(self.table_history) - 1
            print(f"New state saved. Total states: {len(self.table_history)}, Current index: {self.current_history_index}")
        else:
            print(f"State unchanged. Total states: {len(self.table_history)}, Current index: {self.current_history_index}")

    def next_answer(self):
        """Navigate to the next item in the current dropdown list."""
        print("Next button pressed")
        
        # Check if randomize next is enabled
        if self.config.randomize_next.get():
            self.random_next()
            return
        
        # Save current state before navigation with force=True to ensure it's saved
        self.save_current_state(force=True)
            
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
            
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
        
        if current_type == "Starred":
            # For starred items, navigate within the starred list
            current_modes = self.modes  # This is the current dropdown list
            
            try:
                current_index = current_modes.index(current_mode)
                # Move to next mode, wrap around if at the end
                next_index = (current_index + 1) % len(current_modes)
                next_mode = current_modes[next_index]
                
                # Update the mode selection
                self.mode_var.set(next_mode)
                self.on_mode_change(None)  # Trigger the mode change event with None event
                
            except ValueError:
                # Current mode not found in list, stay at current mode
                print(f"Debug: Current mode '{current_mode}' not found in starred modes list")
                pass
        elif current_type == "Verb":
            # For verbs, use the complex voice/tense/mood navigation
            self.next_verb_combination()
        else:
            # For nouns, adjectives, pronouns - navigate through dropdown options
            current_modes = self.modes  # This is the current dropdown list
            
            try:
                current_index = current_modes.index(current_mode)
                # Move to next mode, wrap around if at the end
                next_index = (current_index + 1) % len(current_modes)
                next_mode = current_modes[next_index]
                
                # Update the mode selection
                self.mode_var.set(next_mode)
                self.on_mode_change(None)  # Trigger the mode change event with None event
                
            except ValueError:
                # Current mode not found in list, stay at current mode
                print(f"Debug: Current mode '{current_mode}' not found in modes list")
                pass
        
        # Clear all entries and apply prefill stems if enabled for the new combination
        self.clear_all_entries()
        self.apply_prefill_stems_to_all_entries()

    def random_next(self):
        """Navigate to a completely random table (type, mode, and for verbs: voice/tense/mood)."""
        import random
        
        # Save current state before random navigation
        self.save_current_state()
        
        current_type = self.type_var.get()
        
        if current_type == "Starred":
            # If we're in starred mode, randomize within starred items only
            available_modes = self.modes
            if available_modes and available_modes != ["No starred items"]:
                random_mode = random.choice(available_modes)
                self.mode_var.set(random_mode)
                self.on_mode_change(None)
            return
        
        # For non-starred types, use normal random logic
        # Randomly select a type
        available_types = ["Noun", "Adjective", "Pronoun", "Verb"]
        random_type = random.choice(available_types)
        
        # Set the type
        self.type_var.set(random_type)
        self.on_type_change(None)  # Update the available modes
        
        # Randomly select a mode from the available modes for this type
        available_modes = self.modes
        if available_modes:
            random_mode = random.choice(available_modes)
            self.mode_var.set(random_mode)
            self.on_mode_change(None)
        
        # If it's a verb, also randomize voice, tense, and mood
        if random_type == "Verb":
            # Get available combinations for this verb
            current_mode = self.mode_var.get()
            lemma = None
            if "(" in current_mode and ")" in current_mode:
                lemma = current_mode.split("(")[1].split(")")[0]
            
            if lemma:
                available_combinations = self.get_available_combinations_for_verb(lemma)
                if available_combinations:
                    # Randomly select a combination
                    random_combo = random.choice(available_combinations)
                    tense, mood, voice = random_combo
                    
                    # Set the random combination
                    self.tense_var.set(tense)
                    self.mood_var.set(mood)
                    self.voice_var.set(voice)
                    self.update_tense_mood_constraints()
                    # Recreate the table to handle infinitive vs finite verb layouts
                    self.reset_table()
        
        # Clear all entries and apply prefill stems if enabled
        self.clear_all_entries()
        self.apply_prefill_stems_to_all_entries()

    def next_word_in_list(self):
        """Move to the next word in the current paradigm's word list."""
        # This method is no longer used - navigation goes through dropdown modes instead
        pass
                
    def next_verb_combination(self):
        """Navigate to the next verb combination following the hierarchy: Voice → Tense → Mood → Verb."""
        current_voice = self.voice_var.get()
        current_tense = self.tense_var.get()
        current_mood = self.mood_var.get()
        current_mode = self.mode_var.get()
        
        # Get available combinations for current verb
        lemma = None
        if "(" in current_mode and ")" in current_mode:
            lemma = current_mode.split("(")[1].split(")")[0]
        
        if not lemma:
            return
            
        available_combinations = self.get_available_combinations_for_verb(lemma)
        
        # Special handling for infinitives - skip voice navigation since all voices are shown at once
        if current_mood == "Infinitive":
            # For infinitives, go directly to next tense (skip voice navigation)
            current_mood_combinations = [combo for combo in available_combinations if combo[1] == current_mood]
            available_tenses_current = sorted(list(set([combo[0] for combo in current_mood_combinations])),
                                            key=lambda x: self.verb_tense_order.index(x) if x in self.verb_tense_order else 999)
            
            if current_tense in available_tenses_current:
                current_tense_index = available_tenses_current.index(current_tense)
                if current_tense_index < len(available_tenses_current) - 1:
                    # Move to next tense within infinitive mood
                    next_tense = available_tenses_current[current_tense_index + 1]
                    self.tense_var.set(next_tense)
                    self.update_tense_mood_constraints()
                    # Clear entries and apply prefill stems for the new combination
                    self.clear_all_entries()
                    self.apply_prefill_stems_to_all_entries()
                    # Update star button state after infinitive tense change
                    self.update_star_button()
                    return
            
            # Tense wrapped around in infinitive, advance to next mood
            all_moods_available = sorted(list(set([combo[1] for combo in available_combinations])),
                                       key=lambda x: self.verb_mood_order.index(x) if x in self.verb_mood_order else 999)
            
            if current_mood in all_moods_available:
                current_mood_index = all_moods_available.index(current_mood)
                if current_mood_index < len(all_moods_available) - 1:
                    # Move to next mood, reset to first tense and first voice
                    next_mood = all_moods_available[current_mood_index + 1]
                    
                    # Get first available tense for this mood
                    next_mood_combinations = [combo for combo in available_combinations if combo[1] == next_mood]
                    available_tenses_next_mood = sorted(list(set([combo[0] for combo in next_mood_combinations])),
                                                      key=lambda x: self.verb_tense_order.index(x) if x in self.verb_tense_order else 999)
                    
                    if available_tenses_next_mood:
                        next_tense = available_tenses_next_mood[0]
                        # Get first available voice for this mood/tense combination
                        next_mood_tense_combinations = [combo for combo in available_combinations 
                                                      if combo[1] == next_mood and combo[0] == next_tense]
                        available_voices_next_mood = sorted(list(set([combo[2] for combo in next_mood_tense_combinations])), 
                                                          key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                        
                        if available_voices_next_mood:
                            old_mood = current_mood
                            self.mood_var.set(next_mood)
                            self.tense_var.set(next_tense)
                            self.voice_var.set(available_voices_next_mood[0])
                            self.update_tense_mood_constraints()
                            # Recreate table if mood changed between infinitive and finite forms
                            if (old_mood == "Infinitive") != (next_mood == "Infinitive"):
                                current_paradigm = self.get_current_paradigm()
                                if current_paradigm:
                                    self.create_verb_table(current_paradigm)
                            # Clear entries and apply prefill stems for the new combination
                            self.clear_all_entries()
                            self.apply_prefill_stems_to_all_entries()
                            # Update star button state after mood change (infinitive section)
                            self.update_star_button()
                            return
            
            # All wrapped around, move to next verb
            self.next_verb_in_list()
            
            # Reset to first available combination for new verb
            lemma = None
            current_mode = self.mode_var.get()  # Get updated mode
            if "(" in current_mode and ")" in current_mode:
                lemma = current_mode.split("(")[1].split(")")[0]
            
            if lemma:
                available_combinations = self.get_available_combinations_for_verb(lemma)
                if available_combinations:
                    # Sort combinations to get Present Active Indicative first
                    available_combinations.sort(key=lambda x: (
                        self.verb_mood_order.index(x[1]) if x[1] in self.verb_mood_order else 999,
                        self.verb_tense_order.index(x[0]) if x[0] in self.verb_tense_order else 999,
                        self.verb_voice_order.index(x[2]) if x[2] in self.verb_voice_order else 999
                    ))
                    first_combo = available_combinations[0]
                    old_mood = current_mood
                    self.mood_var.set(first_combo[1])
                    self.tense_var.set(first_combo[0])
                    self.voice_var.set(first_combo[2])
                    self.update_tense_mood_constraints()
                    # Recreate table if mood changed between infinitive and finite forms
                    if (old_mood == "Infinitive") != (first_combo[1] == "Infinitive"):
                        current_paradigm = self.get_current_paradigm()
                        if current_paradigm:
                            self.create_verb_table(current_paradigm)
            return
        
        # Normal handling for non-infinitive moods
        # Step 1: Try to advance Voice within current tense/mood
        current_mood_tense_combinations = [combo for combo in available_combinations 
                                         if combo[0] == current_tense and combo[1] == current_mood]
        available_voices_current = sorted(list(set([combo[2] for combo in current_mood_tense_combinations])), 
                                        key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
        
        if current_voice in available_voices_current:
            current_voice_index = available_voices_current.index(current_voice)
            if current_voice_index < len(available_voices_current) - 1:
                # Move to next voice, keep same tense and mood
                next_voice = available_voices_current[current_voice_index + 1]
                self.voice_var.set(next_voice)
                self.update_tense_mood_constraints()
                # Clear entries and apply prefill stems for the new combination
                self.clear_all_entries()
                self.apply_prefill_stems_to_all_entries()
                # Update star button state after voice change
                self.update_star_button()
                return
        
        # Step 2: Voice wrapped around, try to advance Tense within current mood
        current_mood_combinations = [combo for combo in available_combinations if combo[1] == current_mood]
        available_tenses_current = sorted(list(set([combo[0] for combo in current_mood_combinations])),
                                        key=lambda x: self.verb_tense_order.index(x) if x in self.verb_tense_order else 999)
        
        if current_tense in available_tenses_current:
            current_tense_index = available_tenses_current.index(current_tense)
            if current_tense_index < len(available_tenses_current) - 1:
                # Move to next tense, reset to first voice
                next_tense = available_tenses_current[current_tense_index + 1]
                # Get first available voice for this tense/mood combination
                next_tense_combinations = [combo for combo in available_combinations 
                                         if combo[0] == next_tense and combo[1] == current_mood]
                available_voices_next = sorted(list(set([combo[2] for combo in next_tense_combinations])), 
                                             key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                if available_voices_next:
                    self.voice_var.set(available_voices_next[0])
                    self.tense_var.set(next_tense)
                    self.update_tense_mood_constraints()
                    # Clear entries and apply prefill stems for the new combination
                    self.clear_all_entries()
                    self.apply_prefill_stems_to_all_entries()
                    # Update star button state after tense change
                    self.update_star_button()
                    return
        
        # Step 3: Tense wrapped around, try to advance Mood
        all_moods_available = sorted(list(set([combo[1] for combo in available_combinations])),
                                   key=lambda x: self.verb_mood_order.index(x) if x in self.verb_mood_order else 999)
        
        if current_mood in all_moods_available:
            current_mood_index = all_moods_available.index(current_mood)
            if current_mood_index < len(all_moods_available) - 1:
                # Move to next mood, reset to first tense and first voice
                next_mood = all_moods_available[current_mood_index + 1]
                
                # Get first available tense for this mood
                next_mood_combinations = [combo for combo in available_combinations if combo[1] == next_mood]
                available_tenses_next_mood = sorted(list(set([combo[0] for combo in next_mood_combinations])),
                                                  key=lambda x: self.verb_tense_order.index(x) if x in self.verb_tense_order else 999)
                
                if available_tenses_next_mood:
                    next_tense = available_tenses_next_mood[0]
                    # Get first available voice for this mood/tense combination
                    next_mood_tense_combinations = [combo for combo in available_combinations 
                                                  if combo[1] == next_mood and combo[0] == next_tense]
                    available_voices_next_mood = sorted(list(set([combo[2] for combo in next_mood_tense_combinations])), 
                                                      key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                    
                    if available_voices_next_mood:
                        old_mood = current_mood
                        self.mood_var.set(next_mood)
                        self.tense_var.set(next_tense)
                        self.voice_var.set(available_voices_next_mood[0])
                        self.update_tense_mood_constraints()
                        # Recreate table if mood changed between infinitive and finite forms
                        if (old_mood == "Infinitive") != (next_mood == "Infinitive"):
                            current_paradigm = self.get_current_paradigm()
                            if current_paradigm:
                                self.create_verb_table(current_paradigm)
                        # Clear entries and apply prefill stems for the new combination
                        self.clear_all_entries()
                        self.apply_prefill_stems_to_all_entries()
                        # Update star button state after mood change
                        self.update_star_button()
                        return
        
        # Step 4: All wrapped around, move to next verb
        self.next_verb_in_list()
        
        # Reset to first available combination for new verb (Present Active Indicative)
        lemma = None
        current_mode = self.mode_var.get()  # Get updated mode
        if "(" in current_mode and ")" in current_mode:
            lemma = current_mode.split("(")[1].split(")")[0]
        
        if lemma:
            available_combinations = self.get_available_combinations_for_verb(lemma)
            if available_combinations:
                # Sort combinations to get Present Active Indicative first
                # Priority: Mood (Indicative first) → Tense (Present first) → Voice (Active first)
                available_combinations.sort(key=lambda x: (
                    self.verb_mood_order.index(x[1]) if x[1] in self.verb_mood_order else 999,
                    self.verb_tense_order.index(x[0]) if x[0] in self.verb_tense_order else 999,
                    self.verb_voice_order.index(x[2]) if x[2] in self.verb_voice_order else 999
                ))
                first_combo = available_combinations[0]
                old_mood = current_mood
                self.mood_var.set(first_combo[1])
                self.tense_var.set(first_combo[0])
                self.voice_var.set(first_combo[2])
                self.update_tense_mood_constraints()
                # Recreate table if mood changed between infinitive and finite forms
                if (old_mood == "Infinitive") != (first_combo[1] == "Infinitive"):
                    current_paradigm = self.get_current_paradigm()
                    if current_paradigm:
                        self.create_verb_table(current_paradigm)
                # Clear entries and apply prefill stems for the new combination
                self.clear_all_entries()
                self.apply_prefill_stems_to_all_entries()
                # Update star button state after verb change
                self.update_star_button()

    def next_verb_in_list(self):
        """Move to the next verb in the verb dropdown list."""
        current_mode = self.mode_var.get()
        current_verb_modes = self.verb_modes  # The actual dropdown list
        
        try:
            current_index = current_verb_modes.index(current_mode)
            # Move to next verb, wrap around if at the end
            next_index = (current_index + 1) % len(current_verb_modes)
            next_mode = current_verb_modes[next_index]
            
            # Update the mode selection
            self.mode_var.set(next_mode)
            self.on_mode_change(None)  # Trigger the mode change event
            
        except ValueError:
            # Current mode not found in list, stay at current mode
            print(f"Debug: Current verb mode '{current_mode}' not found in verb modes list")
            pass

    def create_declension_table(self):
        """Create the declension table with input fields for each case."""
        if self.table_frame:
            self.table_frame.destroy()
            
        # Create a container frame that can expand to fill available space
        table_container = ttk.Frame(self.main_frame)
        table_container.grid(row=3, column=0, columnspan=3, sticky='nsew')
        table_container.grid_columnconfigure(0, weight=1)  # Center the table horizontally
        table_container.grid_rowconfigure(0, weight=1)     # Center the table vertically
        
        # Create the table frame inside the container with minimal padding for spacing
        self.table_frame = ttk.Frame(table_container)
        self.table_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)  # Reduced horizontal padding for smaller table
        
        # Configure grid weights for the table frame
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(1, weight=1)
        self.table_frame.grid_columnconfigure(2, weight=1)
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return

        # Check if this is an adjective, noun, pronoun, or verb
        current_type = self.get_effective_type()
        
        if current_type == "Adjective":
            self.create_adjective_table(current_paradigm)
        elif current_type == "Pronoun":
            self.create_pronoun_table(current_paradigm)
        elif current_type == "Verb":
            self.create_verb_table(current_paradigm)
        else:
            self.create_noun_table(current_paradigm)
        
        # Bottom button frame positioned after table, stays at bottom when window resizes
        bottom_button_frame = ttk.Frame(self.main_frame)
        bottom_button_frame.grid(row=4, column=0, sticky='ew', pady=(20, 20))
        
        # Container frame for buttons to allow centering
        button_container = ttk.Frame(bottom_button_frame)
        button_container.grid(row=0, column=1, pady=10)
        
        # Configure the bottom frame for centering
        bottom_button_frame.grid_columnconfigure(0, weight=1)  # Left padding space
        bottom_button_frame.grid_columnconfigure(1, weight=0)  # Button container (centered)
        bottom_button_frame.grid_columnconfigure(2, weight=1)  # Right padding space
        
        # Configure button container columns with equal weight for center alignment
        button_container.grid_columnconfigure(0, weight=1)  # Space before first button
        button_container.grid_columnconfigure(1, weight=0)  # Reveal button
        button_container.grid_columnconfigure(2, weight=0)  # Reset/Retry button
        button_container.grid_columnconfigure(3, weight=0)  # Next button
        button_container.grid_columnconfigure(4, weight=1)  # Space after last button
        
        # Style for buttons - now all buttons use the same large style
        button_style = ttk.Style()
        button_style.configure('Large.TButton',
                             font=('Arial', 11),
                             padding=(10, 6))
        
        # Create all buttons with consistent styling and size
        reveal_button = ttk.Button(
            button_container,
            text="Reveal",
            command=self.reveal_answers,
            style='Large.TButton',
            width=12
        )
        reveal_button.grid(row=0, column=1, padx=15)
        
        # Combined Reset/Retry button in the center
        reset_retry_button = ttk.Button(
            button_container,
            text="Reset",
            command=self.smart_reset_retry,
            style='Large.TButton',
            width=12
        )
        reset_retry_button.grid(row=0, column=2, padx=20)  # Extra padding to emphasize center position
        
        # Store reference to reset/retry button for state management
        self.reset_retry_button = reset_retry_button
        
        next_button = ttk.Button(
            button_container,
            text="Next",
            command=self.next_answer,
            style='Large.TButton',
            width=12
        )
        next_button.grid(row=0, column=3, padx=15)
        
        # Apply stem prefilling if enabled
        self.apply_prefill_stems_to_all_entries()

    def create_noun_table(self, current_paradigm):
        """Create table for noun declensions (2 columns: Singular/Plural)."""
        # Clear any existing widgets in the table frame (except the frame itself)
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Configure grid weights for maximum space utilization
        self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Case labels column
        self.table_frame.grid_columnconfigure(1, weight=1, minsize=120)  # Singular column - reduced by 50%
        self.table_frame.grid_columnconfigure(2, weight=1, minsize=120)  # Plural column - reduced by 50%
        
        # Configure row heights with reduced spacing
        for i in range(7):  # 0-6 rows (header + 5 cases + padding)
            self.table_frame.grid_rowconfigure(i, weight=0)  # Remove minimum height constraint

        # Headers with consistent styling and reduced padding
        ttk.Label(
            self.table_frame,
            text="",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        ttk.Label(
            self.table_frame,
            text="Singular",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=1, padx=10, pady=(5,10))
        ttk.Label(
            self.table_frame,
            text="Plural",
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=2, padx=10, pady=(5,10))

        # Create input fields for each case with guaranteed visibility (British order)
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        for i, case in enumerate(cases, 1):
            # Case label with consistent styling and better positioning
            case_label = ttk.Label(
                self.table_frame,
                text=case,
                font=('Arial', 12, 'bold')
            )
            case_label.grid(row=i, column=0, padx=10, pady=6, sticky='e')

            # Singular entry with consistent sizing
            entry_sg = tk.Entry(
                self.table_frame,
                width=15,  # Reduced by 50%
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_sg.grid(row=i, column=1, padx=10, pady=6, sticky='ew')
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
            error_label_sg.grid(row=i, column=1, sticky='e', padx=10)
            self.error_labels[f"{case}_sg"] = error_label_sg
            error_label_sg.grid_remove()

            # Plural entry with consistent sizing
            entry_pl = tk.Entry(
                self.table_frame,
                width=15,  # Reduced by 50%
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_pl.grid(row=i, column=2, padx=10, pady=6, sticky='ew')
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
            error_label_pl.grid(row=i, column=2, sticky='e', padx=10)
            self.error_labels[f"{case}_pl"] = error_label_pl
            error_label_pl.grid_remove()

    def create_adjective_table(self, current_paradigm):
        """Create table for adjective declensions (2 or 3 genders based on type)."""
        # Clear any existing widgets in the table frame (except the frame itself)
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Determine if this is a 2-termination or 3-termination adjective
        adjective_type = current_paradigm.get("type", "")
        is_two_termination = adjective_type == "adjective_2termination"
        
        if is_two_termination:
            # 2-termination: Masculine/Feminine + Neuter (4 columns total)
            self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Case labels column
            self.table_frame.grid_columnconfigure(1, weight=1, minsize=120)  # M/F Sg - reduced by 50%
            self.table_frame.grid_columnconfigure(2, weight=1, minsize=120)  # M/F Pl - reduced by 50%
            self.table_frame.grid_columnconfigure(3, weight=1, minsize=120)  # Neuter Sg - reduced by 50%
            self.table_frame.grid_columnconfigure(4, weight=1, minsize=120)  # Neuter Pl - reduced by 50%
            
            # Configure row heights with reduced spacing
            for i in range(8):  # 0-7 rows (header + subheader + 5 cases + padding)
                self.table_frame.grid_rowconfigure(i, weight=0)  # Remove minimum height constraint

            # Main headers with consistent styling and reduced padding
            ttk.Label(
                self.table_frame,
                text="",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
            
            ttk.Label(
                self.table_frame,
                text="Masculine/Feminine",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=1, columnspan=2, padx=10, pady=(5,10))
            
            ttk.Label(
                self.table_frame,
                text="Neuter",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=3, columnspan=2, padx=10, pady=(5,10))

            # Sub-headers (Singular/Plural) with reduced padding
            for i, header in enumerate(["Singular", "Plural", "Singular", "Plural"]):
                ttk.Label(
                    self.table_frame,
                    text=header,
                    font=('Arial', 12, 'bold')
                ).grid(row=1, column=i + 1, padx=10, pady=(0,5))

            # Create input fields for each case
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for i, case in enumerate(cases, 2):  # Start from row 2
                # Case label with consistent styling
                case_label = ttk.Label(
                    self.table_frame,
                    text=case,
                    font=('Arial', 12, 'bold'),
                    foreground='#34495e'
                )
                case_label.grid(row=i, column=0, padx=10, pady=6, sticky='e')

                # Masculine/Feminine columns (use masculine data since they're identical)
                for j, number in enumerate(["sg", "pl"]):
                    entry = tk.Entry(
                        self.table_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=i, column=j + 1, padx=10, pady=6, sticky='ew')
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
                    error_label.grid(row=i, column=j + 1, sticky='e', padx=10)
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()

                # Neuter columns
                for j, number in enumerate(["sg", "pl"]):
                    entry = tk.Entry(
                        self.table_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=i, column=j + 3, padx=10, pady=6, sticky='ew')
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
                    error_label.grid(row=i, column=j + 3, sticky='e', padx=10)
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()
        else:
            # 3-termination: Masculine + Feminine + Neuter (6 columns total)
            self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Case labels column
            for i in range(1, 7):  # Gender columns - reduced size
                self.table_frame.grid_columnconfigure(i, weight=1, minsize=120)

            # Configure row heights with reduced spacing
            for i in range(8):  # 0-7 rows (header + subheader + 5 cases + padding)
                self.table_frame.grid_rowconfigure(i, weight=0)  # Remove minimum height constraint

            # Main headers with consistent styling and reduced padding
            ttk.Label(
                self.table_frame,
                text="",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
            
            ttk.Label(
                self.table_frame,
                text="Masculine",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=1, columnspan=2, padx=10, pady=(5,10))
            
            ttk.Label(
                self.table_frame,
                text="Feminine", 
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=3, columnspan=2, padx=10, pady=(5,10))
            
            ttk.Label(
                self.table_frame,
                text="Neuter",
                font=('Arial', 14, 'bold')
            ).grid(row=0, column=5, columnspan=2, padx=10, pady=(5,10))

            # Sub-headers (Singular/Plural for each gender) with reduced padding
            genders = ['masculine', 'feminine', 'neuter']
            for i, gender in enumerate(genders):
                base_col = 1 + i * 2
                ttk.Label(
                    self.table_frame,
                    text="Singular",
                    font=('Arial', 12, 'bold')
                ).grid(row=1, column=base_col, padx=10, pady=(0,5))
                
                ttk.Label(
                    self.table_frame,
                    text="Plural",
                    font=('Arial', 12, 'bold')
                ).grid(row=1, column=base_col + 1, padx=10, pady=(0,5))

            # Create input fields for each case and gender
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for i, case in enumerate(cases, 2):  # Start from row 2
                # Case label with consistent styling
                case_label = ttk.Label(
                    self.table_frame,
                    text=case,
                    font=('Arial', 12, 'bold'),
                    foreground='#34495e'
                ).grid(row=i, column=0, padx=10, pady=6, sticky='e')

                # Create entries for each gender and number
                for j, gender in enumerate(genders):
                    base_col = 1 + j * 2
                    
                    # Singular entry
                    entry_sg = tk.Entry(
                        self.table_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry_sg.grid(row=i, column=base_col, padx=10, pady=6, sticky='ew')
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
                    error_label_sg.grid(row=i, column=base_col, sticky='e', padx=10)
                    self.error_labels[entry_key_sg] = error_label_sg
                    error_label_sg.grid_remove()

                    # Plural entry
                    entry_pl = tk.Entry(
                        self.table_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry_pl.grid(row=i, column=base_col + 1, padx=10, pady=6, sticky='ew')
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
                    error_label_pl.grid(row=i, column=base_col + 1, sticky='e', padx=10)
                    self.error_labels[entry_key_pl] = error_label_pl
                    error_label_pl.grid_remove()

    def create_pronoun_table(self, current_paradigm):
        """Create the pronoun table with appropriate layout based on pronoun type."""
        # Clear any existing widgets in the table frame (except the frame itself)
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
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

    def get_available_voices_for_verb(self, lemma):
        """Determine which voices are available for a given verb based on paradigms data."""
        available_voices = set()
        
        # Search through all paradigms to find entries for this lemma
        for paradigm_key, paradigm_data in self.paradigms.items():
            if (paradigm_data.get('type') == 'verb' and 
                paradigm_data.get('lemma') == lemma and
                'voice' in paradigm_data):
                voice = paradigm_data['voice']
                if voice == 'active':
                    available_voices.add('Active')
                elif voice == 'middle':
                    available_voices.add('Middle')
                elif voice == 'passive':
                    available_voices.add('Passive')
        
        # If no voices found or only active found, default to active only
        if not available_voices or available_voices == {'Active'}:
            return ['Active']
        
        # Return voices in standard order
        ordered_voices = []
        if 'Active' in available_voices:
            ordered_voices.append('Active')
        if 'Middle' in available_voices:
            ordered_voices.append('Middle')
        if 'Passive' in available_voices:
            ordered_voices.append('Passive')
            
        return ordered_voices

    def get_available_combinations_for_verb(self, lemma):
        """Get all available tense/mood/voice combinations for a given verb based on paradigms data."""
        combinations = set()
        
        # Search through all paradigms to find entries for this lemma
        for paradigm_key, paradigm_data in self.paradigms.items():
            if (paradigm_data.get('type') == 'verb' and 
                paradigm_data.get('lemma') == lemma):
                
                tense = paradigm_data.get('tense', '')
                mood = paradigm_data.get('mood', '')
                voice = paradigm_data.get('voice', '')
                
                # Convert to display format
                tense_display = tense.title() if tense else ''
                mood_display = mood.title() if mood else ''
                voice_display = voice.title() if voice else ''
                
                # Handle special cases
                if tense == 'pluperfect':
                    tense_display = 'Pluperfect'
                
                if all([tense_display, mood_display, voice_display]):
                    combinations.add((tense_display, mood_display, voice_display))
        
        return list(combinations)

    def create_verb_table(self, current_paradigm):
        """Create the verb conjugation table with input fields for each person/number."""
        
        # Clear any existing widgets in the table frame (except the frame itself)
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        
        # Reset grid configuration
        for i in range(10):  # Clear up to 10 columns
            self.table_frame.grid_columnconfigure(i, weight=0)
        
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
        available_tenses = self.get_base_available_tenses()
        
        # If current tense is not available for this verb, reset to Present
        if tense_value not in available_tenses:
            tense_value = "Present"
        
        # Further filter tenses based on current mood (if mood is already set)
        current_mood = getattr(self, 'mood_var', None)
        if current_mood:
            try:
                mood_value = current_mood.get()
                if mood_value == "Infinitive":
                    # Infinitives only exist for Present, Aorist, Future, Perfect (no Imperfect, no Pluperfect)
                    available_tenses = [t for t in available_tenses if t not in ["Imperfect", "Pluperfect"]]
                    if tense_value in ["Imperfect", "Pluperfect"]:
                        tense_value = "Present"
            except:
                pass  # Ignore errors if mood_var not properly set yet
        
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
        # Extract the lemma from the mode string (it's in parentheses)
        mode = self.mode_var.get()
        lemma = None
        if "(" in mode and ")" in mode:
            lemma = mode.split("(")[1].split(")")[0]
        
        # Get available voices based on what's actually in the paradigms
        if lemma:
            available_voices = self.get_available_voices_for_verb(lemma)
        else:
            # Fallback to old logic if lemma extraction fails
            active_only_verbs = ["εἰμί", "εἶμι", "βαίνω", "οἶδα", "φημί", "ἵημι"]
            is_active_only = any(verb in mode for verb in active_only_verbs)
            available_voices = ["Active"] if is_active_only else ["Active", "Middle", "Passive"]
        
        # If user had Middle/Passive selected but switched to a verb without those forms, default to Active
        if voice_value in ["Middle", "Passive"] and voice_value not in available_voices:
            voice_value = "Active"
        
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
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif tense_value == "Imperfect":
            available_moods = ["Indicative", "Optative"]  # No infinitive for imperfect
        elif tense_value == "Aorist":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif tense_value == "Future":
            available_moods = ["Indicative", "Optative", "Infinitive"]  # No subjunctive for future
        elif tense_value == "Perfect":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif tense_value == "Pluperfect":
            available_moods = ["Indicative", "Optative"]  # No infinitive for pluperfect
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
        
        # Check if we're dealing with infinitive - different table layout needed
        current_mood = self.mood_var.get()
        if current_mood == "Infinitive":
            # Update selectors frame for infinitive layout (2 columns)
            selectors_frame.grid_configure(columnspan=2)
            self.create_infinitive_table()
        else:
            # Update selectors frame for finite verb layout (3 columns)
            selectors_frame.grid_configure(columnspan=3)
            self.create_finite_verb_table()
        
        # Update tense/mood constraints after everything is set up
        self.update_tense_mood_constraints()
    
    def create_infinitive_table(self):
        """Create a simple table for infinitive forms (tense × voice combinations)."""
        # Configure main table columns for infinitive layout
        self.table_frame.grid_columnconfigure(0, weight=1)  # Tense/Voice label column
        self.table_frame.grid_columnconfigure(1, weight=2)  # Infinitive form column

        # Headers (shifted down to row 2)
        ttk.Label(
            self.table_frame,
            text="Tense × Voice",
            font=('Arial', 12, 'bold')
        ).grid(row=2, column=0, padx=10, pady=10)

        ttk.Label(
            self.table_frame,
            text="Infinitive Form",
            font=('Arial', 12, 'bold')
        ).grid(row=2, column=1, padx=10, pady=10)

        # Get current tense
        current_tense = self.tense_var.get()
        
        # Define voice options (will show all three for the selected tense)
        voices = ["Active", "Middle", "Passive"]
        
        # Create input fields for each voice in the current tense
        for i, voice in enumerate(voices, 3):
            # Tense × Voice label
            ttk.Label(
                self.table_frame,
                text=f"{current_tense} {voice}",
                font=('Arial', 12, 'bold')
            ).grid(row=i, column=0, padx=10, pady=8, sticky='w')

            # Create a frame to hold the entry and error label
            entry_frame = tk.Frame(self.table_frame)
            entry_frame.grid(row=i, column=1, padx=5, pady=8, sticky='ew')
            entry_frame.grid_columnconfigure(0, weight=1)

            entry_key = f"inf_{voice.lower()}"
            entry = tk.Entry(
                entry_frame,
                width=25,
                font=('Times New Roman', 12),
                relief='solid',
                borderwidth=1
            )
            entry.grid(row=0, column=0, sticky='ew')
            entry.bind('<Key>', self.handle_key_press)
            entry.bind('<Return>', lambda e, key=entry_key: self.handle_enter(e, key))
            entry.bind('<Up>', lambda e, key=entry_key: self.handle_arrow(e, key, 'up'))
            entry.bind('<Down>', lambda e, key=entry_key: self.handle_arrow(e, key, 'down'))
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

    def create_finite_verb_table(self):
        """Create the standard verb conjugation table for finite verbs (person × number)."""
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

    def is_greek_vowel(self, char):
        """Check if a character is a Greek vowel (with or without diacritics)."""
        if not char:
            return False
        
        # Decompose the character to get the base letter
        decomposed = unicodedata.normalize('NFD', char)
        base_char = decomposed[0] if decomposed else char
        
        # Check basic Greek vowels
        if base_char.lower() in 'αεηιουω':
            return True
        
        # Also check common precomposed Greek vowels with diacritics
        greek_vowels = {
            # Basic vowels
            'α', 'ε', 'η', 'ι', 'ο', 'υ', 'ω',
            'Α', 'Ε', 'Η', 'Ι', 'Ο', 'Υ', 'Ω',
            # With accents
            'ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ',
            'Ά', 'Έ', 'Ή', 'Ί', 'Ό', 'Ύ', 'Ώ',
            'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ',
            'Ὰ', 'Ὲ', 'Ὴ', 'Ὶ', 'Ὸ', 'Ὺ', 'Ὼ',
            'ᾶ', 'ῆ', 'ῖ', 'ῦ', 'ῶ',
            # With breathing marks
            'ἀ', 'ἐ', 'ἠ', 'ἰ', 'ὀ', 'ὐ', 'ὠ',
            'ἁ', 'ἑ', 'ἡ', 'ἱ', 'ὁ', 'ὑ', 'ὡ',
            'Ἀ', 'Ἐ', 'Ἠ', 'Ἰ', 'Ὀ', 'Ὑ', 'Ὠ',
            'Ἁ', 'Ἑ', 'Ἡ', 'Ἱ', 'Ὁ', 'Ὑ', 'Ὡ',
            # With breathing and accents
            'ἄ', 'ἔ', 'ἤ', 'ἴ', 'ὄ', 'ὔ', 'ὤ',
            'ἅ', 'ἕ', 'ἥ', 'ἵ', 'ὅ', 'ὕ', 'ὥ',
            'ἂ', 'ἒ', 'ἢ', 'ἲ', 'ὂ', 'ὒ', 'ὢ',
            'ἃ', 'ἓ', 'ἣ', 'ἳ', 'ὃ', 'ὓ', 'ὣ',
            'ἆ', 'ἦ', 'ἶ', 'ὖ', 'ὦ',
            'ἇ', 'ἧ', 'ἷ', 'ὗ', 'ὧ',
            # With iota subscript
            'ᾳ', 'ῃ', 'ῳ',
            'ᾼ', 'ῌ', 'ῼ',
            # With breathing and iota subscript
            'ᾀ', 'ᾐ', 'ᾠ', 'ᾁ', 'ᾑ', 'ᾡ',
            'ᾄ', 'ᾔ', 'ᾤ', 'ᾅ', 'ᾕ', 'ᾥ',
            'ᾂ', 'ᾒ', 'ᾢ', 'ᾃ', 'ᾓ', 'ᾣ',
            'ᾆ', 'ᾖ', 'ᾦ', 'ᾇ', 'ᾗ', 'ᾧ',
            # With accents and iota subscript
            'ᾴ', 'ῄ', 'ῴ', 'ᾲ', 'ῂ', 'ῲ', 'ᾷ', 'ῇ', 'ῷ'
        }
        
        return char in greek_vowels

    def handle_key_press(self, event):
        """Handle special character input.
        
        Diacritic shortcuts:
        [ = smooth breathing (ἀ, ἐ, ἠ, ἰ, ὀ, ὐ, ὠ)
        ] = rough breathing (ἁ, ἑ, ἡ, ἱ, ὁ, ὑ, ὡ)
        { = iota subscript (ᾳ, ῃ, ῳ)
        / = acute accent (ά, έ, ή, ί, ό, ύ, ώ)
        \\ = grave accent (ὰ, ὲ, ὴ, ὶ, ὸ, ὺ, ὼ)
        = = circumflex accent (ᾶ, ῆ, ῖ, ῦ, ῶ)
        """
        char = event.char
        entry = event.widget
        
        # Handle special diacritic keys
        if char in ['[', ']', '{', '/', '\\', '=']:
            print(f"Diacritic key detected: {char}")
            cursor_pos = entry.index(tk.INSERT)
            
            # Get the character before the cursor
            if cursor_pos > 0:
                text = entry.get()
                prev_char = text[cursor_pos-1:cursor_pos]
                print(f"Previous character: {prev_char}")
                
                if self.is_greek_vowel(prev_char):
                    result = None
                    if char == '[':
                        result = self.add_smooth_breathing(prev_char)
                    elif char == ']':
                        result = self.add_rough_breathing(prev_char)
                    elif char == '{':
                        result = self.add_iota_subscript(prev_char)
                    elif char == '/':
                        result = self.add_acute_accent(prev_char)
                    elif char == '\\':
                        result = self.add_grave_accent(prev_char)
                    elif char == '=':
                        result = self.add_circumflex_accent(prev_char)
                    
                    if result and result != prev_char:
                        entry.delete(cursor_pos-1, cursor_pos)
                        entry.insert(cursor_pos-1, result)
                        print(f"Inserted character with diacritic: {result}")
                        # Position cursor after the modified character
                        entry.icursor(cursor_pos)
            
            # Prevent the diacritic character from being inserted
            return "break"
        
        return None

    def add_smooth_breathing(self, char):
        """Add smooth breathing to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have breathing
        base_vowels = {
            'α': 'α', 'ε': 'ε', 'η': 'η', 'ι': 'ι', 
            'ο': 'ο', 'υ': 'υ', 'ω': 'ω',
            'Α': 'Α', 'Ε': 'Ε', 'Η': 'Η', 'Ι': 'Ι',
            'Ο': 'Ο', 'Υ': 'Υ', 'Ω': 'Ω',
            # Also handle precomposed characters with accents or other marks
            'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
            'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
            'ᾶ': 'α', 'ῆ': 'η', 'ῖ': 'ι', 'ῦ': 'υ', 'ῶ': 'ω',
            'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αεηιουωΑΕΗΙΟΥΩ':
            print(f"Cannot add breathing to non-vowel: {char}")
            return char
        
        # Remove any existing breathing marks from existing marks
        new_marks = [mark for mark in existing_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        
        # Add smooth breathing at the beginning (breathing comes first in canonical order)
        final_char = base_vowel + SMOOTH_BREATHING + ''.join(new_marks)
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Smooth breathing: {char} -> {result}")
        return result
        
    def add_rough_breathing(self, char):
        """Add rough breathing to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have breathing
        base_vowels = {
            'α': 'α', 'ε': 'ε', 'η': 'η', 'ι': 'ι', 
            'ο': 'ο', 'υ': 'υ', 'ω': 'ω',
            'Α': 'Α', 'Ε': 'Ε', 'Η': 'Η', 'Ι': 'Ι',
            'Ο': 'Ο', 'Υ': 'Υ', 'Ω': 'Ω',
            # Also handle precomposed characters with accents or other marks
            'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
            'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
            'ᾶ': 'α', 'ῆ': 'η', 'ῖ': 'ι', 'ῦ': 'υ', 'ῶ': 'ω',
            'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αεηιουωΑΕΗΙΟΥΩ':
            print(f"Cannot add breathing to non-vowel: {char}")
            return char
        
        # Remove any existing breathing marks from existing marks
        new_marks = [mark for mark in existing_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        
        # Add rough breathing at the beginning (breathing comes first in canonical order)
        final_char = base_vowel + ROUGH_BREATHING + ''.join(new_marks)
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Rough breathing: {char} -> {result}")
        return result

    def add_iota_subscript(self, char):
        """Add iota subscript to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have iota subscript
        base_vowels = {
            'α': 'α', 'η': 'η', 'ω': 'ω',
            'Α': 'Α', 'Η': 'Η', 'Ω': 'Ω',
            # Also handle precomposed characters with accents or breathing
            'ά': 'α', 'ή': 'η', 'ώ': 'ω',
            'ὰ': 'α', 'ὴ': 'η', 'ὼ': 'ω',
            'ᾶ': 'α', 'ῆ': 'η', 'ῶ': 'ω',
            'ἀ': 'α', 'ἠ': 'η', 'ὠ': 'ω',
            'ἁ': 'α', 'ἡ': 'η', 'ὡ': 'ω',
            'ἄ': 'α', 'ἤ': 'η', 'ὤ': 'ω',
            'ἅ': 'α', 'ἥ': 'η', 'ὥ': 'ω',
            'ἂ': 'α', 'ἢ': 'η', 'ὢ': 'ω',
            'ἃ': 'α', 'ἣ': 'η', 'ὣ': 'ω',
            'ἆ': 'α', 'ἦ': 'η', 'ὦ': 'ω',
            'ἇ': 'α', 'ἧ': 'η', 'ὧ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αηωΑΗΩ':
            print(f"Cannot add iota subscript to {char} (only α, η, ω can have iota subscript)")
            return char
        
        # Check if iota subscript already exists
        if IOTA_SUBSCRIPT in existing_marks:
            print(f"Iota subscript already present in {char}")
            return char
        
        # Add iota subscript at the end (it comes last in canonical order)
        final_char = base_vowel + ''.join(existing_marks) + IOTA_SUBSCRIPT
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Iota subscript: {char} -> {result}")
        return result

    def add_acute_accent(self, char):
        """Add acute accent to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have accent
        base_vowels = {
            'α': 'α', 'ε': 'ε', 'η': 'η', 'ι': 'ι', 
            'ο': 'ο', 'υ': 'υ', 'ω': 'ω',
            'Α': 'Α', 'Ε': 'Ε', 'Η': 'Η', 'Ι': 'Ι',
            'Ο': 'Ο', 'Υ': 'Υ', 'Ω': 'Ω',
            # Also handle precomposed characters with breathing or other marks
            'ἀ': 'α', 'ἐ': 'ε', 'ἠ': 'η', 'ἰ': 'ι', 'ὀ': 'ο', 'ὐ': 'υ', 'ὠ': 'ω',
            'ἁ': 'α', 'ἑ': 'ε', 'ἡ': 'η', 'ἱ': 'ι', 'ὁ': 'ο', 'ὑ': 'υ', 'ὡ': 'ω',
            'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αεηιουωΑΕΗΙΟΥΩ':
            print(f"Cannot add accent to non-vowel: {char}")
            return char
        
        # Remove any existing accent marks from existing marks
        accent_marks = ['\u0301', '\u0300', '\u0342']  # acute, grave, circumflex
        new_marks = [mark for mark in existing_marks if mark not in accent_marks]
        
        # Add acute accent in proper position (after breathing, before iota subscript)
        breathing_marks = [mark for mark in new_marks if mark in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        other_marks = [mark for mark in new_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        
        final_char = base_vowel + ''.join(breathing_marks) + '\u0301' + ''.join(other_marks)
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Acute accent: {char} -> {result}")
        return result

    def add_grave_accent(self, char):
        """Add grave accent to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have accent
        base_vowels = {
            'α': 'α', 'ε': 'ε', 'η': 'η', 'ι': 'ι', 
            'ο': 'ο', 'υ': 'υ', 'ω': 'ω',
            'Α': 'Α', 'Ε': 'Ε', 'Η': 'Η', 'Ι': 'Ι',
            'Ο': 'Ο', 'Υ': 'Υ', 'Ω': 'Ω',
            # Also handle precomposed characters with breathing or other marks
            'ἀ': 'α', 'ἐ': 'ε', 'ἠ': 'η', 'ἰ': 'ι', 'ὀ': 'ο', 'ὐ': 'υ', 'ὠ': 'ω',
            'ἁ': 'α', 'ἑ': 'ε', 'ἡ': 'η', 'ἱ': 'ι', 'ὁ': 'ο', 'ὑ': 'υ', 'ὡ': 'ω',
            'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αεηιουωΑΕΗΙΟΥΩ':
            print(f"Cannot add accent to non-vowel: {char}")
            return char
        
        # Remove any existing accent marks from existing marks
        accent_marks = ['\u0301', '\u0300', '\u0342']  # acute, grave, circumflex
        new_marks = [mark for mark in existing_marks if mark not in accent_marks]
        
        # Add grave accent in proper position (after breathing, before iota subscript)
        breathing_marks = [mark for mark in new_marks if mark in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        other_marks = [mark for mark in new_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        
        final_char = base_vowel + ''.join(breathing_marks) + '\u0300' + ''.join(other_marks)
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Grave accent: {char} -> {result}")
        return result

    def add_circumflex_accent(self, char):
        """Add circumflex accent to a vowel, handling existing diacritics."""
        # Decompose the character to separate base letter from combining marks
        decomposed = unicodedata.normalize('NFD', char)
        
        if not decomposed:
            return char
            
        base_char = decomposed[0]
        existing_marks = decomposed[1:]
        
        # Check if base character can have circumflex (only α, η, ι, υ, ω can have circumflex)
        base_vowels = {
            'α': 'α', 'η': 'η', 'ι': 'ι', 
            'υ': 'υ', 'ω': 'ω',
            'Α': 'Α', 'Η': 'Η', 'Ι': 'Ι',
            'Υ': 'Υ', 'Ω': 'Ω',
            # Also handle precomposed characters with breathing or other marks
            'ἀ': 'α', 'ἠ': 'η', 'ἰ': 'ι', 'ὐ': 'υ', 'ὠ': 'ω',
            'ἁ': 'α', 'ἡ': 'η', 'ἱ': 'ι', 'ὑ': 'υ', 'ὡ': 'ω',
            'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
        }
        
        # Get the base vowel (remove any existing accents/breathing)
        base_vowel = base_vowels.get(base_char, base_char)
        if base_vowel not in 'αηιυωΑΗΙΥΩ':
            print(f"Cannot add circumflex to {char} (only α, η, ι, υ, ω can have circumflex)")
            return char
        
        # Remove any existing accent marks from existing marks
        accent_marks = ['\u0301', '\u0300', '\u0342']  # acute, grave, circumflex
        new_marks = [mark for mark in existing_marks if mark not in accent_marks]
        
        # Add circumflex accent in proper position (after breathing, before iota subscript)
        breathing_marks = [mark for mark in new_marks if mark in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        other_marks = [mark for mark in new_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
        
        final_char = base_vowel + ''.join(breathing_marks) + '\u0342' + ''.join(other_marks)
        
        # Normalize to precomposed form if possible
        result = unicodedata.normalize('NFC', final_char)
        print(f"Circumflex accent: {char} -> {result}")
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
        """Handle type change between Starred, Noun, Adjective, Pronoun, and Verb."""
        # Save state before changing (only if event is not None, to avoid duplicate saves)
        if event is not None:
            self.save_current_state()
            
        current_type = self.type_var.get()
        
        if current_type == "Starred":
            # Handle starred items
            self.modes = self.get_starred_display_items()
            if self.modes:
                self.mode_var.set(self.modes[0])
            else:
                self.mode_var.set("No starred items")
                self.modes = ["No starred items"]
        elif current_type == "Noun":
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
        # Save state before changing (only if event is not None, to avoid duplicate saves)
        if event is not None:
            self.save_current_state()
            
        # Handle starred items specially
        if self.type_var.get() == "Starred":
            selected_display = self.mode_var.get()
            
            if selected_display == "No starred items":
                return
            
            # Find the corresponding starred item key
            starred_item_key = None
            for item_key in self.starred_items:
                parts = item_key.split(':')
                if len(parts) >= 2:
                    item_type = parts[0]
                    mode = parts[1]
                    
                    if item_type == "Verb" and len(parts) >= 5:
                        voice = parts[2]
                        tense = parts[3]
                        mood = parts[4]
                        
                        # Create display text that matches get_starred_display_items format
                        if "(" in mode and ")" in mode:
                            verb_name = mode.split("(")[1].split(")")[0]
                            display_text = f"{verb_name} - {tense} {voice} {mood}"
                        else:
                            display_text = f"{mode} - {tense} {voice} {mood}"
                    else:
                        display_text = mode
                    
                    if display_text == selected_display:
                        starred_item_key = item_key
                        break
            
            if starred_item_key:
                # Parse and set the appropriate type and mode
                parts = starred_item_key.split(':')
                original_type = parts[0]
                original_mode = parts[1]
                
                # Temporarily switch to the original type to load the paradigm
                # But keep type_var as "Starred" so navigation works correctly
                
                if original_type == "Verb" and len(parts) >= 5:
                    # For verbs, also set voice, tense, mood
                    voice = parts[2]
                    tense = parts[3]
                    mood = parts[4]
                    
                    # Set verb form variables
                    if hasattr(self, 'voice_var'):
                        self.voice_var.set(voice)
                    if hasattr(self, 'tense_var'):
                        self.tense_var.set(tense)
                    if hasattr(self, 'mood_var'):
                        self.mood_var.set(mood)
                
                # Set the mode to the original mode for table loading
                self.mode_var.set(original_mode)
                
                # Reset the mode display back to the starred display format
                self.mode_var.set(selected_display)
                
                # Force table recreation for starred items
                self.reset_table()
                self.update_word_display()
                return  # Don't call reset_table again at the end
            
        # For verbs, reset tense/voice/mood to appropriate defaults when switching between different verbs
        elif self.type_var.get() == "Verb":
            # Get available options for the new verb
            mode = self.mode_var.get()
            
            # Set tense to first available option
            if hasattr(self, 'tense_var'):
                available_tenses = self.get_base_available_tenses()
                if available_tenses:
                    self.tense_var.set(available_tenses[0])
                else:
                    self.tense_var.set("Present")
            
            # Set voice to Active (all verbs have Active)
            if hasattr(self, 'voice_var'):
                self.voice_var.set("Active")
            
            # Set mood to Indicative (all verbs have Indicative)
            if hasattr(self, 'mood_var'):
                self.mood_var.set("Indicative")
        
        self.reset_table()
        self.update_word_display()

    def on_verb_form_change(self, event):
        """Handle changes to verb tense, voice, or mood selectors."""
        if self.type_var.get() == "Verb":
            # Update available options based on current selections
            self.update_tense_mood_constraints()
            self.reset_table()
            self.update_word_display()
    
    def update_tense_mood_constraints(self):
        """Update available tense and mood options based on current selections."""
        current_tense = self.tense_var.get()
        current_mood = self.mood_var.get()
        current_voice = self.voice_var.get()
        
        # Get available combinations from paradigms
        mode = self.mode_var.get()
        lemma = None
        if "(" in mode and ")" in mode:
            lemma = mode.split("(")[1].split(")")[0]
        
        if lemma:
            available_combinations = self.get_available_combinations_for_verb(lemma)
            
            # Extract available tenses and sort them according to hierarchy
            available_tenses = list(set([combo[0] for combo in available_combinations]))
            available_tenses.sort(key=lambda x: self.verb_tense_order.index(x) if x in self.verb_tense_order else 999)
            
            # If current tense is not available for this verb, reset to first available
            if current_tense not in available_tenses:
                if available_tenses:
                    self.tense_var.set(available_tenses[0])
                    current_tense = available_tenses[0]
            
            # Update tense dropdown
            self.tense_dropdown['values'] = available_tenses
            
            # Extract available moods for current tense and sort them according to hierarchy
            available_moods = list(set([combo[1] for combo in available_combinations if combo[0] == current_tense]))
            available_moods.sort(key=lambda x: self.verb_mood_order.index(x) if x in self.verb_mood_order else 999)
            
            # If current mood is not available for this tense, reset to first available
            if current_mood not in available_moods:
                if available_moods:
                    self.mood_var.set(available_moods[0])
                    current_mood = available_moods[0]
            
            # Update mood dropdown
            self.mood_dropdown['values'] = available_moods
            
            # Handle voice dropdown based on mood
            if current_mood == "Infinitive":
                # For infinitives, all voices are shown in the table, so voice selection is not needed
                # Set voice dropdown to show "All" or just the first available voice
                available_voices = list(set([combo[2] for combo in available_combinations 
                                           if combo[0] == current_tense and combo[1] == "Infinitive"]))
                if available_voices:
                    available_voices.sort(key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                    # For infinitives, just set to the first voice (but table shows all)
                    if hasattr(self, 'voice_dropdown'):
                        self.voice_dropdown['values'] = [available_voices[0]]  # Only show one option
                        self.voice_var.set(available_voices[0])
            else:
                # Extract available voices for current tense and mood and sort them according to hierarchy
                available_voices = list(set([combo[2] for combo in available_combinations 
                                           if combo[0] == current_tense and combo[1] == current_mood]))
                available_voices.sort(key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                
                # Update voice dropdown if it exists
                if hasattr(self, 'voice_dropdown'):
                    self.voice_dropdown['values'] = available_voices
                    
                    # Reset voice if current selection is not available
                    if current_voice not in available_voices:
                        if available_voices:
                            self.voice_var.set(available_voices[0])
        else:
            # Fallback to original logic if no lemma found
            self.update_tense_mood_constraints_fallback()

    def update_tense_mood_constraints_fallback(self):
        """Fallback logic for when lemma cannot be extracted."""
        current_tense = self.tense_var.get()
        current_mood = self.mood_var.get()
        
        # Determine available tenses based on current mood
        if current_mood == "Infinitive":
            # Infinitives only exist for Present, Aorist, Future, Perfect (no Imperfect, no Pluperfect)
            base_tenses = self.get_base_available_tenses()
            available_tenses = [t for t in base_tenses if t not in ["Imperfect", "Pluperfect"]]
            if current_tense in ["Imperfect", "Pluperfect"]:
                self.tense_var.set("Present")
                current_tense = "Present"
        else:
            available_tenses = self.get_base_available_tenses()
        
        # If current tense is not available for this verb, reset to first available
        if current_tense not in available_tenses:
            if available_tenses:
                self.tense_var.set(available_tenses[0])
                current_tense = available_tenses[0]
        
        # Update tense dropdown
        self.tense_dropdown['values'] = available_tenses
        
        # Determine available moods based on current tense
        if current_tense == "Present":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif current_tense == "Imperfect":
            available_moods = ["Indicative", "Optative"]  # No infinitive for imperfect
            if current_mood == "Infinitive":
                self.mood_var.set("Indicative")
        elif current_tense == "Aorist":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif current_tense == "Future":
            available_moods = ["Indicative", "Optative", "Infinitive"]  # No subjunctive for future
            if current_mood == "Subjunctive":
                self.mood_var.set("Indicative")
        elif current_tense == "Perfect":
            available_moods = ["Indicative", "Subjunctive", "Optative", "Imperative", "Infinitive"]
        elif current_tense == "Pluperfect":
            available_moods = ["Indicative", "Optative"]  # No infinitive for pluperfect
            if current_mood == "Infinitive":
                self.mood_var.set("Indicative")
        else:
            available_moods = ["Indicative"]
        
        # Update mood dropdown
        self.mood_dropdown['values'] = available_moods
        
        # Update available voices based on current verb
        mode = self.mode_var.get()
        lemma = None
        if "(" in mode and ")" in mode:
            lemma = mode.split("(")[1].split(")")[0]
        
        if lemma:
            available_voices = self.get_available_voices_for_verb(lemma)
        else:
            # Fallback logic
            active_only_verbs = ["εἰμί", "εἶμι", "βαίνω", "οἶδα", "φημί", "ἵημι"]
            is_active_only = any(verb in mode for verb in active_only_verbs)
            available_voices = ["Active"] if is_active_only else ["Active", "Middle", "Passive"]
        
        # Sort voices according to hierarchy
        available_voices.sort(key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
        
        # Update voice dropdown if it exists
        if hasattr(self, 'voice_dropdown'):
            current_voice = self.voice_var.get()
            current_mood = self.mood_var.get()
            
            # Handle infinitive mood specially
            if current_mood == "Infinitive":
                # For infinitives, only show one voice option since all are displayed in table
                if available_voices:
                    self.voice_dropdown['values'] = [available_voices[0]]
                    self.voice_var.set(available_voices[0])
            else:
                self.voice_dropdown['values'] = available_voices
                
                # Reset voice if current selection is not available
                if current_voice not in available_voices:
                    self.voice_var.set("Active")
    
    def get_base_available_tenses(self):
        """Get the base available tenses for the current verb (before mood constraints)."""
        mode = self.mode_var.get()
        
        if "εἰμί" in mode:
            return ["Present", "Imperfect"]
        elif "οἶδα" in mode:
            return ["Present", "Imperfect"]
        elif "εἶμι" in mode:
            return ["Present", "Imperfect", "Future"]
        elif "βαίνω" in mode:
            # βαίνω only has root aorist paradigms
            return ["Aorist"]
        elif "βάλλω" in mode:
            # βάλλω only has second aorist paradigms for educational focus
            return ["Aorist"]
        elif "λύω" in mode or "Release" in mode:
            # Only λύω has Perfect and Pluperfect paradigms for now
            return ["Present", "Imperfect", "Aorist", "Future", "Perfect", "Pluperfect"]
        else:
            return ["Present", "Imperfect", "Aorist", "Future"]

    def get_current_paradigm(self):
        """Get the currently selected paradigm."""
        mode = self.mode_var.get()
        current_type = self.type_var.get()
        
        # Handle starred items - need to get the original mode for paradigm lookup
        original_mode = mode
        original_type = current_type
        
        if current_type == "Starred":
            # Find the original type and mode for this starred item
            starred_item_key = None
            for item_key in self.starred_items:
                parts = item_key.split(':')
                if len(parts) >= 2:
                    item_type = parts[0]
                    item_mode = parts[1]
                    
                    if item_type == "Verb" and len(parts) >= 5:
                        voice = parts[2]
                        tense = parts[3]
                        mood = parts[4]
                        
                        # Create display text that matches get_starred_display_items format
                        if "(" in item_mode and ")" in item_mode:
                            verb_name = item_mode.split("(")[1].split(")")[0]
                            display_text = f"{verb_name} - {tense} {voice} {mood}"
                        else:
                            display_text = f"{item_mode} - {tense} {voice} {mood}"
                    else:
                        display_text = item_mode
                    
                    if display_text == mode:
                        original_type = item_type
                        original_mode = item_mode
                        break
        
        # For verbs, use dropdown selections to determine paradigm
        if original_type == "Verb":
            # Get the base verb from the mode
            if "λύω" in original_mode:
                verb_base = "luo"
            elif "εἰμί" in original_mode:
                verb_base = "eimi"
            elif "φιλέω" in original_mode:
                verb_base = "phileo"
            elif "τιμάω" in original_mode:
                verb_base = "timao"
            elif "δηλόω" in original_mode:
                verb_base = "deloo"
            elif "βάλλω" in original_mode:
                verb_base = "ballo"
            elif "βαίνω" in original_mode:
                verb_base = "baino"
            elif "δίδωμι" in original_mode:
                verb_base = "didomi"
            elif "τίθημι" in original_mode:
                verb_base = "tithemi"
            elif "ἵστημι" in original_mode:
                verb_base = "histemi"
            elif "οἶδα" in original_mode:
                verb_base = "oida"
            elif "εἶμι" in original_mode:
                verb_base = "eimi_go"
            elif "φημί" in original_mode:
                verb_base = "phemi"
            elif "ἵημι" in original_mode:
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
                    "future": "fut",
                    "perfect": "perf",
                    "pluperfect": "plpf"
                }
                tense_key = tense_map.get(tense_val, tense_val)
                
                # Map mood names to paradigm keys
                mood_map = {
                    "indicative": "ind",
                    "subjunctive": "subj",
                    "optative": "opt",
                    "imperative": "imp",
                    "infinitive": "inf"
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
                if mood_val == "infinitive":
                    # For infinitives, combine all three voices into one paradigm
                    combined_paradigm = {}
                    for voice_name, voice_abbr in voice_map.items():
                        voice_paradigm_key = f"{verb_base}_{tense_key}_{mood_key}_{voice_abbr}"
                        voice_paradigm = self.paradigms.get(voice_paradigm_key)
                        if voice_paradigm:
                            # Extract the infinitive form for this voice
                            inf_key = f"inf_{voice_name}"
                            if inf_key in voice_paradigm:
                                combined_paradigm[inf_key] = voice_paradigm[inf_key]
                    return combined_paradigm if combined_paradigm else None
                else:
                    # For finite verbs, use single paradigm
                    paradigm_key = f"{verb_base}_{tense_key}_{mood_key}_{voice_key}"
                    return self.paradigms.get(paradigm_key)
            else:
                # Fallback to present indicative active
                paradigm_key = f"{verb_base}_pres_ind_act"
                return self.paradigms.get(paradigm_key)
        
        # For non-verbs, use the existing paradigm map
        paradigm_map = {
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
            "Article (ὁ, ἡ, τό)": "article",
            "Personal I (ἐγώ)": "ego",
            "Personal You (σύ)": "sy", 
            "Personal Third Person (αὐτός, αὐτή, αὐτό)": "autos",
            "Demonstrative This (οὗτος, αὕτη, τοῦτο)": "houtos",
            "Relative Who/Which (ὅς, ἥ, ὅ)": "hos",
            "Interrogative Who/What (τίς, τί)": "tis_interrog",
            "Indefinite Someone/Something (τις, τι)": "tis_indef",
            "Present Indicative Active - Release (λύω)": "luo_pres_ind_act",
            "Present Indicative Active - To Be (εἰμί)": "eimi_pres_ind_act",
            "Present Indicative Active - Step (βαίνω)": "baino_pres_ind_act"
        }
        
        paradigm_key = paradigm_map.get(original_mode)
        return self.paradigms.get(paradigm_key) if paradigm_key else None

    def strip_breathing_marks(self, text):
        """Remove breathing marks from Greek text for comparison when ignore_breathings is enabled"""
        if not text:
            return text
        
        # Remove smooth and rough breathing marks
        text = text.replace(SMOOTH_BREATHING, '')
        text = text.replace(ROUGH_BREATHING, '')
        
        # Also remove combined breathing marks that might appear in composed characters
        normalized = unicodedata.normalize('NFD', text)
        
        # Filter out breathing mark characters
        breathing_marks = {'\u0313', '\u0314'}  # smooth and rough breathing
        filtered = ''.join(char for char in normalized if char not in breathing_marks)
        
        return unicodedata.normalize('NFC', filtered)

    def compare_answers(self, user_input, correct_answer):
        """Compare user input with correct answer, respecting configuration settings"""
        if not user_input or not correct_answer:
            return False
        
        # Apply normalization based on settings
        processed_user = user_input.strip()
        processed_correct = correct_answer.strip()
        
        # Handle prefill stems mode - check if user input combines correctly with prefilled stem
        if self.config.prefill_stems.get():
            # In prefill mode, the user input should be the complete word they've built
            # We compare against the stored full answer
            pass  # The regular comparison below will handle this correctly
        
        # Strip breathing marks if option is enabled
        if self.config.ignore_breathings.get():
            processed_user = self.strip_breathing_marks(processed_user)
            processed_correct = self.strip_breathing_marks(processed_correct)
        
        return processed_user == processed_correct
    
    def validate_prefilled_answer(self, entry_key, user_input):
        """Validate user input for prefilled stem entries"""
        if entry_key not in self.entries:
            return False
        
        entry = self.entries[entry_key]
        if not hasattr(entry, '_full_answer'):
            return False
        
        expected_full = entry._full_answer
        
        # Handle contractions if this is a contract verb
        current_type = self.type_var.get()
        if current_type == "Verb" and hasattr(entry, '_stem') and hasattr(entry, '_ending'):
            # For contract verbs, the user input might need contraction
            contracted_form = self.handle_contractions(entry._stem, user_input[len(entry._stem):], "verb")
            return self.compare_answers(contracted_form, expected_full)
        
        # For non-contract cases, direct comparison
        return self.compare_answers(user_input, expected_full)
    
    def extract_stem_and_ending(self, word, paradigm_type=None):
        """Extract the stem and ending from a Greek word using paradigm-aware analysis"""
        if not word:
            return "", ""
        
        # Get the current paradigm to do smart stem extraction
        current_paradigm = self.get_current_paradigm()
        if current_paradigm:
            return self.smart_stem_extraction(word, current_paradigm, paradigm_type)
        
        # Fallback to basic extraction if no paradigm available
        return self.basic_stem_extraction(word, paradigm_type)
    
    def smart_stem_extraction(self, target_word, paradigm, paradigm_type):
        """Use paradigm data to find the most likely stem for a word"""
        # Collect all forms from the paradigm to analyze
        all_forms = []
        current_type = self.type_var.get()
        
        if current_type == "Verb":
            # For verbs, use specialized verb stem extraction
            return self.extract_verb_stem(target_word, paradigm)
        elif current_type == "Adjective":
            # Collect from all genders
            for gender in ["masculine", "feminine", "neuter"]:
                if gender in paradigm:
                    for key, value in paradigm[gender].items():
                        if value and isinstance(value, str):
                            all_forms.append(value)
        elif current_type == "Pronoun":
            # Handle both simple and gendered pronoun structures
            for key, value in paradigm.items():
                if isinstance(value, dict):
                    # Gendered structure
                    for subkey, subvalue in value.items():
                        if subvalue and isinstance(subvalue, str):
                            all_forms.append(subvalue)
                elif value and isinstance(value, str):
                    # Simple structure
                    all_forms.append(value)
        else:
            # Noun - simple structure
            for key, value in paradigm.items():
                if value and isinstance(value, str) and key not in ["type", "gender", "lemma"]:
                    all_forms.append(value)
        
        # Find the common stem by analyzing all forms
        if all_forms and target_word in all_forms:
            return self.find_stem_from_paradigm_forms(target_word, all_forms, paradigm_type)
        
        # If target word not found in paradigm, use basic extraction
        return self.basic_stem_extraction(target_word, paradigm_type)
    
    def extract_verb_stem(self, target_word, paradigm):
        """Extract verb stem using tense/mood/voice-specific analysis"""
        if not paradigm or "type" not in paradigm or paradigm["type"] != "verb":
            return self.basic_stem_extraction(target_word, "verb")
        
        # Get tense, mood, voice information
        tense = paradigm.get("tense", "present")
        mood = paradigm.get("mood", "indicative") 
        voice = paradigm.get("voice", "active")
        lemma = paradigm.get("lemma", "")
        
        # Collect all verb forms from this specific tense/mood/voice
        verb_forms = []
        for key, value in paradigm.items():
            if key not in ["type", "tense", "mood", "voice", "lemma"] and value and isinstance(value, str):
                verb_forms.append(value)
        
        if not verb_forms:
            return self.basic_stem_extraction(target_word, "verb")
        
        # Find the consistent stem for this entire tense paradigm
        consistent_stem = self.get_consistent_verb_stem(verb_forms, tense, mood, voice, lemma)
        
        # Apply this consistent stem to the target word
        return self.apply_consistent_stem(target_word, consistent_stem)
    
    def get_consistent_verb_stem(self, verb_forms, tense, mood, voice, lemma):
        """Get the consistent stem for all forms in this tense paradigm"""
        
        # Remove accents for analysis
        def remove_accents_for_stem_analysis(word):

            nfd = unicodedata.normalize('NFD', word)
            accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
            filtered = ''.join(char for char in nfd if char not in accent_marks)
            return unicodedata.normalize('NFC', filtered)
        
        accent_free_forms = [remove_accents_for_stem_analysis(form) for form in verb_forms]
        
        # Special handling for infinitives - they have only one form
        if mood == "infinitive":
            current_paradigm = self.get_current_paradigm()
            return self.extract_infinitive_stem_from_paradigm(accent_free_forms, tense, voice, lemma, current_paradigm)
        
        # Handle different tense systems to find the consistent stem
        if tense == "present":
            return self.extract_present_stem_from_paradigm(accent_free_forms, lemma)
            
        elif tense == "imperfect":
            # Imperfect uses present stem + augment
            # Remove augments to find the underlying present stem
            unaugmented_forms = [self.remove_augment(form) for form in accent_free_forms]
            present_stem = self.extract_present_stem_from_paradigm(unaugmented_forms, lemma)
            # For imperfect, stem includes the augment when it appears
            return f"ἐ{present_stem}" if present_stem else present_stem
            
        elif tense == "aorist":
            # Aorist stem includes augment + aorist marker
            # Check for root aorist information in current paradigm
            current_paradigm = self.get_current_paradigm()
            return self.extract_aorist_stem_from_paradigm(accent_free_forms, lemma, current_paradigm)
            
        elif tense == "future":
            # Future stem usually has σ marker
            return self.extract_future_stem_from_paradigm(accent_free_forms, lemma)
            
        elif tense == "perfect":
            # Perfect stem has reduplication + perfect marker
            return self.extract_perfect_stem_from_paradigm(accent_free_forms, lemma)
            
        elif tense == "pluperfect":
            # Pluperfect uses perfect stem + augment (like imperfect uses present stem + augment)
            # Remove augments to find the underlying perfect stem
            unaugmented_forms = [self.remove_augment(form) for form in accent_free_forms]
            perfect_stem = self.extract_perfect_stem_from_paradigm(unaugmented_forms, lemma)
            # For pluperfect, stem includes the augment when it appears
            return f"ἐ{perfect_stem}" if perfect_stem else perfect_stem
            
        else:
            # Fallback to basic common prefix for other tenses
            return self.find_common_verb_stem(accent_free_forms)
    
    def apply_consistent_stem(self, target_word, consistent_stem):
        """Apply the consistent stem to extract stem and ending from target word"""
        if not consistent_stem:
            return self.basic_stem_extraction(target_word, "verb")
        
        # Remove accents for comparison
        def remove_accents_for_stem_analysis(word):

            nfd = unicodedata.normalize('NFD', word)
            accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
            filtered = ''.join(char for char in nfd if char not in accent_marks)
            return unicodedata.normalize('NFC', filtered)
        
        accent_free_target = remove_accents_for_stem_analysis(target_word)
        accent_free_stem = remove_accents_for_stem_analysis(consistent_stem)
        
        # Find where the stem ends in the target word
        if accent_free_target.startswith(accent_free_stem):
            stem_length = len(accent_free_stem)
            # Map back to original word with accents
            original_stem = target_word[:stem_length]
            original_ending = target_word[stem_length:]
            return original_stem, original_ending
        else:
            # If stem doesn't match exactly, try to find the best match
            # This handles cases where augments or other modifications occur
            return self.basic_stem_extraction(target_word, "verb")
    
    def get_verb_stem_by_tense(self, target_word, verb_forms, tense, mood, voice, lemma):
        """Get verb stem based on tense/mood/voice system"""
        
        # Remove accents for analysis
        def remove_accents_for_stem_analysis(word):

            nfd = unicodedata.normalize('NFD', word)
            accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
            filtered = ''.join(char for char in nfd if char not in accent_marks)
            return unicodedata.normalize('NFC', filtered)
        
        accent_free_forms = [remove_accents_for_stem_analysis(form) for form in verb_forms]
        accent_free_target = remove_accents_for_stem_analysis(target_word)
        
        # Handle different tense systems
        if tense == "present":
            # Present stem system - find common stem without endings
            stem = self.extract_present_stem(accent_free_forms, accent_free_target)
            
        elif tense == "imperfect":
            # Imperfect uses present stem + augment - remove augment first
            unaugmented_forms = [self.remove_augment(form) for form in accent_free_forms]
            stem = self.extract_present_stem(unaugmented_forms, self.remove_augment(accent_free_target))
            
        elif tense == "future":
            # Future stem system - usually present stem + σ (or contracted)
            stem = self.extract_future_stem(accent_free_forms, accent_free_target, lemma)
            
        elif tense == "aorist":
            # Aorist stem system - may be sigmatic (σ) or strong aorist
            stem = self.extract_aorist_stem(accent_free_forms, accent_free_target, lemma)
            
        elif tense == "perfect":
            # Perfect stem system - reduplication + stem + perfect marker
            stem = self.extract_perfect_stem(accent_free_forms, accent_free_target, lemma)
            
        else:
            # Fallback to basic common prefix
            stem = self.find_common_verb_stem(accent_free_forms)
        
        # Map back to original word with accents
        if accent_free_target.startswith(stem):
            stem_length = len(stem)
            original_stem = target_word[:stem_length]
            original_ending = target_word[stem_length:]
            return original_stem, original_ending
        else:
            return self.basic_stem_extraction(target_word, "verb")
    
    def extract_infinitive_stem_from_paradigm(self, accent_free_forms, tense, voice, lemma, paradigm=None):
        """Extract infinitive stem based on known infinitive endings"""
        if not accent_free_forms:
            return ""
        
        infinitive_form = accent_free_forms[0]  # Only one form for infinitives
        
        # Greek infinitive endings by tense and voice:
        # Present Active: -ειν (λύειν)
        # Present Middle/Passive: -εσθαι (λύεσθαι)
        # Aorist Active: -σαι (λύσαι)
        # Aorist Middle: -σασθαι (λύσασθαι)
        # Aorist Passive: -θηναι (λυθῆναι)
        # Root Aorist Active: -ναι (βῆναι)
        # Perfect Active: -εναι (λελυκέναι)
        # Perfect Middle/Passive: -σθαι (λελύσθαι)
        
        if tense == "present":
            if voice == "active":
                # Present active infinitive: λύειν → λυ
                if infinitive_form.endswith('ειν'):
                    return infinitive_form[:-3]
                elif infinitive_form.endswith('ναι'):  # εἶναι type
                    return infinitive_form[:-3]
            elif voice in ["middle", "passive"]:
                # Present middle/passive infinitive: λύεσθαι → λυ
                if infinitive_form.endswith('εσθαι'):
                    return infinitive_form[:-5]  # Remove εσθαι to get λυ
                elif infinitive_form.endswith('σθαι'):  # shorter ending
                    return infinitive_form[:-4]
                    
        elif tense == "aorist":
            # Check for root aorist first
            if paradigm and paradigm.get("aorist_type") == "root":
                aorist_root = paradigm.get("aorist_root", "")
                if aorist_root and voice == "active":
                    # Root aorist infinitive: βῆναι → βη
                    if infinitive_form.endswith('ναι'):
                        return aorist_root  # Direct root without augment for infinitive
                    elif infinitive_form.endswith('αι'):
                        return aorist_root
            
            # Regular aorist patterns
            if voice == "active":
                # Aorist active infinitive: λῦσαι → λυ (remove σαι)
                if infinitive_form.endswith('σαι'):
                    return infinitive_form[:-3]  # Remove σαι to get λυ
                elif infinitive_form.endswith('αι'):  # strong aorist
                    return infinitive_form[:-2]
            elif voice == "middle":
                # Aorist middle infinitive: λύσασθαι → λυ
                if infinitive_form.endswith('σασθαι'):
                    return infinitive_form[:-6]  # Remove σασθαι to get λυ
                elif infinitive_form.endswith('ασθαι'):  # strong aorist
                    return infinitive_form[:-5]
            elif voice == "passive":
                # Aorist passive infinitive: λυθῆναι → λυθ
                if infinitive_form.endswith('θηναι'):
                    return infinitive_form[:-5]
                elif infinitive_form.endswith('ηναι'):
                    return infinitive_form[:-4]
                    
        elif tense == "future":
            if voice == "active":
                # Future active infinitive: λύσειν → λυσ
                if infinitive_form.endswith('σειν'):
                    return infinitive_form[:-3]  # Remove ειν to get λυσ
                elif infinitive_form.endswith('ειν'):
                    return infinitive_form[:-3]
            elif voice in ["middle", "passive"]:
                # Future middle/passive infinitive: λύσεσθαι → λυσ
                if infinitive_form.endswith('σεσθαι'):
                    return infinitive_form[:-5]  # Remove εσθαι to get λυσ
                elif infinitive_form.endswith('εσθαι'):
                    return infinitive_form[:-5]
                    
        elif tense == "perfect":
            if voice == "active":
                # Perfect active infinitive: λελυκέναι → λελυκ
                if infinitive_form.endswith('εναι'):
                    return infinitive_form[:-4]
                elif infinitive_form.endswith('ναι'):
                    return infinitive_form[:-3]
            elif voice in ["middle", "passive"]:
                # Perfect middle/passive infinitive: λελύσθαι → λελυ
                if infinitive_form.endswith('σθαι'):
                    return infinitive_form[:-4]
                elif infinitive_form.endswith('θαι'):
                    return infinitive_form[:-3]
        
        # Fallback: return most of the form
        return infinitive_form[:-2] if len(infinitive_form) > 2 else infinitive_form

    def extract_present_stem_from_paradigm(self, accent_free_forms, lemma):
        """Extract present stem from all forms in present paradigm"""
        # Handle contract verbs specially
        if self.is_contract_verb_by_lemma(lemma):
            return self.extract_contract_verb_stem(lemma, accent_free_forms)
        
        # For regular verbs, find the common stem across all forms
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # For thematic verbs, remove theme vowel if present
        if self.is_thematic_verb_pattern(accent_free_forms):
            if len(common_stem) > 1 and common_stem[-1] in ['ο', 'ε']:
                common_stem = common_stem[:-1]
        
        return common_stem
    
    def extract_aorist_stem_from_paradigm(self, accent_free_forms, lemma, paradigm=None):
        """Extract aorist stem from all forms in aorist paradigm"""
        # Check for root aorist first
        if paradigm and paradigm.get("aorist_type") == "root":
            aorist_root = paradigm.get("aorist_root", "")
            if aorist_root:
                # For root aorists like βαίνω → ἔβην, stem is augment + root
                return f"ἐ{aorist_root}" if aorist_root else aorist_root
        
        # For regular aorists: λύω → ἔλυσα, ἔλυσας, ἔλυσε, ἐλύσαμεν, ἐλύσατε, ἔλυσαν
        # The consistent stem is ἐλυσ (including augment + σ marker)
        
        # Find the common prefix across all aorist forms
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # For sigmatic aorist, the stem includes the σ
        # For strong aorist, it's the modified root
        
        # Check if this looks like a sigmatic aorist (has σ in common stem)
        if 'σ' in common_stem:
            # Find where the σ is and include it in the stem
            sigma_pos = common_stem.find('σ')
            if sigma_pos >= 0:
                return common_stem[:sigma_pos + 1]  # Include the σ
        
        return common_stem
    
    def extract_future_stem_from_paradigm(self, accent_free_forms, lemma):
        """Extract future stem from all forms in future paradigm"""
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # Future usually has σ marker
        if 'σ' in common_stem:
            sigma_pos = common_stem.find('σ')
            if sigma_pos >= 0:
                return common_stem[:sigma_pos + 1]  # Include the σ
        
        return common_stem
    
    def extract_perfect_stem_from_paradigm(self, accent_free_forms, lemma):
        """Extract perfect stem from all forms in perfect paradigm"""
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # Perfect has reduplication + κ marker (active)
        # For now, return the common stem as-is
        return common_stem
        """Extract present stem from present tense forms"""
        # Check if this is a contract verb by examining the lemma context
        # Contract verbs show contraction in their paradigm forms
        current_paradigm = self.get_current_paradigm()
        lemma = current_paradigm.get("lemma", "") if current_paradigm else ""
        
        # Handle contract verbs specially
        if self.is_contract_verb_by_lemma(lemma):
            return self.extract_contract_verb_stem(lemma, accent_free_forms)
        
        # Regular thematic/athematic verbs
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # For thematic verbs, stem usually ends before the theme vowel
        # Check if this looks like a thematic verb pattern
        if self.is_thematic_verb_pattern(accent_free_forms):
            # Remove theme vowel from stem (ο/ε alternation)
            if len(common_stem) > 1 and common_stem[-1] in ['ο', 'ε']:
                common_stem = common_stem[:-1]
        
        return common_stem
    
    def extract_future_stem(self, accent_free_forms, target_form, lemma):
        """Extract future stem - usually present stem + σ"""
        # Future often has σ marker: λυσω, λυσεις, λυσει, etc.
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # If stem ends in σ, that's probably the future marker
        if common_stem.endswith('σ'):
            # The true stem is before the σ
            return common_stem[:-1]
        
        # For contract verbs, the σ may have caused contraction
        # φιλεω → φιληστε becomes φιλησ- stem
        return common_stem
    
    def extract_aorist_stem(self, accent_free_forms, target_form, lemma):
        """Extract aorist stem - sigmatic or strong aorist"""
        # Remove augments first for aorist forms
        unaugmented_forms = [self.remove_augment(form) for form in accent_free_forms]
        common_stem = self.find_common_verb_stem(unaugmented_forms)
        
        # Sigmatic aorist: λυσα, λυσας, λυσε → λυσ- stem
        if common_stem.endswith('σ'):
            return common_stem
        
        # Strong aorist: εβαλον, εβαλες, εβαλε → βαλ- stem  
        return common_stem
    
    def extract_perfect_stem(self, accent_free_forms, target_form, lemma):
        """Extract perfect stem - has reduplication + stem + κ marker"""
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # Perfect active usually has -κ- marker: λελυκα, λελυκας, etc.
        if 'κ' in common_stem:
            # Include the κ in the stem for perfect
            return common_stem
        
        # For perfect passive, no κ marker
        return common_stem
    
    def find_common_verb_stem(self, accent_free_forms):
        """Find the longest common prefix among verb forms"""
        if not accent_free_forms:
            return ""
        
        if len(accent_free_forms) == 1:
            # Single form - take most of it as stem, leave short ending
            form = accent_free_forms[0]
            if len(form) > 3:
                return form[:-2]  # Leave 2 chars for ending
            else:
                return form[:-1] if len(form) > 1 else form
        
        # Multiple forms - find longest common prefix
        min_length = min(len(form) for form in accent_free_forms)
        common_prefix = ""
        
        for i in range(min_length):
            char = accent_free_forms[0][i]
            if all(form[i] == char for form in accent_free_forms):
                common_prefix += char
            else:
                break
        
        # Ensure reasonable minimum stem length
        if len(common_prefix) < 2:
            # Take at least 2 characters from the shortest form
            if accent_free_forms:
                shortest = min(accent_free_forms, key=len)
                return shortest[:max(2, len(shortest) - 2)]
        
        return common_prefix
    
    def is_thematic_verb_pattern(self, accent_free_forms):
        """Check if this looks like a thematic verb (ο/ε theme vowel pattern)"""
        # Look for alternating ο/ε pattern typical of thematic verbs
        # λυω, λυεις, λυει → shows ο/ε alternation
        theme_vowels = set()
        for form in accent_free_forms:
            if len(form) >= 3:
                # Look at the vowel before the ending
                potential_theme = form[-3:-2] if len(form) > 3 else form[-2:-1]
                if potential_theme in ['ο', 'ε']:
                    theme_vowels.add(potential_theme)
        
        # If we see both ο and ε, it's likely thematic
        return 'ο' in theme_vowels and 'ε' in theme_vowels
    
    def find_stem_from_paradigm_forms(self, target_word, all_forms, paradigm_type):
        """Analyze multiple paradigm forms to determine the correct stem"""
        # Remove duplicates and empty forms
        unique_forms = list(set(form for form in all_forms if form and len(form) > 1))
        
        if len(unique_forms) < 2:
            return self.basic_stem_extraction(target_word, paradigm_type)
        
        # For consistent stem finding, we need to remove accents first
        # because Greek accents shift but the stem remains the same
        def remove_accents_for_stem_analysis(word):
            """Remove accents for stem analysis while preserving base characters"""

            # Normalize to decomposed form
            nfd = unicodedata.normalize('NFD', word)
            # Remove accent marks but keep breathing marks for now
            accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}  # acute, grave, circumflex, diaeresis
            filtered = ''.join(char for char in nfd if char not in accent_marks)
            return unicodedata.normalize('NFC', filtered)
        
        # Remove accents from all forms for analysis
        accent_free_forms = [remove_accents_for_stem_analysis(form) for form in unique_forms]
        accent_free_target = remove_accents_for_stem_analysis(target_word)
        
        # Find the longest common prefix among accent-free forms
        def longest_common_prefix(strings):
            if not strings:
                return ""
            # Don't go shorter than 2 characters for stem
            min_len = min(len(s) for s in strings)
            for i in range(min_len):
                char = strings[0][i]
                if not all(s[i] == char for s in strings):
                    return strings[0][:max(2, i)]  # Ensure minimum 2 chars
            return strings[0][:min_len]
        
        # Special handling for verbs with augments
        if paradigm_type == "verb":
            # Remove potential augments before finding common stem
            cleaned_forms = []
            for form in accent_free_forms:
                cleaned = self.remove_augment(form)
                cleaned_forms.append(cleaned)
            common_stem = longest_common_prefix(cleaned_forms)
        else:
            # For nouns/adjectives, work with accent-free forms directly
            common_stem = longest_common_prefix(accent_free_forms)
        
        # Apply declension-specific stem finding
        if paradigm_type in ["noun", "adjective"]:
            common_stem = self.refine_stem_by_declension(common_stem, accent_free_forms, paradigm_type)
        
        # Ensure minimum stem length (Greek stems are rarely shorter than 3 characters)
        if len(common_stem) < 3 and len(accent_free_target) > 4:
            # For longer words, stem should be at least 3 characters
            common_stem = accent_free_target[:3]
        elif len(common_stem) < 2:
            # Absolute minimum of 2 characters
            common_stem = accent_free_target[:2]
        
        # Now find this stem in the original target word (with accents)
        # We need to map back from accent-free to accented
        if accent_free_target.startswith(common_stem):
            # Find where the stem ends in the original word
            stem_end_pos = len(common_stem)
            
            # The stem in the original word is the first stem_end_pos characters
            original_stem = target_word[:stem_end_pos]
            original_ending = target_word[stem_end_pos:]
            
            return original_stem, original_ending
        else:
            # Fallback if mapping failed
            return self.basic_stem_extraction(target_word, paradigm_type)
    
    def refine_stem_by_declension(self, preliminary_stem, accent_free_forms, paradigm_type):
        """Refine stem based on declension patterns"""
        if not preliminary_stem or len(preliminary_stem) < 2:
            return preliminary_stem
        
        # Analyze the endings to determine declension type
        endings = []
        for form in accent_free_forms:
            if form.startswith(preliminary_stem):
                ending = form[len(preliminary_stem):]
                endings.append(ending)
        
        # Look for characteristic declension patterns
        endings_set = set(endings)
        
        # First declension (like μουσα): endings include α, αν, ης, η, αι, ας, ων, αις
        first_decl_endings = {'α', 'αν', 'ης', 'η', 'αι', 'ας', 'ων', 'αις'}
        
        # Second declension (like λογος): endings include ος, ον, ου, ω, οι, ους, ων, οις
        second_decl_endings = {'ος', 'ον', 'ου', 'ω', 'οι', 'ους', 'ων', 'οις'}
        
        # Check if endings match declension patterns
        if endings_set.intersection(first_decl_endings) and len(preliminary_stem) >= 3:
            # First declension - usually consistent stem
            return preliminary_stem
        elif endings_set.intersection(second_decl_endings) and len(preliminary_stem) >= 3:
            # Second declension - usually consistent stem  
            return preliminary_stem
        else:
            # Third declension or other - may have stem changes
            # For now, keep the preliminary stem but ensure it's reasonable length
            if len(preliminary_stem) >= 3:
                return preliminary_stem
            else:
                # Try to extend the stem by one character if possible
                if accent_free_forms and len(accent_free_forms[0]) > len(preliminary_stem):
                    return accent_free_forms[0][:len(preliminary_stem) + 1]
        
        return preliminary_stem
    
    def remove_augment(self, verb_form):
        """Remove temporal augments from Greek verb forms"""
        if not verb_form:
            return verb_form
        
        # Syllabic augment (ἐ-) - most common
        if verb_form.startswith('ἐ') and len(verb_form) > 1:
            return verb_form[1:]
        
        # Temporal augment for vowel-initial verbs (lengthening)
        # α → η, ε → η, ο → ω, etc.
        augment_mappings = {
            'η': ['α', 'ε'],  # η could be augmented α or ε
            'ω': ['ο'],       # ω could be augmented ο
            'ῃ': ['ᾳ'],       # ῃ could be augmented ᾳ
        }
        
        if len(verb_form) > 2:
            first_char = verb_form[0]
            if first_char in augment_mappings:
                # Try replacing with each possible unaugmented form
                for original in augment_mappings[first_char]:
                    return original + verb_form[1:]
        
        return verb_form
    
    def handle_contractions(self, stem, ending, paradigm_type):
        """Handle Greek vowel contractions between stem and ending"""
        if not stem or not ending or paradigm_type != "verb":
            return stem + ending
        
        # Contract verb patterns (common contractions)
        stem_final = stem[-1] if stem else ''
        ending_initial = ending[0] if ending else ''
        
        # α-contract verbs (like τιμάω)
        if stem_final == 'α':
            contractions = {
                'ε': 'α',    # αε → α
                'ει': 'ᾳ',   # αει → ᾳ  
                'η': 'α',    # αη → α
                'ο': 'ω',    # αο → ω
                'ου': 'ω',   # αου → ω
                'ω': 'ω',    # αω → ω
            }
            if ending in contractions:
                return stem[:-1] + contractions[ending]
        
        # ε-contract verbs (like φιλέω)
        elif stem_final == 'ε':
            contractions = {
                'ε': 'ει',   # εε → ει
                'ει': 'ει',  # εει → ει
                'η': 'η',    # εη → η
                'ο': 'ου',   # εο → ου
                'ου': 'ου',  # εου → ου
                'ω': 'ω',    # εω → ω
            }
            if ending in contractions:
                return stem[:-1] + contractions[ending]
        
        # ο-contract verbs (like δηλόω)
        elif stem_final == 'ο':
            contractions = {
                'ε': 'ου',   # οε → ου
                'ει': 'οι',  # οει → οι
                'η': 'ω',    # οη → ω
                'ο': 'ου',   # οο → ου
                'ου': 'ου',  # οου → ου
                'ω': 'ω',    # οω → ω
            }
            if ending in contractions:
                return stem[:-1] + contractions[ending]
        
        # No contraction needed
        return stem + ending
    
    def basic_stem_extraction(self, word, paradigm_type=None):
        """Fallback basic stem extraction when paradigm analysis fails"""
        if not word:
            return "", ""
        
        # Enhanced ending patterns based on paradigm type
        if paradigm_type == "noun":
            common_endings = ['ους', 'ων', 'οις', 'ας', 'αις', 'ος', 'η', 'ον', 'ου', 'ες', 'α']
        elif paradigm_type == "verb": 
            common_endings = ['ουσι', 'ομεν', 'ετε', 'εις', 'ει', 'ω', 'ον', 'ες', 'ε']
        elif paradigm_type == "adjective":
            common_endings = ['ους', 'ων', 'οις', 'ας', 'αις', 'ος', 'η', 'ον', 'ου', 'ες', 'α']
        else:
            # General patterns
            common_endings = ['ους', 'ων', 'οις', 'ας', 'αις', 'ουσι', 'ομεν', 'ετε', 
                            'ος', 'η', 'ον', 'ου', 'ες', 'α', 'εις', 'ει', 'ω']
        
        # Try to find the longest matching ending
        for ending in sorted(common_endings, key=len, reverse=True):
            if word.endswith(ending) and len(word) > len(ending):
                stem = word[:-len(ending)]
                # Don't leave too short a stem
                if len(stem) >= 2:
                    return stem, ending
        
        # If no good ending found, use intelligent split
        # For Greek, usually 2-3 characters for ending is reasonable
        if len(word) <= 3:
            return word[:-1], word[-1:]
        elif len(word) <= 5:
            return word[:-2], word[-2:]
        else:
            return word[:-3], word[-3:]
    
    def prefill_entry_with_stem(self, entry_key, full_word):
        """Prefill an entry field with just the stem, leaving ending for user"""
        if entry_key not in self.entries or not full_word:
            return
        
        entry = self.entries[entry_key]
        current_type = self.type_var.get()
        
        # Determine paradigm type for better stem extraction
        paradigm_type = "noun"
        if current_type == "Verb":
            paradigm_type = "verb"
        elif current_type in ["Adjective", "Pronoun"]:
            paradigm_type = "adjective"
        
        # Get the appropriate stem based on the specific form
        stem = self.get_context_appropriate_stem(entry_key, full_word, paradigm_type)
        
        if not stem:
            # Fallback to regular extraction
            stem, ending = self.extract_stem_and_ending(full_word, paradigm_type)
        
        # Clear the entry and insert just the stem
        entry.delete(0, tk.END)
        entry.insert(0, stem)
        
        # Store the full answer and stem info for checking purposes
        entry._full_answer = full_word
        entry._stem = stem

    def get_context_appropriate_stem(self, entry_key, full_word, paradigm_type):
        """Get the appropriate stem based on the specific grammatical context"""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return None
            
        current_mode = self.mode_var.get()
        current_type = self.type_var.get()
        
        if current_type == "Verb":
            return self.get_verb_context_stem(entry_key, full_word, current_paradigm, current_mode)
        else:
            # For nouns, adjectives, pronouns - use regular extraction for now
            stem, ending = self.extract_stem_and_ending(full_word, paradigm_type)
            return stem
    
    def get_verb_context_stem(self, entry_key, full_word, paradigm, current_mode):
        """Get context-appropriate stem for verbs, handling irregular verbs and mi verbs"""
        # Extract lemma from current mode
        lemma = None
        if "(" in current_mode and ")" in current_mode:
            lemma = current_mode.split("(")[1].split(")")[0]
        
        tense = paradigm.get("tense", "present")
        mood = paradigm.get("mood", "indicative")
        voice = paradigm.get("voice", "active")
        
        # Determine if this is singular or plural
        is_plural = entry_key.endswith("_pl")
        
        # Special handling for irregular and mi verbs
        if lemma:
            special_stem = self.get_special_verb_stem(lemma, entry_key, tense, mood, voice, is_plural)
            if special_stem:
                return special_stem
        
        # Handle contract verbs
        if self.is_contract_verb(paradigm):
            stem, ending = self.extract_stem_and_ending(full_word, "verb")
            return self.get_uncontracted_stem(full_word, stem, ending)
        
        # Fallback to regular stem extraction
        stem, ending = self.extract_stem_and_ending(full_word, "verb")
        return stem
    
    def get_special_verb_stem(self, lemma, entry_key, tense, mood, voice, is_plural):
        """Get special stems for irregular verbs and mi verbs"""
        
        # Define special stem patterns for irregular and mi verbs
        special_stems = {
            "οἶδα": {
                "present": {
                    "singular": "οἰ",
                    "plural": "ἰσ"
                },
                # Add other tenses as needed
            },
            "ἵημι": {
                "present": {
                    "all": "ἱ"  # Shorter stem for all forms
                },
                "aorist": {
                    "all": "ἡ"  # Different stem for aorist
                }
            },
            "φημί": {
                "present": {
                    "singular": "φη",  # φη- for singular present forms
                    "plural": "φα"     # φα- for plural present forms
                },
                "imperfect": {
                    "singular": "φη",  # φη- for singular imperfect forms  
                    "plural": "φα"     # φα- for plural imperfect forms
                },
                "future": {
                    "all": "φη"       # φη- for future forms
                }
            },
            "δίδωμι": {
                "present": {
                    "singular": "διδο",  # διδο- for singular present forms
                    "plural": "διδο"     # διδο- for plural present forms  
                },
                "aorist": {
                    "singular": "δω",    # δω- for singular aorist (ἔδωκα)
                    "plural": "δο"       # δο- for plural aorist (ἔδομεν)
                }
            },
            "τίθημι": {
                "present": {
                    "singular": "τιθε",  # τιθε- for singular present forms
                    "plural": "τιθε"     # τιθε- for plural present forms
                },
                "aorist": {
                    "singular": "θη",    # θη- for singular aorist (ἔθηκα)
                    "plural": "θε"       # θε- for plural aorist (ἔθεμεν)
                }
            },
            "ἵστημι": {
                "present": {
                    "singular": "ἱστα",  # ἱστα- for singular present forms
                    "plural": "ἱστα"     # ἱστα- for plural present forms
                },
                "aorist": {
                    "singular": "στησ",  # στησ- for singular aorist (ἔστησα)
                    "plural": "στη"      # στη- for plural aorist (ἔστημεν)
                }
            }
        }
        
        if lemma not in special_stems:
            return None
            
        verb_stems = special_stems[lemma]
        
        # Get tense-specific stems
        if tense in verb_stems:
            tense_stems = verb_stems[tense]
            
            # Check for all-forms stem first
            if "all" in tense_stems:
                return tense_stems["all"]
            
            # Check for singular/plural specific stems
            number_key = "plural" if is_plural else "singular"
            if number_key in tense_stems:
                return tense_stems[number_key]
                
        return None
    
    def is_contract_verb_by_lemma(self, lemma):
        """Check if a verb is a contract verb based on its lemma"""
        if not lemma:
            return False
        return lemma.endswith('άω') or lemma.endswith('έω') or lemma.endswith('όω')
    
    def extract_contract_verb_stem(self, lemma, contracted_forms):
        """Extract the practical stem for contract verbs (what remains after contraction)"""
        if not lemma:
            # Fallback: analyze contracted forms to find practical stem
            common_stem = self.find_common_verb_stem(contracted_forms)
            return common_stem
        
        # For contract verbs, the practical stem is what students see after contraction
        if lemma.endswith('άω'):
            return lemma[:-2]  # τιμάω → τιμ (practical stem after contraction)
        elif lemma.endswith('έω'):
            return lemma[:-2]  # φιλέω → φιλ (practical stem after contraction)
        elif lemma.endswith('όω'):
            return lemma[:-2]  # δηλόω → δηλ (practical stem after contraction)
        
        # Fallback for other patterns
        return lemma[:-1] if lemma.endswith('ω') else lemma

    def is_contract_verb(self, paradigm):
        """Check if the current verb paradigm represents a contract verb"""
        # Look for characteristic contract verb endings in the paradigm
        sample_forms = []
        for key, value in paradigm.items():
            if isinstance(value, str) and key not in ["type", "lemma"]:
                sample_forms.append(value)
        
        # Contract verbs often have ω, ᾷς, ᾷ endings instead of regular ω, εις, ει
        contract_indicators = ['ᾷς', 'ᾷ', 'εῖς', 'εῖ', 'οῦς', 'οῖ', 'ῶ']
        return any(any(form.endswith(indicator) for indicator in contract_indicators) 
                  for form in sample_forms)
    
    def get_uncontracted_stem(self, full_word, contracted_stem, ending):
        """Get the uncontracted stem for contract verbs"""
        # This is a simplified approach - in practice, this would need
        # more sophisticated analysis of the contract patterns
        
        # Look at the full word to see if we can identify the contract vowel
        if len(full_word) >= 3:
            # Check for common contract patterns
            if 'ω' in full_word[-2:] and not ending.startswith('ω'):
                # Might be α-contract (αω → ω) or ο-contract (οω → ω)
                if contracted_stem and contracted_stem[-1] not in ['α', 'ο']:
                    # Try adding contract vowel
                    return contracted_stem + 'α'  # Default to α-contract
            elif 'ει' in full_word[-3:]:
                # Might be ε-contract (εε → ει)
                if contracted_stem and contracted_stem[-1] != 'ε':
                    return contracted_stem + 'ε'
        
        return contracted_stem
    
    def apply_prefill_stems_to_all_entries(self):
        """Apply stem prefilling to all current entries if the option is enabled"""
        if not self.config.prefill_stems.get():
            return
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        current_type = self.type_var.get()
        
        # Iterate through all entries and prefill them
        for entry_key, entry in self.entries.items():
            # Get the correct answer for this entry
            correct_answer = ""
            
            if current_type == "Adjective":
                # Parse entry_key like "Nominative_masculine_sg"
                parts = entry_key.split('_')
                if len(parts) == 3:
                    case, gender, number = parts
                    if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                        correct_answer = current_paradigm[gender][f"{case}_{number}"]
            elif current_type == "Pronoun":
                # Handle pronouns similar to adjectives for gender pronouns
                parts = entry_key.split('_')
                if len(parts) == 3:
                    case, gender, number = parts
                    if gender in current_paradigm and f"{case}_{number}" in current_paradigm[gender]:
                        correct_answer = current_paradigm[gender][f"{case}_{number}"]
                else:
                    # Simple pronoun structure
                    correct_answer = current_paradigm.get(entry_key, "")
            else:
                # Noun, verb, simple structure
                correct_answer = current_paradigm.get(entry_key, "")
            
            if correct_answer:
                self.prefill_entry_with_stem(entry_key, correct_answer)

    def check_answers(self):
        """Check all user inputs against correct answers."""
        # Clear previous error indicators
        for error_label in self.error_labels.values():
            error_label.grid_remove()
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        all_correct = True
        current_type = self.get_effective_type()  # Use effective type to handle starred items
        
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
                                
                                if not self.compare_answers(user_answer, correct_answer):
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
                            
                            if not self.compare_answers(user_answer, correct_answer):
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
                                    
                                    if not self.compare_answers(user_answer, correct_answer):
                                        # Show error indicator
                                        if entry_key in self.error_labels:
                                            self.error_labels[entry_key].grid()
                                        all_correct = False
        elif current_type == "Verb":
            # Check if we're dealing with infinitives or finite verbs
            current_mood = self.mood_var.get()
            
            if current_mood == "Infinitive":
                # Check infinitive answers (voice-based structure)
                voices = ["active", "middle", "passive"]
                for voice in voices:
                    entry_key = f"inf_{voice}"
                    
                    if entry_key in self.entries:
                        user_answer = self.entries[entry_key].get().strip()
                        correct_answer = current_paradigm.get(entry_key, "")
                        
                        if not self.compare_answers(user_answer, correct_answer):
                            # Show error indicator
                            if entry_key in self.error_labels:
                                self.error_labels[entry_key].grid()
                            all_correct = False
            else:
                # Check finite verb answers (person/number structure)
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        
                        if entry_key in self.entries:
                            user_answer = self.entries[entry_key].get().strip()
                            correct_answer = current_paradigm.get(entry_key, "")
                            
                            if not self.compare_answers(user_answer, correct_answer):
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
                        
                        if not self.compare_answers(user_answer, correct_answer):
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
        """Show the correct answers in all fields and track incorrect ones."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        # Capture user answers BEFORE revealing
        user_answers_before_reveal = {}
        for entry_key, entry in self.entries.items():
            user_answers_before_reveal[entry_key] = entry.get().strip()
        
        # Clear error indicators
        for error_label in self.error_labels.values():
            error_label.grid_remove()
        
        # Clear previous incorrect entries tracking
        self.incorrect_entries.clear()
        
        current_type = self.get_effective_type()  # Use effective type to handle starred items
        
        if current_type == "Adjective":
            # Check and fill adjective answers
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
                                correct_answer = current_paradigm[gender][answer_key]
                                user_answer = entry.get().strip()
                                
                                # Check if answer is correct
                                is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                
                                entry.configure(state='normal')
                                entry.delete(0, tk.END)
                                entry.insert(0, correct_answer)
                                
                                if is_correct:
                                    # Correct answer - make it gold and readonly
                                    entry.configure(state='readonly', bg='#FFD700')  # Gold color
                                else:
                                    # Incorrect or missing answer - make it red and track it
                                    entry.configure(bg='#FFB6B6')  # Light red color
                                    self.incorrect_entries.add(entry_key)
        elif current_type == "Pronoun":
            # Check and fill pronoun answers (no vocative)
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                # Personal pronouns use simple structure like nouns
                for case in pronoun_cases:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{number}"
                        
                        if entry_key in self.entries and entry_key in current_paradigm:
                            entry = self.entries[entry_key]
                            correct_answer = current_paradigm[entry_key]
                            user_answer = entry.get().strip()
                            
                            # Check if answer is correct
                            is_correct = self.check_answer_correctness(user_answer, correct_answer)
                            
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            
                            if is_correct:
                                # Correct answer - make it gold and readonly
                                entry.configure(state='readonly', bg='#FFD700')  # Gold color
                            else:
                                # Incorrect or missing answer - make it red and track it
                                entry.configure(bg='#FFB6B6')  # Light red color
                                self.incorrect_entries.add(entry_key)
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
                                    correct_answer = current_paradigm[gender][answer_key]
                                    user_answer = entry.get().strip()
                                    
                                    # Check if answer is correct
                                    is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                    
                                    entry.configure(state='normal')
                                    entry.delete(0, tk.END)
                                    entry.insert(0, correct_answer)
                                    
                                    if is_correct:
                                        # Correct answer - make it gold and readonly
                                        entry.configure(state='readonly', bg='#FFD700')  # Gold color
                                    else:
                                        # Incorrect or missing answer - make it red and track it
                                        entry.configure(bg='#FFB6B6')  # Light red color
                                        self.incorrect_entries.add(entry_key)
        elif current_type == "Verb":
            # Check if we're dealing with infinitives or finite verbs
            current_mood = self.mood_var.get()
            
            if current_mood == "Infinitive":
                # Check and fill infinitive answers (voice-based structure)
                voices = ["active", "middle", "passive"]
                for voice in voices:
                    entry_key = f"inf_{voice}"
                    
                    if entry_key in self.entries and entry_key in current_paradigm:
                        entry = self.entries[entry_key]
                        correct_answer = current_paradigm[entry_key]
                        user_answer = entry.get().strip()
                        
                        # Check if answer is correct
                        is_correct = self.check_answer_correctness(user_answer, correct_answer)
                        
                        entry.configure(state='normal')
                        entry.delete(0, tk.END)
                        entry.insert(0, correct_answer)
                        
                        if is_correct:
                            # Correct answer - make it gold and readonly
                            entry.configure(state='readonly', bg='#FFD700')  # Gold color
                        else:
                            # Incorrect or missing answer - make it red and track it
                            entry.configure(bg='#FFB6B6')  # Light red color
                            self.incorrect_entries.add(entry_key)
            else:
                # Check and fill finite verb answers (person/number structure)
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        
                        if entry_key in self.entries and entry_key in current_paradigm:
                            entry = self.entries[entry_key]
                            correct_answer = current_paradigm[entry_key]
                            user_answer = entry.get().strip()
                            
                            # Check if answer is correct
                            is_correct = self.check_answer_correctness(user_answer, correct_answer)
                            
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            
                            if is_correct:
                                # Correct answer - make it gold and readonly
                                entry.configure(state='readonly', bg='#FFD700')  # Gold color
                            else:
                                # Incorrect or missing answer - make it red and track it
                                entry.configure(bg='#FFB6B6')  # Light red color
                                self.incorrect_entries.add(entry_key)
        else:
            # Check and fill noun answers (simple structure)
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    
                    if entry_key in self.entries and entry_key in current_paradigm:
                        entry = self.entries[entry_key]
                        correct_answer = current_paradigm[entry_key]
                        user_answer = entry.get().strip()
                        
                        # Check if answer is correct
                        is_correct = self.check_answer_correctness(user_answer, correct_answer)
                        
                        entry.configure(state='normal')
                        entry.delete(0, tk.END)
                        entry.insert(0, correct_answer)
                        
                        if is_correct:
                            # Correct answer - make it gold and readonly
                            entry.configure(state='readonly', bg='#FFD700')  # Gold color
                        else:
                            # Incorrect or missing answer - make it red and track it
                            entry.configure(bg='#FFB6B6')  # Light red color
                            self.incorrect_entries.add(entry_key)
        
        # Record attempt in Learn Mode BEFORE revealing answers
        if self.learn_mode_enabled.get() and self.current_session:
            self.record_learn_mode_attempt(user_answers_before_reveal)
        
        # Mark that answers have been revealed and update button
        self.has_revealed = True
        self.update_reset_retry_button()

    def record_learn_mode_attempt(self, user_answers_before_reveal=None):
        """Record the current table attempt in Learn Mode"""
        if not self.current_session or not self.entries:
            return
        
        # Get current paradigm info
        paradigm_type = self.type_var.get()
        paradigm_name = self.mode_var.get()
        
        # Use provided user answers or collect current ones (fallback)
        if user_answers_before_reveal is not None:
            user_answers = user_answers_before_reveal
        else:
            user_answers = {}
            for entry_key, entry in self.entries.items():
                user_answers[entry_key] = entry.get().strip()
        
        # Get correct answers
        correct_answers = {}
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
        
        current_type = self.type_var.get()
        
        if current_type == "Adjective":
            # Handle adjective answers
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            is_two_termination = current_paradigm.get("type") == "adjective_2termination"
            genders = ["masculine", "neuter"] if is_two_termination else ["masculine", "feminine", "neuter"]
            
            for case in cases:
                for gender in genders:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{gender}_{number}"
                        if entry_key in self.entries and gender in current_paradigm:
                            answer_key = f"{case}_{number}"
                            if answer_key in current_paradigm[gender]:
                                correct_answers[entry_key] = current_paradigm[gender][answer_key]
        
        elif current_type == "Pronoun":
            # Handle pronoun answers
            pronoun_cases = ["Nominative", "Accusative", "Genitive", "Dative"]
            mode = self.mode_var.get()
            
            if "Personal I" in mode or "Personal You" in mode:
                for case in pronoun_cases:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{number}"
                        if entry_key in self.entries and entry_key in current_paradigm:
                            correct_answers[entry_key] = current_paradigm[entry_key]
            else:
                genders = ["masculine", "feminine", "neuter"]
                for case in pronoun_cases:
                    for gender in genders:
                        for number in ["sg", "pl"]:
                            entry_key = f"{case}_{gender}_{number}"
                            if entry_key in self.entries and gender in current_paradigm:
                                answer_key = f"{case}_{number}"
                                if answer_key in current_paradigm[gender]:
                                    correct_answers[entry_key] = current_paradigm[gender][answer_key]
        
        elif current_type == "Verb":
            # Handle verb answers
            current_mood = self.mood_var.get()
            
            if current_mood == "Infinitive":
                voices = ["active", "middle", "passive"]
                for voice in voices:
                    entry_key = f"inf_{voice}"
                    if entry_key in self.entries and entry_key in current_paradigm:
                        correct_answers[entry_key] = current_paradigm[entry_key]
            else:
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        if entry_key in self.entries and entry_key in current_paradigm:
                            correct_answers[entry_key] = current_paradigm[entry_key]
        
        else:
            # Handle noun answers
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    if entry_key in self.entries and entry_key in current_paradigm:
                        correct_answers[entry_key] = current_paradigm[entry_key]
        
        # Calculate time taken if we tracked start time
        time_taken = None
        if self.attempt_start_time:
            time_taken = int((datetime.now() - self.attempt_start_time).total_seconds())
        
        # Record the attempt
        accuracy = self.current_session.record_table_attempt(
            paradigm_type, paradigm_name, user_answers, correct_answers, time_taken
        )
        
        # Update progress display
        session_stats = self.current_session.get_session_stats()
        self.progress_tracker.update_session_stats(session_stats)
        
        print(f"Learn Mode: Recorded attempt for {paradigm_type} - {paradigm_name}, "
              f"Accuracy: {accuracy:.1f}%, Session total: {session_stats['total_attempts']} attempts")

    def check_answer_correctness(self, user_answer, correct_answer):
        """Check if user's answer matches the correct answer, ignoring accents and breathing marks."""
        # Remove leading/trailing whitespace
        user_answer = user_answer.strip()
        correct_answer = correct_answer.strip()
        
        # If user answer is empty, it's incorrect
        if not user_answer:
            return False
        
        # Simple comparison first
        if user_answer == correct_answer:
            return True
        
        # Remove Greek diacritics (accents and breathing marks) for comparison
        def remove_greek_diacritics(text):
            """Remove Greek accents, breathing marks, and other diacritics."""
            # Normalize to NFD (decomposed form) to separate base characters from diacritics
            nfd_text = unicodedata.normalize('NFD', text)
            
            # Remove common Greek diacritical marks
            diacritics_to_remove = [
                '\u0300',  # Grave accent
                '\u0301',  # Acute accent
                '\u0302',  # Circumflex
                '\u0304',  # Macron
                '\u0306',  # Breve
                '\u0308',  # Diaeresis
                '\u0313',  # Smooth breathing
                '\u0314',  # Rough breathing
                '\u0342',  # Perispomeni (circumflex)
                '\u0343',  # Koronis
                '\u0344',  # Dialytika tonos
                '\u0345',  # Iota subscript
            ]
            
            # Remove each diacritic
            for diacritic in diacritics_to_remove:
                nfd_text = nfd_text.replace(diacritic, '')
            
            # Normalize back to NFC (composed form)
            return unicodedata.normalize('NFC', nfd_text)
        
        # Compare without diacritics
        user_clean = remove_greek_diacritics(user_answer)
        correct_clean = remove_greek_diacritics(correct_answer)
        
        return user_clean == correct_clean

    def retry_incorrect_answers(self):
        """Clear only the incorrect/missing answers for retry, keeping correct ones locked."""
        if not self.has_revealed:
            return  # Should not happen since button is disabled before reveal
        
        # Clear only the incorrect entries
        for entry_key in self.incorrect_entries:
            if entry_key in self.entries:
                entry = self.entries[entry_key]
                entry.configure(state='normal')
                entry.configure(bg='white')  # Reset to normal background
                entry.delete(0, tk.END)
        
        # Apply prefill stems if enabled
        self.apply_prefill_stems_to_all_entries()
        
        # Disable retry button again until next reveal
        self.has_revealed = False
        self.update_reset_retry_button()

    def smart_reset_retry(self):
        """Smart button that acts as Reset before reveal, Retry after reveal."""
        if self.has_revealed and self.incorrect_entries:
            # After reveal with incorrect entries - act as Retry
            self.retry_incorrect_answers()
        else:
            # Before reveal or no incorrect entries - act as Reset
            self.reset_table()

    def update_reset_retry_button(self):
        """Update the Reset/Retry button text and state based on current context."""
        if not hasattr(self, 'reset_retry_button'):
            return
            
        if self.has_revealed and self.incorrect_entries:
            # After reveal with incorrect entries - show as Retry
            self.reset_retry_button.configure(text="Retry", state='normal')
        else:
            # Before reveal or no incorrect entries - show as Reset
            self.reset_retry_button.configure(text="Reset", state='normal')

    def clear_all_entries(self):
        """Clear all entries without recreating the table."""
        # Reset visual state of existing entries before clearing
        for entry in self.entries.values():
            try:
                entry.configure(state='normal')
                entry.configure(bg='white')
                entry.delete(0, tk.END)
            except tk.TclError:
                # Widget may have been destroyed already
                pass
        
        # Hide all error indicators
        for error_label in self.error_labels.values():
            try:
                error_label.grid_remove()
            except tk.TclError:
                # Widget may have been destroyed already
                pass
        
        # Reset reveal/retry state
        self.has_revealed = False
        self.incorrect_entries.clear()
        self.update_reset_retry_button()
        
        # Start timing for Learn Mode
        if self.learn_mode_enabled.get():
            self.attempt_start_time = datetime.now()

    def reset_table(self):
        """Clear all entries and error indicators."""
        # Reset visual state of existing entries before clearing
        for entry in self.entries.values():
            try:
                entry.configure(state='normal')
                entry.configure(bg='white')
                entry.delete(0, tk.END)
            except tk.TclError:
                # Widget may have been destroyed already
                pass
        
        # Hide all error indicators
        for error_label in self.error_labels.values():
            try:
                error_label.grid_remove()
            except tk.TclError:
                # Widget may have been destroyed already
                pass
        
        # Reset reveal/retry state
        self.has_revealed = False
        self.incorrect_entries.clear()
        self.update_reset_retry_button()
        
        # Start timing for Learn Mode
        if self.learn_mode_enabled.get():
            self.attempt_start_time = datetime.now()
        
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

Special Characters & Diacritics:
Type a vowel (α, ε, η, ι, ο, υ, ω) followed by diacritic shortcuts:

Breathing Marks:
• [ for smooth breathing (e.g., α[ → ἀ, ε[ → ἐ)
• ] for rough breathing (e.g., α] → ἁ, ε] → ἑ)

Accents:
• / for acute accent (e.g., α/ → ά, ε/ → έ)
• \\ for grave accent (e.g., α\\ → ὰ, ε\\ → ὲ)
• = for circumflex accent (e.g., α= → ᾶ, η= → ῆ)

Iota Subscript:
• { for iota subscript (e.g., α{ → ᾳ, η{ → ῃ, ω{ → ῳ)
  (Only α, η, ω can have iota subscript)

Combining Diacritics:
The system now supports combining multiple diacritics!
• ἀ{ → ᾀ (smooth breathing + iota subscript)
• ἁ/ → ἅ (rough breathing + acute accent)
• ὠ= → ὦ (smooth breathing + circumflex)
• ᾳ[ → ᾀ (iota subscript + smooth breathing)
• ἄ{ → ᾄ (breathing + accent + iota subscript)

Tips:
• The word to decline is shown above the table
• Gold background indicates correct answers
• Red X marks indicate incorrect answers
• Accents are not required for checking
• You can add diacritics in any order - the system will handle them correctly'''

        help_window = tk.Toplevel(self.root)
        help_window.title("Greek Grammar Help")
        help_window.geometry("500x650")

        # Create frame for text widget and scrollbar
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create text widget with scrollbar
        text_widget = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.insert("1.0", help_text)
        text_widget.config(state='disabled')
        
        # Pack text widget and scrollbar
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
            # Handle different verb entry key formats
            current_mood = self.mood_var.get()
            if current_mood == "Infinitive":
                # Parse infinitive entry key: "inf_voice" (e.g., "inf_active", "inf_middle", "inf_passive")
                if entry_key in current_paradigm:
                    correct_answer = current_paradigm[entry_key]
            else:
                # Parse finite verb entry key: "person_number" (e.g., "1st_sg", "3rd_pl")
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

    def find_next_incomplete_entry(self, candidates):
        """Find the next entry that needs completion from a list of candidate keys."""
        for key in candidates:
            if key in self.entries:
                entry = self.entries[key]
                # Check if entry needs completion (not readonly, meaning not already correct)
                if str(entry.cget('state')) != 'readonly':
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
                        next_key = self.find_next_incomplete_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we've finished all cases in sg column, move to pl column of same gender
                    if number == "sg":
                        candidates = [f"{cases[i]}_{gender}_pl" for i in range(len(cases))]
                        next_key = self.find_next_incomplete_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we're in plural and finished all cases, try next gender (start with sg)
                    if gender_idx < len(genders) - 1:
                        for next_gender in genders[gender_idx + 1:]:
                            # Try sg first, then pl for next gender
                            candidates = [f"{cases[i]}_{next_gender}_sg" for i in range(len(cases))]
                            candidates.extend([f"{cases[i]}_{next_gender}_pl" for i in range(len(cases))])
                            next_key = self.find_next_incomplete_entry(candidates)
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
                        next_key = self.find_next_incomplete_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we've finished all cases in sg column, move to pl column
                    if number == "sg":
                        candidates = [f"{pronoun_cases[i]}_pl" for i in range(len(pronoun_cases))]
                        next_key = self.find_next_incomplete_entry(candidates)
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
                            next_key = self.find_next_incomplete_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
                        
                        # If we've finished all cases in sg column, move to pl column of same gender
                        if number == "sg":
                            candidates = [f"{pronoun_cases[i]}_{gender}_pl" for i in range(len(pronoun_cases))]
                            next_key = self.find_next_incomplete_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
                        
                        # If we're in plural and finished all cases, try next gender (start with sg)
                        if gender_idx < len(genders) - 1:
                            for next_gender in genders[gender_idx + 1:]:
                                candidates = [f"{pronoun_cases[i]}_{next_gender}_sg" for i in range(len(pronoun_cases))]
                                candidates.extend([f"{pronoun_cases[i]}_{next_gender}_pl" for i in range(len(pronoun_cases))])
                                next_key = self.find_next_incomplete_entry(candidates)
                                if next_key:
                                    self.entries[next_key].focus()
                                    return
        elif current_type == "Verb":
            # Handle different verb entry key formats
            current_mood = self.mood_var.get()
            if current_mood == "Infinitive":
                # Parse infinitive: "inf_voice" (e.g., "inf_active", "inf_middle", "inf_passive")
                parts = current_key.split('_')
                if len(parts) == 2 and parts[0] == "inf":
                    voice = parts[1]
                    voices = ["active", "middle", "passive"]
                    if voice in voices:
                        voice_idx = voices.index(voice)
                        
                        # Try next voice (downward movement through the list)
                        if voice_idx < len(voices) - 1:
                            candidates = [f"inf_{voices[i]}" for i in range(voice_idx + 1, len(voices))]
                            next_key = self.find_next_incomplete_entry(candidates)
                            if next_key:
                                self.entries[next_key].focus()
                                return
            else:
                # Parse finite verb: "person_number" (e.g., "1st_sg", "2nd_pl")
                parts = current_key.split('_')
                if len(parts) == 2:
                    person, number = parts
                    persons = ["1st", "2nd", "3rd"]
                    person_idx = persons.index(person)
                    
                    # Try next person in same number column first (downward movement)
                    if person_idx < len(persons) - 1:
                        candidates = [f"{persons[i]}_{number}" for i in range(person_idx + 1, len(persons))]
                        next_key = self.find_next_incomplete_entry(candidates)
                        if next_key:
                            self.entries[next_key].focus()
                            return
                    
                    # If we've finished all persons in sg column, move to pl column
                    if number == "sg":
                        candidates = [f"{persons[i]}_pl" for i in range(len(persons))]
                        next_key = self.find_next_incomplete_entry(candidates)
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
                    next_key = self.find_next_incomplete_entry(candidates)
                    if next_key:
                        self.entries[next_key].focus()
                        return
                
                # If we've finished all cases in sg column, move to pl column
                if number == "sg":
                    candidates = [f"{cases[i]}_pl" for i in range(len(cases))]
                    next_key = self.find_next_incomplete_entry(candidates)
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
            # Handle different verb navigation patterns
            current_mood = self.mood_var.get()
            if current_mood == "Infinitive":
                # Handle infinitive navigation (inf_voice structure)
                parts = current_key.split('_')
                if len(parts) == 2 and parts[0] == "inf":
                    voice = parts[1]
                    voices = ["active", "middle", "passive"]
                    if voice in voices:
                        voice_idx = voices.index(voice)
                        
                        if direction == 'up' and voice_idx > 0:
                            next_key = f"inf_{voices[voice_idx - 1]}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        elif direction == 'down' and voice_idx < len(voices) - 1:
                            next_key = f"inf_{voices[voice_idx + 1]}"
                            if next_key in self.entries:
                                self.entries[next_key].focus()
                        # Left/right navigation is not meaningful for infinitives (single column)
            else:
                # Handle finite verb navigation (person/number structure)
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

    # Starred Items Management
    def load_starred_items(self):
        """Load starred items from file."""
        try:
            import os
            if os.path.exists(self.starred_file):
                import json
                with open(self.starred_file, 'r', encoding='utf-8') as f:
                    starred_list = json.load(f)
                    self.starred_items = set(starred_list)
                    print(f"Loaded {len(self.starred_items)} starred items")
        except Exception as e:
            print(f"Error loading starred items: {e}")
            self.starred_items = set()

    def save_starred_items(self):
        """Save starred items to file."""
        try:
            import json
            with open(self.starred_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.starred_items), f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.starred_items)} starred items")
        except Exception as e:
            print(f"Error saving starred items: {e}")

    def get_current_item_key(self):
        """Get the current table's key for starring (format: 'type:mode')."""
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
        
        # If we're in starred mode, we need to find the original key
        if current_type == "Starred":
            # Find the corresponding starred item key
            for item_key in self.starred_items:
                parts = item_key.split(':')
                if len(parts) >= 2:
                    item_type = parts[0]
                    item_mode = parts[1]
                    
                    if item_type == "Verb" and len(parts) >= 5:
                        voice = parts[2]
                        tense = parts[3]
                        mood = parts[4]
                        
                        # Create display text that matches get_starred_display_items format
                        if "(" in item_mode and ")" in item_mode:
                            verb_name = item_mode.split("(")[1].split(")")[0]
                            display_text = f"{verb_name} - {tense} {voice} {mood}"
                        else:
                            display_text = f"{item_mode} - {tense} {voice} {mood}"
                    else:
                        display_text = item_mode
                    
                    if display_text == current_mode:
                        return item_key
            
            # Fallback - shouldn't happen
            return f"Unknown:{current_mode}"
        
        # For non-starred items, generate the key normally
        # For verbs, include voice/tense/mood in the key for specificity
        if current_type == "Verb":
            current_voice = getattr(self, 'voice_var', None)
            current_tense = getattr(self, 'tense_var', None) 
            current_mood = getattr(self, 'mood_var', None)
            
            if current_voice and current_tense and current_mood:
                voice = current_voice.get()
                tense = current_tense.get()
                mood = current_mood.get()
                return f"{current_type}:{current_mode}:{voice}:{tense}:{mood}"
        
        return f"{current_type}:{current_mode}"

    def get_effective_type(self):
        """Get the effective type for table creation (handles starred items)."""
        current_type = self.type_var.get()
        
        if current_type != "Starred":
            return current_type
        
        # For starred items, determine the original type
        current_mode = self.mode_var.get()
        
        # Find the original type for this starred item
        for item_key in self.starred_items:
            parts = item_key.split(':')
            if len(parts) >= 2:
                item_type = parts[0]
                item_mode = parts[1]
                
                if item_type == "Verb" and len(parts) >= 5:
                    voice = parts[2]
                    tense = parts[3]
                    mood = parts[4]
                    
                    # Create display text that matches get_starred_display_items format
                    if "(" in item_mode and ")" in item_mode:
                        verb_name = item_mode.split("(")[1].split(")")[0]
                        display_text = f"{verb_name} - {tense} {voice} {mood}"
                    else:
                        display_text = f"{item_mode} - {tense} {voice} {mood}"
                else:
                    display_text = item_mode
                
                if display_text == current_mode:
                    return item_type
        
        # Fallback to Noun if we can't determine the type
        return "Noun"

    def is_current_item_starred(self):
        """Check if the current table is starred."""
        return self.get_current_item_key() in self.starred_items

    def toggle_star(self):
        """Toggle star status of current table."""
        current_type = self.type_var.get()
        item_key = self.get_current_item_key()
        
        if item_key in self.starred_items:
            # Unstar
            self.starred_items.remove(item_key)
            print(f"Unstarred: {item_key}")
            
            # If we're in starred mode and we just unstarred the current item,
            # we need to handle navigation since this item will disappear from the list
            if current_type == "Starred":
                self.update_starred_dropdown()
                # If there are still starred items, navigate to the first one
                remaining_items = self.get_starred_display_items()
                if remaining_items:
                    self.mode_var.set(remaining_items[0])
                    self.on_mode_change(None)
                else:
                    # No more starred items, switch to Noun type
                    self.type_var.set("Noun")
                    self.on_type_change(None)
                    
        elif current_type != "Starred":
            # Only allow starring when NOT in starred mode
            self.starred_items.add(item_key)
            print(f"Starred: {item_key}")
        else:
            # In starred mode, only allow unstarring
            print("Cannot star items while in Starred mode - only unstarring is allowed")
            return
        
        # Save to file
        self.save_starred_items()
        
        # Update star button appearance
        self.update_star_button()

    def update_star_button(self):
        """Update the star button appearance based on current star status."""
        if self.star_button:
            current_type = self.type_var.get()
            is_starred = self.is_current_item_starred()
            
            if current_type == "Starred":
                # In starred mode, always show filled star (can only unstar)
                self.star_button.config(text="★", foreground="black")
            elif is_starred:
                # In normal mode but item is starred - filled star
                self.star_button.config(text="★", foreground="black")
            else:
                # In normal mode and item is not starred - outline star
                self.star_button.config(text="☆", foreground="black")

    def get_starred_display_items(self):
        """Get list of starred items formatted for dropdown display."""
        starred_display = []
        
        for item_key in sorted(self.starred_items):
            # Parse the item key
            parts = item_key.split(':')
            if len(parts) >= 2:
                item_type = parts[0]
                mode = parts[1]
                
                if item_type == "Verb" and len(parts) >= 5:
                    # For verbs, create a more concise display
                    voice = parts[2]
                    tense = parts[3]
                    mood = parts[4]
                    
                    # Extract just the verb name from the mode (what's in parentheses)
                    if "(" in mode and ")" in mode:
                        verb_name = mode.split("(")[1].split(")")[0]
                        display_text = f"{verb_name} - {tense} {voice} {mood}"
                    else:
                        display_text = f"{mode} - {tense} {voice} {mood}"
                else:
                    # For other types, just use the mode
                    display_text = mode
                
                starred_display.append(display_text)
        
        return starred_display

    def update_starred_dropdown(self):
        """Update the mode dropdown when in starred mode."""
        if self.type_var.get() == "Starred":
            starred_items = self.get_starred_display_items()
            self.modes = starred_items  # Update self.modes as well
            self.mode_dropdown['values'] = starred_items
            
            # If current selection is no longer valid, select first item
            if starred_items and self.mode_var.get() not in starred_items:
                self.mode_var.set(starred_items[0])
                self.on_mode_change(None)
            elif not starred_items:
                # No starred items left, set to "No starred items"
                self.modes = ["No starred items"]
                self.mode_dropdown['values'] = self.modes
                self.mode_var.set("No starred items")

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
