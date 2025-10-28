import tkinter as tk
from tkinter import ttk, messagebox, font
import json
import unicodedata
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from database import DatabaseManager
from session_manager import SessionManager

# Try to import PIL for better image handling
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
        self.lock_current_type = tk.BooleanVar(value=False)
        self.auto_advance = tk.BooleanVar(value=False)
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
        self.lock_current_type.set(False)

class BellerophonGrammarApp:
    def check_and_auto_advance(self):
        auto_advance_enabled = False
        if hasattr(self, 'config') and hasattr(self.config, 'auto_advance'):
            auto_advance_enabled = self.config.auto_advance.get() if hasattr(self.config.auto_advance, 'get') else self.config.auto_advance
        elif hasattr(self, 'auto_advance'):
            auto_advance_enabled = self.auto_advance.get() if hasattr(self.auto_advance, 'get') else self.auto_advance

        all_correct = all(str(entry.cget('state')) == 'readonly' for entry in self.entries.values())
        if all_correct and auto_advance_enabled and len(self.entries) > 0:
            # Check which side we're on (Greek or Latin) and call appropriate next function
            # Greek side uses type_var, Latin side uses latin_type_var
            if hasattr(self, 'latin_type_var') and hasattr(self, 'latin_entries') and len(self.latin_entries) > 0:
                # We're on Latin side
                if hasattr(self, 'next_latin_word') and callable(self.next_latin_word):
                    self.next_latin_word()
                    # Focus on first Latin entry after table loads
                    self.root.after(50, self.focus_first_latin_entry)
            elif hasattr(self, 'type_var'):
                # We're on Greek side
                if self.config.randomize_next.get():
                    if hasattr(self, 'random_next') and callable(self.random_next):
                        self.random_next()
                else:
                    if hasattr(self, 'next_answer') and callable(self.next_answer):
                        self.next_answer()
                # Focus on first Greek entry after table loads
                self.root.after(50, self.focus_first_greek_entry)
    
    def focus_first_latin_entry(self):
        """Focus on the first editable entry in the Latin table."""
        if hasattr(self, 'latin_entries') and self.latin_entries:
            for entry in self.latin_entries.values():
                if str(entry.cget('state')) != 'readonly':
                    entry.focus()
                    return
    
    def focus_first_greek_entry(self):
        """Focus on the first editable entry in the Greek table."""
        if hasattr(self, 'entries') and self.entries:
            for entry in self.entries.values():
                if str(entry.cget('state')) != 'readonly':
                    entry.focus()
                    return
    def get_effective_type_from_item_key(self, item_key):
        """Extracts the type (Noun, Verb, etc.) from a starred item key."""
        return item_key.split(":", 1)[0] if item_key and ":" in item_key else None
    
    def get_effective_type(self):
        """Get the effective type, resolving Starred items to their real type."""
        current_type = getattr(self, 'type_var', None)
        if not current_type:
            return None
        
        type_value = current_type.get()
        
        # If we're in Starred mode, extract the real type from the current item
        if type_value == "Starred":
            current_mode = getattr(self, 'mode_var', None)
            if current_mode and current_mode.get() != "No starred items":
                # Use display map to find the actual item key
                display_map = self.get_starred_display_map()
                item_key = display_map.get(current_mode.get())
                if item_key:
                    return self.get_effective_type_from_item_key(item_key)
        
        return type_value
    
    def clear_error(self, key):
        """Clear error indicator for a specific entry key."""
        if key in self.error_labels:
            try:
                self.error_labels[key].grid_remove()
            except tk.TclError:
                pass  # Widget may have been destroyed
    
    def init_starred_verb(self, starred_key):
        """Initialize a starred verb with its specific form data."""
        parts = starred_key.split(':')
        if len(parts) < 5 or parts[0] != "Verb":
            return False
            
        mode = parts[1]
        voice = parts[2]
        tense = parts[3]
        mood = parts[4]
        
        # Store the starred verb state
        self._starred_verb_data = {
            'mode': mode,
            'voice': voice,
            'tense': tense,
            'mood': mood,
            'key': starred_key
        }
        
        # Initialize or update the verb form variables
        if not hasattr(self, 'voice_var'):
            self.voice_var = tk.StringVar(value=voice)
        else:
            self.voice_var.set(voice)
            
        if not hasattr(self, 'tense_var'):
            self.tense_var = tk.StringVar(value=tense)
        else:
            self.tense_var.set(tense)
            
        if not hasattr(self, 'mood_var'):
            self.mood_var = tk.StringVar(value=mood)
        else:
            self.mood_var.set(mood)
        
        return True
    
    def get_starred_verb_paradigm(self):
        """Get paradigm specifically for starred verbs."""
        if not hasattr(self, '_starred_verb_data'):
            return None
            
        data = self._starred_verb_data
        mode = data['mode']
        
        # Extract verb base from mode
        verb_base = None
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
        elif "βαίνω" in mode:
            verb_base = "baino"
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
        
        if not verb_base:
            print(f"Warning: Could not determine verb base for mode: {mode}")
            return None
        
        # Map form values to paradigm keys
        tense_map = {
            "present": "pres", "imperfect": "impf", "aorist": "aor",
            "future": "fut", "perfect": "perf", "pluperfect": "plpf"
        }
        mood_map = {
            "indicative": "ind", "subjunctive": "subj", "optative": "opt",
            "imperative": "imp", "infinitive": "inf"
        }
        voice_map = {
            "active": "act", "middle": "mid", "passive": "pass"
        }
        
        tense_key = tense_map.get(data['tense'].lower(), data['tense'].lower())
        mood_key = mood_map.get(data['mood'].lower(), data['mood'].lower())
        voice_key = voice_map.get(data['voice'].lower(), data['voice'].lower())
        
        # Build paradigm key
        if data['mood'].lower() == "infinitive":
            # For infinitives, combine all voices
            combined_paradigm = {}
            for voice_name, voice_abbr in voice_map.items():
                voice_paradigm_key = f"{verb_base}_{tense_key}_{mood_key}_{voice_abbr}"
                voice_paradigm = self.paradigms.get(voice_paradigm_key)
                if voice_paradigm:
                    inf_key = f"inf_{voice_name}"
                    if inf_key in voice_paradigm:
                        combined_paradigm[inf_key] = voice_paradigm[inf_key]
            return combined_paradigm if combined_paradigm else None
        else:
            paradigm_key = f"{verb_base}_{tense_key}_{mood_key}_{voice_key}"
            return self.paradigms.get(paradigm_key)
    
    def create_starred_verb_table(self, paradigm):
        """Create a verb table specifically for starred verbs with locked controls."""
        if not paradigm or not hasattr(self, '_starred_verb_data'):
            return
        
        # Clear entry and error label dictionaries before destroying widgets
        self.entries.clear()
        self.error_labels.clear()
        
        # Destroy existing table frame and create new one (like create_declension_table)
        if hasattr(self, 'table_frame') and self.table_frame:
            self.table_frame.destroy()
            
        # Create a container frame that can expand and center content
        # Table can now use full space since buttons are floating
        table_container = ttk.Frame(self.main_frame)
        table_container.grid(row=3, column=0, columnspan=3, rowspan=2, sticky='nsew')
        table_container.grid_columnconfigure(0, weight=1)  # Left padding
        table_container.grid_columnconfigure(1, weight=0)  # Table content
        table_container.grid_columnconfigure(2, weight=1)  # Right padding
        table_container.grid_rowconfigure(0, weight=1)
        
        # Create the table frame in the center column - add bottom padding for floating buttons
        self.table_frame = ttk.Frame(table_container)
        self.table_frame.grid(row=0, column=1, sticky='nsew', padx=20, pady=(0, 80))
        
        # Configure grid weights for responsive design
        for i in range(10):  # Allow for up to 10 columns
            self.table_frame.grid_columnconfigure(i, weight=1)
        
        # Use the standard verb table creation method for proper layout
        # The _in_starred_context flag will prevent unwanted mode changes
        self.current_starred_paradigm = paradigm
        self.create_verb_table(paradigm)
        
        # Add buttons (create_verb_table doesn't create buttons, only create_declension_table does)
        self.create_buttons_for_starred_verbs()
    
    def create_buttons_for_starred_verbs(self):
        """Create the control buttons for starred verbs."""
        # Bottom button frame positioned as overlay to allow table to extend underneath
        bottom_button_frame = ttk.Frame(self.main_frame)
        # Use place instead of grid to create floating buttons that don't constrain table space
        bottom_button_frame.place(relx=0.0, rely=1.0, anchor='sw', relwidth=1.0)
        
        # Container frame for buttons to allow centering
        button_container = ttk.Frame(bottom_button_frame)
        button_container.grid(row=0, column=1, pady=10)
        
        # Configure the bottom frame for centering floating buttons
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
    

    def get_available_types(self):
        """Get the list of available types based on whether starred items exist."""
        base_types = ["Noun", "Adjective", "Pronoun", "Verb"]
        
        # Check if there are any starred items
        starred_items = self.get_starred_display_items()
        if starred_items:
            # If starred items exist, add "Starred" at the end
            return base_types + ["Starred"]
        else:
            # If no starred items, just return base types
            return base_types
    
    def update_type_dropdown(self):
        """Update the type dropdown values based on current starred items."""
        available_types = self.get_available_types()
        
        # Update the dropdown values
        if hasattr(self, 'type_dropdown'):
            current_value = self.type_var.get()
            self.type_dropdown['values'] = available_types
            
            # If current selection is "Starred" but no starred items exist, switch to "Noun"
            if current_value == "Starred" and "Starred" not in available_types:
                self.type_var.set("Noun")
                self.on_type_change(None)
    
    def create_starred_finite_verb_table(self, paradigm, verb_data):
        """Create finite verb table for starred verbs."""
        # Configure table columns
        self.table_frame.grid_columnconfigure(0, weight=1)  # Person/Number
        self.table_frame.grid_columnconfigure(1, weight=1)  # Form
        self.table_frame.grid_columnconfigure(2, weight=2)  # Your Answer
        
        # Headers
        ttk.Label(self.table_frame, text="Person/Number", font=('Arial', 12, 'bold')).grid(row=2, column=0, padx=10, pady=10)
        ttk.Label(self.table_frame, text="Form", font=('Arial', 12, 'bold')).grid(row=2, column=1, padx=10, pady=10)
        ttk.Label(self.table_frame, text="Your Answer", font=('Arial', 12, 'bold')).grid(row=2, column=2, padx=10, pady=10)
        
        # Person/Number entries - always create all entries, even if paradigm doesn't have them
        persons = ["1st Sing", "2nd Sing", "3rd Sing", "1st Plur", "2nd Plur", "3rd Plur"]
        keys = ["1st_sg", "2nd_sg", "3rd_sg", "1st_pl", "2nd_pl", "3rd_pl"]
        
        for i, (person, key) in enumerate(zip(persons, keys), 3):
            # Person label
            ttk.Label(self.table_frame, text=person, font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=8, sticky='e')
            
            # Form label - show the actual verb form from paradigm
            form_text = paradigm.get(key, "—")
            ttk.Label(self.table_frame, text=form_text, font=('Times New Roman', 12)).grid(row=i, column=1, padx=10, pady=8, sticky='w')
            
            # Entry field - create entry regardless of whether it's in paradigm
            entry_frame = tk.Frame(self.table_frame)
            entry_frame.grid(row=i, column=2, padx=5, pady=8, sticky='ew')
            entry_frame.grid_columnconfigure(0, weight=1)
            
            # Check if this form exists in the paradigm
            form_exists = key in paradigm
            
            if form_exists:
                # Create normal entry
                entry = tk.Entry(entry_frame, width=18, font=('Times New Roman', 12), relief='solid', borderwidth=1)
                entry.grid(row=0, column=0, sticky='ew')
                entry.bind('<KeyPress>', self.handle_key_press)
                entry.bind('<KeyRelease>', lambda e, k=key: (self.handle_text_change(e, k), self.clear_error(k)))
                entry.bind('<Return>', lambda e, k=key: self.handle_enter(e, k))
                
                self.entries[key] = entry
                
                # Error label
                error_label = ttk.Label(entry_frame, text="X", foreground='red', font=('Arial', 10, 'bold'))
                error_label.grid(row=0, column=1, padx=(5, 0))
                error_label.grid_remove()
                self.error_labels[key] = error_label
            else:
                # Grey out missing forms
                entry = tk.Entry(entry_frame, width=18, font=('Times New Roman', 12), relief='solid', borderwidth=1, state='disabled', disabledbackground='#f0f0f0')
                entry.grid(row=0, column=0, sticky='ew')
    
    def create_starred_infinitive_table(self, paradigm, verb_data):
        """Create infinitive table for starred verbs."""
        # Configure table columns
        self.table_frame.grid_columnconfigure(0, weight=1)  # Voice
        self.table_frame.grid_columnconfigure(1, weight=1)  # Form
        self.table_frame.grid_columnconfigure(2, weight=2)  # Your Answer
        
        # Headers
        ttk.Label(self.table_frame, text="Tense × Voice", font=('Arial', 12, 'bold')).grid(row=2, column=0, padx=10, pady=10)
        ttk.Label(self.table_frame, text="Form", font=('Arial', 12, 'bold')).grid(row=2, column=1, padx=10, pady=10)
        ttk.Label(self.table_frame, text="Your Answer", font=('Arial', 12, 'bold')).grid(row=2, column=2, padx=10, pady=10)
        
        # Voice entries
        voices = ["Active", "Middle", "Passive"]
        voice_keys = ["inf_active", "inf_middle", "inf_passive"]
        
        for i, (voice, key) in enumerate(zip(voices, voice_keys), 3):
            # Voice label
            ttk.Label(self.table_frame, text=f"{verb_data['tense']} {voice}", font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=8, sticky='w')
            
            # Form label - show the actual infinitive form from paradigm
            form_text = paradigm.get(key, "—")
            ttk.Label(self.table_frame, text=form_text, font=('Times New Roman', 12)).grid(row=i, column=1, padx=10, pady=8, sticky='w')
            
            # Entry field - create regardless of whether it's in paradigm
            entry_frame = tk.Frame(self.table_frame)
            entry_frame.grid(row=i, column=2, padx=5, pady=8, sticky='ew')
            entry_frame.grid_columnconfigure(0, weight=1)
            
            form_exists = key in paradigm
            
            if form_exists:
                entry = tk.Entry(entry_frame, width=18, font=('Times New Roman', 12), relief='solid', borderwidth=1)
                entry.grid(row=0, column=0, sticky='ew')
                entry.bind('<KeyPress>', self.handle_key_press)
                entry.bind('<KeyRelease>', lambda e, k=key: (self.handle_text_change(e, k), self.clear_error(k)))
                entry.bind('<Return>', lambda e, k=key: self.handle_enter(e, k))
                
                self.entries[key] = entry
                
                # Error label
                error_label = ttk.Label(entry_frame, text="X", foreground='red', font=('Arial', 10, 'bold'))
                error_label.grid(row=0, column=1, padx=(5, 0))
                error_label.grid_remove()
                self.error_labels[key] = error_label
            else:
                # Grey out missing forms
                entry = tk.Entry(entry_frame, width=18, font=('Times New Roman', 12), relief='solid', borderwidth=1, state='disabled', disabledbackground='#f0f0f0')
                entry.grid(row=0, column=0, sticky='ew')

    def __init__(self, root):
        self.root = root
        self.root.configure(bg='#F8F6F1')  # White Marble background for root window
        # --- BEGIN: moved UI setup and initialization code into __init__ ---
        self.incorrect_entries = set()  # Track which entries were incorrect
        self.has_revealed = False  # Track if answers have been revealed
        # Initialize practice configuration
        self.config = PracticeConfig()
        # Initialize session manager
        self.session_manager = SessionManager()
        self.current_session_id = None
        self.current_session_tables = []
        self.current_table_index = 0
        # Initialize recent word history (track last 10 words to avoid repetition)
        from collections import deque
        self.recent_word_history = deque(maxlen=10)
        # Initialize starred items system (Greek side)
        self.starred_items = set()  # Set of starred items in format "type:mode"
        self.starred_file = "starred_items.json"
        self.star_button = None  # Will be created in setup_ui
        # Load starred items from file
        self.load_starred_items()
        # Initialize Latin starred items system (separate from Greek)
        self.latin_starred_items = set()  # Set of starred Latin items
        self.latin_starred_file = "latin_starred_items.json"
        self.latin_star_button = None  # Will be created in show_latin_view
        # Load Latin starred items from file
        self.load_latin_starred_items()
        # Initialize header logo and app icon before any UI code that checks them
        self.header_logo = self.load_header_logo()
        self.latin_header_logo = self.load_latin_header_logo()  # Latin-specific logo
        self.app_icon = self.load_app_icon()
        # Initialize table_frame to None to avoid AttributeError before first use
        self.table_frame = None
        # Initialize entries and error_labels as empty dicts to avoid AttributeError before first use
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
        self.root.state('zoomed')  # Start maximized
        self.root.minsize(1000, 700)  # Set minimum size to prevent content from being cut off
        
        # Main container that will expand to fill the window (use tk.Frame for proper background)
        self.main_frame = tk.Frame(self.root, bg='#F8F6F1')
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        
        # Configure grid weights for proper expansion
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Configure main_frame to expand
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Set window icon (small icon)
        if self.app_icon:
            try:
                self.root.iconphoto(True, self.app_icon)
            except Exception as e:
                print(f"Could not set window icon: {e}")
        
        # Load paradigms early so they're available for session mode
        try:
            with open('paradigms.json', 'r', encoding='utf-8') as f:
                self.paradigms = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "Could not find paradigms.json file")
            self.root.destroy()
            return
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Could not parse paradigms.json file")
            self.root.destroy()
            return
        
        # Show tables view directly (startup page and session mode are shelved for now)
        self.show_tables_view()
        # To re-enable startup page, change above line to: self.show_startup_page()
    
    # ============================================================================
    # SHELVED FEATURES: Startup Page and Session Mode
    # ============================================================================
    # The following methods are shelved but preserved for future development:
    # - show_startup_page() - Startup screen with logo and buttons
    # - show_session_options_page() - Session configuration screen
    # - show_session_mode() - Active session with progress tracking
    # - show_session_review() - Session results and statistics
    # - All session table creation and management methods
    # To re-enable, change show_tables_view() to show_startup_page() in __init__
    # ============================================================================
    
    def show_startup_page(self):
        """Display the startup page with logo and navigation buttons."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Clear all previous grid configurations
        for i in range(10):
            self.main_frame.grid_rowconfigure(i, weight=0)
            self.main_frame.grid_columnconfigure(i, weight=0)
        
        # Configure main_frame for centered content
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create centered container
        center_container = ttk.Frame(self.main_frame)
        center_container.grid(row=0, column=0)
        
        # Load and display the Bellerophon small logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "Bellerphon small.png")
            logo_image = Image.open(logo_path)
            # Resize to 360x300 pixels
            logo_image = logo_image.resize((360, 300), Image.Resampling.LANCZOS)
            self.startup_logo = ImageTk.PhotoImage(logo_image)
            
            logo_label = ttk.Label(center_container, image=self.startup_logo)
            logo_label.grid(row=0, column=0, pady=(0, 40))
            # Keep reference to prevent garbage collection
            logo_label.image = self.startup_logo
        except Exception as e:
            print(f"Could not load startup logo: {e}")
            # Fallback text
            fallback_label = ttk.Label(
                center_container,
                text="BELLEROPHON\nGRAMMAR",
                font=('Arial', 36, 'bold'),
                justify='center'
            )
            fallback_label.grid(row=0, column=0, pady=(0, 40))
        
        # Welcome text
        welcome_label = ttk.Label(
            center_container,
            text="Welcome to Bellerophon Grammar",
            font=('Arial', 18),
            justify='center'
        )
        welcome_label.grid(row=1, column=0, pady=(0, 30))
        
        # Button container
        button_container = ttk.Frame(center_container)
        button_container.grid(row=2, column=0)
        
        # Configure button style
        button_style = ttk.Style()
        button_style.configure('Startup.TButton',
                             font=('Arial', 14),
                             padding=(30, 15))
        
        # Create three buttons in a horizontal row
        tables_button = ttk.Button(
            button_container,
            text="Tables",
            command=self.show_tables_view,
            style='Startup.TButton',
            width=20
        )
        tables_button.grid(row=0, column=0, padx=10)
        
        session_button = ttk.Button(
            button_container,
            text="Start new session",
            command=self.start_new_session,
            style='Startup.TButton',
            width=20,
            state='normal'  # Now enabled
        )
        session_button.grid(row=0, column=1, padx=10)
        
        stats_button = ttk.Button(
            button_container,
            text="Statistics",
            command=self.show_statistics,
            style='Startup.TButton',
            width=20,
            state='disabled'  # Disabled for now
        )
        stats_button.grid(row=0, column=2, padx=10)
    
    def start_new_session(self):
        """Show the session options page."""
        self.show_session_options_page()
    
    def show_session_options_page(self):
        """Display the session configuration page."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Clear all previous grid configurations
        for i in range(10):
            self.main_frame.grid_rowconfigure(i, weight=0)
            self.main_frame.grid_columnconfigure(i, weight=0)
        
        # Configure main_frame for centered content
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create centered container
        center_container = ttk.Frame(self.main_frame)
        center_container.grid(row=0, column=0)
        
        # Title
        title_label = ttk.Label(
            center_container,
            text="Configure Your Study Session",
            font=('Arial', 24, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 30), sticky='w')
        
        # Options frame
        options_frame = ttk.Frame(center_container)
        options_frame.grid(row=1, column=0, sticky='ew')
        
        current_row = 0
        
        # 1. Number of tables
        num_tables_label = ttk.Label(
            options_frame,
            text="Number of tables:",
            font=('Arial', 14, 'bold')
        )
        num_tables_label.grid(row=current_row, column=0, sticky='w', pady=(0, 10))
        
        self.num_tables_var = tk.IntVar(value=10)
        num_tables_frame = ttk.Frame(options_frame)
        num_tables_frame.grid(row=current_row, column=1, sticky='w', padx=(20, 0), pady=(0, 10))
        
        for num in [5, 10, 15]:
            rb = ttk.Radiobutton(
                num_tables_frame,
                text=str(num),
                variable=self.num_tables_var,
                value=num
            )
            rb.pack(side='left', padx=5)
        
        current_row += 1
        
        # 2. Word types
        word_types_label = ttk.Label(
            options_frame,
            text="Word types:",
            font=('Arial', 14, 'bold')
        )
        word_types_label.grid(row=current_row, column=0, sticky='w', pady=(10, 10))
        
        word_types_frame = ttk.Frame(options_frame)
        word_types_frame.grid(row=current_row, column=1, sticky='w', padx=(20, 0), pady=(10, 10))
        
        self.word_type_vars = {}
        word_types = ['Nouns', 'Verbs', 'Adjectives', 'Pronouns', 'Starred']
        for i, wtype in enumerate(word_types):
            var = tk.BooleanVar(value=True if wtype != 'Starred' else False)
            self.word_type_vars[wtype] = var
            cb = ttk.Checkbutton(
                word_types_frame,
                text=wtype,
                variable=var
            )
            cb.grid(row=0, column=i, padx=5, sticky='w')
        
        # Add "Mixed" option
        var = tk.BooleanVar(value=False)
        self.word_type_vars['Mixed'] = var
        cb = ttk.Checkbutton(
            word_types_frame,
            text="Mixed (All types)",
            variable=var,
            command=self.toggle_mixed_mode
        )
        cb.grid(row=1, column=0, columnspan=3, padx=5, pady=(5, 0), sticky='w')
        
        current_row += 1
        
        # 3. Focus area
        focus_label = ttk.Label(
            options_frame,
            text="Focus area:",
            font=('Arial', 14, 'bold')
        )
        focus_label.grid(row=current_row, column=0, sticky='w', pady=(10, 10))
        
        self.focus_area_var = tk.StringVar(value="General")
        focus_frame = ttk.Frame(options_frame)
        focus_frame.grid(row=current_row, column=1, sticky='w', padx=(20, 0), pady=(10, 10))
        
        focus_options = [
            ("General Practice", "General"),
            ("Weak Tables (Low mastery)", "Weak"),
            ("Untested Tables", "Untested")
        ]
        
        for i, (text, value) in enumerate(focus_options):
            rb = ttk.Radiobutton(
                focus_frame,
                text=text,
                variable=self.focus_area_var,
                value=value
            )
            rb.grid(row=i, column=0, sticky='w', pady=2)
        
        current_row += 1
        
        # 4. Spaced repetition toggle
        spaced_rep_label = ttk.Label(
            options_frame,
            text="Advanced:",
            font=('Arial', 14, 'bold')
        )
        spaced_rep_label.grid(row=current_row, column=0, sticky='w', pady=(10, 10))
        
        self.spaced_repetition_var = tk.BooleanVar(value=False)
        spaced_rep_cb = ttk.Checkbutton(
            options_frame,
            text="Spaced Repetition (avoid recently practiced tables)",
            variable=self.spaced_repetition_var
        )
        spaced_rep_cb.grid(row=current_row, column=1, sticky='w', padx=(20, 0), pady=(10, 10))
        
        current_row += 1
        
        # Button frame
        button_frame = ttk.Frame(center_container)
        button_frame.grid(row=2, column=0, pady=(30, 0))
        
        # Back button
        back_button = ttk.Button(
            button_frame,
            text="← Back",
            command=self.show_startup_page,
            width=15
        )
        back_button.pack(side='left', padx=5)
        
        # Start session button
        start_button = ttk.Button(
            button_frame,
            text="Start Session",
            command=self.start_study_session,
            width=15,
            style='Accent.TButton'
        )
        start_button.pack(side='left', padx=5)
        
        # Configure accent button style
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 12, 'bold'))
    
    def toggle_mixed_mode(self):
        """When Mixed is selected, deselect all other word types."""
        if self.word_type_vars['Mixed'].get():
            for key in self.word_type_vars:
                if key != 'Mixed':
                    self.word_type_vars[key].set(False)
    
    def get_all_table_identifiers(self, word_types: List[str]) -> List[dict]:
        """
        Get all possible table identifiers for the selected word types.
        
        Returns:
            List of dicts with keys: table_id, word_type, word, subtype
        """
        import random
        tables = []
        
        for paradigm_key, paradigm_data in self.paradigms.items():
            word_type = paradigm_data.get('type', '').lower()
            word = paradigm_data.get('word', '')
            
            # Check if this word type is selected
            type_match = False
            if 'Mixed' in word_types:
                type_match = True
            elif word_type == 'noun' and 'Nouns' in word_types:
                type_match = True
            elif word_type == 'verb' and 'Verbs' in word_types:
                type_match = True
            elif word_type == 'adjective' and 'Adjectives' in word_types:
                type_match = True
            elif word_type == 'pronoun' and 'Pronouns' in word_types:
                type_match = True
            
            if not type_match:
                continue
            
            # For verbs, create separate entries for each tense/mood/voice combination
            if word_type == 'verb':
                for tense in paradigm_data.get('tenses', {}).keys():
                    for mood in paradigm_data['tenses'][tense].get('moods', {}).keys():
                        for voice in paradigm_data['tenses'][tense]['moods'][mood].get('voices', {}).keys():
                            subtype = f"{tense}:{mood}:{voice}"
                            table_id = self.session_manager.get_table_id(word_type, word, subtype)
                            tables.append({
                                'table_id': table_id,
                                'word_type': word_type,
                                'word': word,
                                'subtype': subtype,
                                'tense': tense,
                                'mood': mood,
                                'voice': voice
                            })
            # For nouns, adjectives, pronouns - one table per word
            else:
                table_id = self.session_manager.get_table_id(word_type, word)
                tables.append({
                    'table_id': table_id,
                    'word_type': word_type,
                    'word': word,
                    'subtype': None
                })
        
        # Handle starred items if requested
        if 'Starred' in word_types:
            for starred_key in self.starred_items:
                # Parse starred key format: "type:word" or "type:word:subtype"
                parts = starred_key.split(':')
                if len(parts) >= 2:
                    word_type = parts[0].lower()
                    word = parts[1]
                    subtype = ':'.join(parts[2:]) if len(parts) > 2 else None
                    
                    table_id = self.session_manager.get_table_id(word_type, word, subtype)
                    
                    # Check if not already in list
                    if not any(t['table_id'] == table_id for t in tables):
                        table_info = {
                            'table_id': table_id,
                            'word_type': word_type,
                            'word': word,
                            'subtype': subtype
                        }
                        if subtype and ':' in subtype:
                            verb_parts = subtype.split(':')
                            if len(verb_parts) == 3:
                                table_info['tense'] = verb_parts[0]
                                table_info['mood'] = verb_parts[1]
                                table_info['voice'] = verb_parts[2]
                        tables.append(table_info)
        
        return tables
    
    def start_study_session(self):
        """Start a study session with the selected options."""
        # Get selected word types
        selected_types = [key for key, var in self.word_type_vars.items() if var.get()]
        
        if not selected_types:
            messagebox.showwarning("No Word Types", "Please select at least one word type.")
            return
        
        # Get number of tables
        num_tables = self.num_tables_var.get()
        
        # Get focus area
        focus_area = self.focus_area_var.get()
        
        # Get spaced repetition setting
        use_spaced_rep = self.spaced_repetition_var.get()
        
        # Get all available tables for selected types
        all_tables = self.get_all_table_identifiers(selected_types)
        
        if not all_tables:
            messagebox.showerror("No Tables", "No tables found for the selected word types.")
            return
        
        # Select tables based on focus area
        import random
        selected_tables = []
        
        if focus_area == "Weak":
            # Get weak tables
            all_table_ids = [t['table_id'] for t in all_tables]
            weak_table_ids = self.session_manager.get_weak_tables(limit=num_tables * 2)
            
            # Filter to only include tables from selected types
            weak_tables = [t for t in all_tables if t['table_id'] in weak_table_ids]
            
            if len(weak_tables) < num_tables:
                messagebox.showinfo(
                    "Limited Weak Tables",
                    f"Only {len(weak_tables)} weak tables found. Adding random tables to reach {num_tables}."
                )
                selected_tables = weak_tables
                remaining = num_tables - len(weak_tables)
                available = [t for t in all_tables if t['table_id'] not in weak_table_ids]
                random.shuffle(available)
                selected_tables.extend(available[:remaining])
            else:
                random.shuffle(weak_tables)
                selected_tables = weak_tables[:num_tables]
        
        elif focus_area == "Untested":
            # Get untested tables
            all_table_ids = [t['table_id'] for t in all_tables]
            untested_table_ids = self.session_manager.get_untested_tables(all_table_ids, limit=num_tables * 2)
            
            untested_tables = [t for t in all_tables if t['table_id'] in untested_table_ids]
            
            if len(untested_tables) < num_tables:
                messagebox.showinfo(
                    "Limited Untested Tables",
                    f"Only {len(untested_tables)} untested tables found. Adding other tables to reach {num_tables}."
                )
                selected_tables = untested_tables
                remaining = num_tables - len(untested_tables)
                available = [t for t in all_tables if t['table_id'] not in untested_table_ids]
                random.shuffle(available)
                selected_tables.extend(available[:remaining])
            else:
                random.shuffle(untested_tables)
                selected_tables = untested_tables[:num_tables]
        
        else:  # General practice
            if use_spaced_rep:
                all_table_ids = [t['table_id'] for t in all_tables]
                spaced_table_ids = self.session_manager.get_tables_for_spaced_repetition(
                    all_table_ids, days_threshold=2, limit=num_tables * 2
                )
                spaced_tables = [t for t in all_tables if t['table_id'] in spaced_table_ids]
                
                if len(spaced_tables) >= num_tables:
                    random.shuffle(spaced_tables)
                    selected_tables = spaced_tables[:num_tables]
                else:
                    selected_tables = spaced_tables
                    remaining = num_tables - len(spaced_tables)
                    available = [t for t in all_tables if t['table_id'] not in spaced_table_ids]
                    random.shuffle(available)
                    selected_tables.extend(available[:remaining])
            else:
                random.shuffle(all_tables)
                selected_tables = all_tables[:num_tables]
        
        if not selected_tables:
            messagebox.showerror("No Tables", "Could not select any tables for the session.")
            return
        
        # Create session in database
        self.current_session_id = self.session_manager.create_session(
            num_tables=len(selected_tables),
            word_types=selected_types,
            focus_area=focus_area
        )
        
        # Add tables to session
        for i, table_info in enumerate(selected_tables):
            self.session_manager.add_session_table(
                self.current_session_id,
                table_info['table_id'],
                i
            )
        
        # Store session tables and reset index
        self.current_session_tables = selected_tables
        self.current_table_index = 0
        self.session_table_attempts = {}  # Track attempts per table
        
        # Start the session
        self.show_session_mode()
    
    def show_session_mode(self):
        """Display the session mode with one table at a time."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Clear all previous grid configurations
        for i in range(10):
            self.main_frame.grid_rowconfigure(i, weight=0)
            self.main_frame.grid_columnconfigure(i, weight=0)
        
        # Configure main_frame for session layout
        self.main_frame.grid_rowconfigure(0, weight=0)  # Progress bar - fixed
        self.main_frame.grid_rowconfigure(1, weight=0)  # Title - fixed
        self.main_frame.grid_rowconfigure(2, weight=1)  # Table area - expandable
        self.main_frame.grid_rowconfigure(3, weight=0)  # Buttons - fixed
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Get current table info
        if self.current_table_index >= len(self.current_session_tables):
            # Session complete
            self.show_session_review()
            return
        
        current_table = self.current_session_tables[self.current_table_index]
        table_id = current_table['table_id']
        
        # Initialize attempts tracking for this table
        if table_id not in self.session_table_attempts:
            self.session_table_attempts[table_id] = {
                'attempts': 0,
                'total_cells': 0,
                'correct_cells': 0
            }
        
        # Progress tracker frame
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=(10, 10))
        
        # Progress text
        progress_text = f"Table {self.current_table_index + 1} of {len(self.current_session_tables)}"
        progress_label = ttk.Label(
            progress_frame,
            text=progress_text,
            font=('Arial', 16, 'bold')
        )
        progress_label.pack(side='left')
        
        # Progress bar
        progress_percentage = (self.current_table_index / len(self.current_session_tables)) * 100
        progress_bar = ttk.Progressbar(
            progress_frame,
            length=300,
            mode='determinate',
            value=progress_percentage
        )
        progress_bar.pack(side='right', padx=(20, 0))
        
        # Exit session button
        exit_button = ttk.Button(
            progress_frame,
            text="Exit Session",
            command=self.exit_session,
            width=12
        )
        exit_button.pack(side='right', padx=(10, 10))
        
        # Table title frame
        title_frame = ttk.Frame(self.main_frame)
        title_frame.grid(row=1, column=0, pady=(10, 20))
        
        # Build title text
        word = current_table['word']
        word_type = current_table['word_type'].capitalize()
        
        if current_table['word_type'] == 'verb':
            tense = current_table.get('tense', '')
            mood = current_table.get('mood', '')
            voice = current_table.get('voice', '')
            title_text = f"{word} - {word_type} ({tense} {mood} {voice})"
        else:
            title_text = f"{word} - {word_type}"
        
        title_label = ttk.Label(
            title_frame,
            text=title_text,
            font=('Arial', 20, 'bold')
        )
        title_label.pack()
        
        # Table container (scrollable)
        table_container = ttk.Frame(self.main_frame)
        table_container.grid(row=2, column=0, sticky='nsew', padx=20, pady=10)
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Create the table based on word type
        self.create_session_table(table_container, current_table)
        
        # Buttons frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=3, column=0, pady=20)
        
        # Reveal button
        self.session_reveal_button = ttk.Button(
            button_frame,
            text="Reveal Answers",
            command=self.reveal_session_answers,
            width=18
        )
        self.session_reveal_button.pack(side='left', padx=5)
        
        # Retry button
        self.session_retry_button = ttk.Button(
            button_frame,
            text="Retry Incorrect",
            command=self.retry_session_incorrect,
            width=18,
            state='disabled'
        )
        self.session_retry_button.pack(side='left', padx=5)
        
        # Next table button (initially disabled)
        self.session_next_button = ttk.Button(
            button_frame,
            text="Next Table →",
            command=self.next_session_table,
            width=18,
            state='disabled',
            style='Accent.TButton'
        )
        self.session_next_button.pack(side='left', padx=5)
    
    def create_session_table(self, container, table_info):
        """Create the appropriate table based on word type."""
        word_type = table_info['word_type']
        word = table_info['word']
        
        # Store current session state for table creation
        self.session_current_word = word
        self.session_current_type = word_type
        
        if word_type == 'verb':
            # Set verb-specific state
            self.session_current_tense = table_info.get('tense')
            self.session_current_mood = table_info.get('mood')
            self.session_current_voice = table_info.get('voice')
            # Create verb table (will use existing methods)
            self.create_verb_table_for_session(container)
        elif word_type == 'noun':
            self.create_noun_table_for_session(container)
        elif word_type == 'adjective':
            self.create_adjective_table_for_session(container)
        elif word_type == 'pronoun':
            self.create_pronoun_table_for_session(container)
    
    def exit_session(self):
        """Exit the current session and return to startup."""
        if messagebox.askyesno("Exit Session", "Are you sure you want to exit? Progress will be saved."):
            # Save current state
            # (session is already being tracked in database)
            self.show_startup_page()
    
    def reveal_session_answers(self):
        """Reveal answers in session mode."""
        # Increment attempt counter
        current_table = self.current_session_tables[self.current_table_index]
        table_id = current_table['table_id']
        self.session_table_attempts[table_id]['attempts'] += 1
        
        # Use existing reveal logic but track correctness
        correct_count = 0
        total_count = 0
        
        for key, entry in self.entries.items():
            try:
                user_answer = entry.get().strip()
                correct_answer = self.get_correct_answer_for_session(key, current_table)
                
                total_count += 1
                
                if correct_answer:
                    is_correct = self.is_answer_correct(user_answer, correct_answer)
                    
                    if is_correct:
                        entry.configure(state='readonly', readonlybackground='#90EE90')  # Light green
                        correct_count += 1
                    else:
                        entry.configure(state='readonly', readonlybackground='#FFB6C6')  # Light red
                        entry.delete(0, tk.END)
                        entry.insert(0, correct_answer)
            except tk.TclError:
                pass
        
        # Store stats
        self.session_table_attempts[table_id]['total_cells'] = total_count
        self.session_table_attempts[table_id]['correct_cells'] = correct_count
        
        # Check if all correct
        if correct_count == total_count and total_count > 0:
            self.session_next_button.configure(state='normal')
            self.session_retry_button.configure(state='disabled')
            messagebox.showinfo("Perfect!", "All answers correct! You can proceed to the next table.")
        else:
            self.session_retry_button.configure(state='normal')
            accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
            messagebox.showinfo(
                "Review Needed",
                f"Accuracy: {accuracy:.1f}% ({correct_count}/{total_count} correct)\n\nPlease retry the incorrect answers."
            )
        
        # Disable reveal button
        self.session_reveal_button.configure(state='disabled')
    
    def retry_session_incorrect(self):
        """Allow retry of incorrect answers in session mode."""
        for key, entry in self.entries.items():
            try:
                # Get background color
                bg_color = entry.cget('readonlybackground')
                if bg_color and '#FFB6C6' in str(bg_color):  # Light red = incorrect
                    entry.configure(state='normal', bg='white')
                    entry.delete(0, tk.END)
            except tk.TclError:
                pass
        
        # Re-enable reveal, disable retry
        self.session_reveal_button.configure(state='normal')
        self.session_retry_button.configure(state='disabled')
    
    def next_session_table(self):
        """Move to the next table in the session."""
        # Record results for current table
        current_table = self.current_session_tables[self.current_table_index]
        table_id = current_table['table_id']
        
        stats = self.session_table_attempts[table_id]
        accuracy = (stats['correct_cells'] / stats['total_cells']) if stats['total_cells'] > 0 else 0
        needs_review = accuracy < 0.9
        
        # Update session database
        self.session_manager.update_session_table(
            self.current_session_id,
            table_id,
            stats['attempts'],
            accuracy,
            needs_review
        )
        
        # Update mastery tracking
        self.session_manager.record_table_attempt(
            table_id,
            current_table['word_type'],
            current_table['word'],
            accuracy,
            current_table.get('subtype')
        )
        
        # Move to next table
        self.current_table_index += 1
        
        # Clear entries for next table
        self.entries = {}
        self.error_labels = {}
        
        # Show next table or review
        self.show_session_mode()
    
    def get_correct_answer_for_session(self, key, table_info):
        """Get the correct answer for a specific cell in session mode."""
        word_type = table_info['word_type']
        word = table_info['word']
        
        # Get the paradigm for this word
        paradigm_key = None
        for pkey, pdata in self.paradigms.items():
            if pdata.get('word') == word and pdata.get('type', '').lower() == word_type:
                paradigm_key = pkey
                break
        
        if not paradigm_key:
            return None
        
        paradigm = self.paradigms[paradigm_key]
        
        # Parse the key to get the correct answer based on word type
        if word_type == 'noun':
            # Key format: "Case_number" (e.g., "Nominative_sg")
            parts = key.split('_')
            if len(parts) == 2:
                case, number = parts
                return paradigm.get('forms', {}).get(case.lower(), {}).get(number, '')
        
        elif word_type == 'adjective':
            # Key format: "Case_Gender_Number" (e.g., "Nominative_M_sg")
            parts = key.split('_')
            if len(parts) == 3:
                case, gender, number = parts
                return paradigm.get('forms', {}).get(case.lower(), {}).get(gender.lower(), {}).get(number, '')
        
        elif word_type == 'pronoun':
            # Similar to adjective structure
            parts = key.split('_')
            if len(parts) >= 2:
                case = parts[0]
                rest = '_'.join(parts[1:])
                return paradigm.get('forms', {}).get(case.lower(), {}).get(rest, '')
        
        elif word_type == 'verb':
            # Key format: "Person_Number" (e.g., "1_sg")
            tense = table_info.get('tense')
            mood = table_info.get('mood')
            voice = table_info.get('voice')
            
            parts = key.split('_')
            if len(parts) == 2:
                person, number = parts
                try:
                    forms = paradigm.get('tenses', {}).get(tense, {}).get('moods', {}).get(mood, {}).get('voices', {}).get(voice, {})
                    return forms.get(number, {}).get(person, '')
                except (KeyError, AttributeError):
                    return None
        
        return None
    
    def create_verb_table_for_session(self, container):
        """Create verb table for session mode."""
        word = self.session_current_word
        tense = self.session_current_tense
        mood = self.session_current_mood
        voice = self.session_current_voice
        
        # Find the paradigm
        paradigm = None
        for pkey, pdata in self.paradigms.items():
            if pdata.get('word') == word and pdata.get('type', '').lower() == 'verb':
                paradigm = pdata
                break
        
        if not paradigm:
            return
        
        # Get the forms for this tense/mood/voice
        try:
            forms = paradigm.get('tenses', {}).get(tense, {}).get('moods', {}).get(mood, {}).get('voices', {}).get(voice, {})
        except (KeyError, AttributeError):
            return
        
        # Create the table frame
        self.table_frame = ttk.Frame(container)
        self.table_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create table structure similar to create_verb_table
        # Configure columns
        self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        self.table_frame.grid_columnconfigure(1, weight=1, minsize=120)
        self.table_frame.grid_columnconfigure(2, weight=1, minsize=120)
        
        # Headers
        ttk.Label(self.table_frame, text="Person", font=('Arial', 14, 'bold')).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        ttk.Label(self.table_frame, text="Singular", font=('Arial', 14, 'bold')).grid(row=0, column=1, padx=10, pady=(5,10))
        ttk.Label(self.table_frame, text="Plural", font=('Arial', 14, 'bold')).grid(row=0, column=2, padx=10, pady=(5,10))
        
        # Create entries for each person
        persons = ["1", "2", "3"]
        person_labels = ["1st", "2nd", "3rd"]
        
        for i, (person, label) in enumerate(zip(persons, person_labels), 1):
            ttk.Label(self.table_frame, text=label, font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            # Singular
            entry_sg = tk.Entry(self.table_frame, width=15, font=('Times New Roman', 14), relief='solid', borderwidth=1)
            entry_sg.grid(row=i, column=1, padx=5, pady=6, sticky='ew')
            self.entries[f"{person}_sg"] = entry_sg
            
            # Plural
            entry_pl = tk.Entry(self.table_frame, width=15, font=('Times New Roman', 14), relief='solid', borderwidth=1)
            entry_pl.grid(row=i, column=2, padx=5, pady=6, sticky='ew')
            self.entries[f"{person}_pl"] = entry_pl
    
    def create_noun_table_for_session(self, container):
        """Create noun table for session mode."""
        word = self.session_current_word
        
        # Find the paradigm
        paradigm = None
        for pkey, pdata in self.paradigms.items():
            if pdata.get('word') == word and pdata.get('type', '').lower() == 'noun':
                paradigm = pdata
                break
        
        if not paradigm:
            return
        
        # Create the table frame
        self.table_frame = ttk.Frame(container)
        self.table_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Configure columns
        self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        self.table_frame.grid_columnconfigure(1, weight=1, minsize=120)
        self.table_frame.grid_columnconfigure(2, weight=1, minsize=120)
        
        # Headers
        ttk.Label(self.table_frame, text="Case", font=('Arial', 14, 'bold')).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        ttk.Label(self.table_frame, text="Singular", font=('Arial', 14, 'bold')).grid(row=0, column=1, padx=10, pady=(5,10))
        ttk.Label(self.table_frame, text="Plural", font=('Arial', 14, 'bold')).grid(row=0, column=2, padx=10, pady=(5,10))
        
        # Create entries for each case
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        
        for i, case in enumerate(cases, 1):
            ttk.Label(self.table_frame, text=case, font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            # Singular
            entry_sg = tk.Entry(self.table_frame, width=15, font=('Times New Roman', 14), relief='solid', borderwidth=1)
            entry_sg.grid(row=i, column=1, padx=5, pady=6, sticky='ew')
            self.entries[f"{case}_sg"] = entry_sg
            
            # Plural
            entry_pl = tk.Entry(self.table_frame, width=15, font=('Times New Roman', 14), relief='solid', borderwidth=1)
            entry_pl.grid(row=i, column=2, padx=5, pady=6, sticky='ew')
            self.entries[f"{case}_pl"] = entry_pl
    
    def create_adjective_table_for_session(self, container):
        """Create adjective table for session mode."""
        word = self.session_current_word
        
        # Find the paradigm
        paradigm = None
        for pkey, pdata in self.paradigms.items():
            if pdata.get('word') == word and pdata.get('type', '').lower() == 'adjective':
                paradigm = pdata
                break
        
        if not paradigm:
            return
        
        # Create the table frame
        self.table_frame = ttk.Frame(container)
        self.table_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Configure columns for 3 genders x 2 numbers = 6 columns + 1 for case labels
        self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        for col in range(1, 7):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=100)
        
        # Headers - row 0
        ttk.Label(self.table_frame, text="Case", font=('Arial', 14, 'bold')).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        
        # Gender headers with colspan
        ttk.Label(self.table_frame, text="Masculine", font=('Arial', 14, 'bold')).grid(row=0, column=1, columnspan=2, pady=(5,10))
        ttk.Label(self.table_frame, text="Feminine", font=('Arial', 14, 'bold')).grid(row=0, column=3, columnspan=2, pady=(5,10))
        ttk.Label(self.table_frame, text="Neuter", font=('Arial', 14, 'bold')).grid(row=0, column=5, columnspan=2, pady=(5,10))
        
        # Number sub-headers - row 1
        for col_offset in [1, 3, 5]:
            ttk.Label(self.table_frame, text="Sg", font=('Arial', 12)).grid(row=1, column=col_offset, pady=5)
            ttk.Label(self.table_frame, text="Pl", font=('Arial', 12)).grid(row=1, column=col_offset+1, pady=5)
        
        # Create entries for each case
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
        genders = ["M", "F", "N"]
        
        for i, case in enumerate(cases, 2):
            ttk.Label(self.table_frame, text=case, font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            col = 1
            for gender in genders:
                # Singular
                entry_sg = tk.Entry(self.table_frame, width=12, font=('Times New Roman', 14), relief='solid', borderwidth=1)
                entry_sg.grid(row=i, column=col, padx=2, pady=6, sticky='ew')
                self.entries[f"{case}_{gender}_sg"] = entry_sg
                col += 1
                
                # Plural
                entry_pl = tk.Entry(self.table_frame, width=12, font=('Times New Roman', 14), relief='solid', borderwidth=1)
                entry_pl.grid(row=i, column=col, padx=2, pady=6, sticky='ew')
                self.entries[f"{case}_{gender}_pl"] = entry_pl
                col += 1
    
    def create_pronoun_table_for_session(self, container):
        """Create pronoun table for session mode."""
        word = self.session_current_word
        
        # Find the paradigm
        paradigm = None
        for pkey, pdata in self.paradigms.items():
            if pdata.get('word') == word and pdata.get('type', '').lower() == 'pronoun':
                paradigm = pdata
                break
        
        if not paradigm:
            return
        
        # Create a simple table similar to nouns
        self.table_frame = ttk.Frame(container)
        self.table_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Get the forms to determine structure
        forms = paradigm.get('forms', {})
        if not forms:
            return
        
        # Determine columns from first case
        first_case_forms = list(forms.values())[0] if forms else {}
        columns = list(first_case_forms.keys())
        
        # Configure grid
        self.table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        for i in range(len(columns)):
            self.table_frame.grid_columnconfigure(i+1, weight=1, minsize=100)
        
        # Headers
        ttk.Label(self.table_frame, text="Case", font=('Arial', 14, 'bold')).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        for i, col_name in enumerate(columns, 1):
            ttk.Label(self.table_frame, text=col_name.replace('_', ' ').title(), font=('Arial', 14, 'bold')).grid(row=0, column=i, padx=10, pady=(5,10))
        
        # Create entries for each case
        cases = list(forms.keys())
        for i, case in enumerate(cases, 1):
            ttk.Label(self.table_frame, text=case.title(), font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            for j, col_name in enumerate(columns, 1):
                entry = tk.Entry(self.table_frame, width=15, font=('Times New Roman', 14), relief='solid', borderwidth=1)
                entry.grid(row=i, column=j, padx=5, pady=6, sticky='ew')
                self.entries[f"{case.title()}_{col_name}"] = entry
    
    def show_session_review(self):
        """Show the session review/results page."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Clear all previous grid configurations
        for i in range(10):
            self.main_frame.grid_rowconfigure(i, weight=0)
            self.main_frame.grid_columnconfigure(i, weight=0)
        
        # Configure for centered content
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create centered container
        center_container = ttk.Frame(self.main_frame)
        center_container.grid(row=0, column=0)
        
        # Title
        title_label = ttk.Label(
            center_container,
            text="Session Complete!",
            font=('Arial', 28, 'bold')
        )
        title_label.pack(pady=(0, 30))
        
        # Calculate overall statistics
        total_tables = len(self.current_session_tables)
        total_correct = 0
        total_cells = 0
        
        for table_id, stats in self.session_table_attempts.items():
            total_correct += stats['correct_cells']
            total_cells += stats['total_cells']
        
        overall_accuracy = (total_correct / total_cells * 100) if total_cells > 0 else 0
        
        # Update session in database
        self.session_manager.complete_session(
            self.current_session_id,
            overall_accuracy / 100  # Store as 0-1 fraction
        )
        
        # Overall stats frame
        stats_frame = ttk.Frame(center_container)
        stats_frame.pack(pady=20)
        
        ttk.Label(
            stats_frame,
            text=f"Overall Accuracy: {overall_accuracy:.1f}%",
            font=('Arial', 20, 'bold')
        ).pack()
        
        ttk.Label(
            stats_frame,
            text=f"Tables Completed: {total_tables}",
            font=('Arial', 14)
        ).pack(pady=5)
        
        ttk.Label(
            stats_frame,
            text=f"Total Cells: {total_correct}/{total_cells} correct",
            font=('Arial', 14)
        ).pack(pady=5)
        
        # Tables needing review
        tables_need_review = []
        for table_info in self.current_session_tables:
            table_id = table_info['table_id']
            if table_id in self.session_table_attempts:
                stats = self.session_table_attempts[table_id]
                accuracy = (stats['correct_cells'] / stats['total_cells']) if stats['total_cells'] > 0 else 0
                if accuracy < 0.9:
                    tables_need_review.append({
                        'word': table_info['word'],
                        'type': table_info['word_type'],
                        'accuracy': accuracy * 100,
                        'attempts': stats['attempts']
                    })
        
        if tables_need_review:
            review_label = ttk.Label(
                center_container,
                text="Tables Needing Review:",
                font=('Arial', 16, 'bold')
            )
            review_label.pack(pady=(20, 10))
            
            # Create scrollable list
            review_frame = ttk.Frame(center_container)
            review_frame.pack(fill='both', expand=True, pady=10)
            
            for table in tables_need_review:
                subtype_text = f" ({table.get('subtype', '')})" if table.get('subtype') else ""
                review_text = f"• {table['word']} ({table['type']}{subtype_text}) - {table['accuracy']:.1f}% - {table['attempts']} attempts"
                ttk.Label(
                    review_frame,
                    text=review_text,
                    font=('Arial', 12)
                ).pack(anchor='w', pady=2)
        
        # Buttons
        button_frame = ttk.Frame(center_container)
        button_frame.pack(pady=30)
        
        ttk.Button(
            button_frame,
            text="Start New Session",
            command=self.show_session_options_page,
            width=20
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Return to Home",
            command=self.show_startup_page,
            width=20
        ).pack(side='left', padx=5)
    
    def show_statistics(self):
        """Placeholder for showing statistics."""
        pass
    
    def show_latin_view(self):
        """Show the Latin grammar tables interface."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Clear all previous grid configurations
        for i in range(10):
            self.main_frame.grid_rowconfigure(i, weight=0)
            self.main_frame.grid_columnconfigure(i, weight=0)
        
        # Create a red background wrapper frame (use tk.Frame for proper background color)
        red_wrapper = tk.Frame(self.main_frame, bg='#8B0000')
        red_wrapper.grid(row=0, column=0, sticky='nsew')
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Configure red_wrapper rows to expand properly
        red_wrapper.grid_rowconfigure(0, weight=0)  # Title - fixed
        red_wrapper.grid_rowconfigure(1, weight=0)  # Type selector - fixed
        red_wrapper.grid_rowconfigure(2, weight=0)  # Word display - fixed
        red_wrapper.grid_rowconfigure(3, weight=0)  # Verb controls - fixed
        red_wrapper.grid_rowconfigure(4, weight=1)  # Table area - expands
        red_wrapper.grid_rowconfigure(5, weight=0)  # Buttons - fixed
        red_wrapper.grid_columnconfigure(0, weight=1)  # Center everything horizontally
        
        # Load Latin paradigms
        try:
            with open('latin_paradigms.json', 'r', encoding='utf-8') as f:
                self.latin_paradigms = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "Could not find latin_paradigms.json file")
            self.show_tables_view()  # Return to Greek view
            return
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Could not parse latin_paradigms.json file")
            self.show_tables_view()  # Return to Greek view
            return
        
        # Title frame with logo and back button
        title_frame = tk.Frame(red_wrapper, bg='#8B0000')
        title_frame.grid(row=0, column=0, pady=(20, 20), sticky='ew', padx=20)
        title_frame.grid_columnconfigure(0, weight=1)
        title_frame.grid_columnconfigure(1, weight=0)
        title_frame.grid_columnconfigure(2, weight=0)
        
        # Logo (Latin-specific logo)
        if self.latin_header_logo:
            # Use Latin header logo
            logo_label = tk.Label(title_frame, image=self.latin_header_logo, bg='#8B0000', cursor='hand2')
            logo_label.grid(row=0, column=0, sticky='w')
            # Keep a reference to prevent garbage collection
            logo_label.image = self.latin_header_logo
            # Bind click event to return to startup page
            logo_label.bind('<Button-1>', lambda e: self.show_startup_page())
        else:
            # Fallback to text title
            title_label = tk.Label(
                title_frame, 
                text="Bellerophon Grammar Study - Latin",
                bg='#8B0000',
                fg='white',
                font=('Arial', 24, 'bold')
            )
            title_label.grid(row=0, column=0, sticky='w')
        
        # Practice options frame
        practice_options_frame = tk.Frame(title_frame, bg='#8B0000')
        practice_options_frame.grid(row=0, column=1, sticky='ne', padx=(10, 10))
        
        # Prefill stems checkbox
        prefill_stems_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Prefill stems",
            variable=self.config.prefill_stems,
            command=self.on_latin_prefill_stems_toggle
        )
        prefill_stems_cb.grid(row=0, column=0, sticky='e', padx=(0, 10))

        # Randomize next checkbox
        randomize_next_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Randomize next",
            variable=self.config.randomize_next,
            command=self.on_randomize_toggle
        )
        randomize_next_cb.grid(row=0, column=1, sticky='e')

        # Auto advance checkbox
        auto_advance_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Auto advance",
            variable=self.config.auto_advance
        )
        auto_advance_cb.grid(row=0, column=2, sticky='e', padx=(10, 0))
        
        # Back to Greek button
        back_button = ttk.Button(
            title_frame,
            text="← Back to Greek",
            command=self.show_tables_view,
            width=15
        )
        back_button.grid(row=0, column=2, sticky='ne')
        
        # Type and word selection frame (matching Greek layout)
        mode_frame = tk.Frame(red_wrapper, bg='#8B0000')
        mode_frame.grid(row=1, column=0, pady=(0, 20), sticky='ew', padx=20)
        mode_frame.columnconfigure(1, weight=0, minsize=250)  # Type dropdown column
        mode_frame.columnconfigure(2, weight=0, minsize=100)  # Label column
        mode_frame.columnconfigure(3, weight=1)  # Dropdown column - expandable
        
        # Type selector label
        tk.Label(
            mode_frame,
            text="Type:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11)
        ).grid(row=0, column=0, padx=(0, 10))
        
        # Initialize Latin type variable
        self.latin_type_var = tk.StringVar(value="Noun")
        
        # Type dropdown - will be dynamically updated based on starred items
        self.latin_type_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.latin_type_var,
            values=self.get_available_latin_types(),
            font=('Times New Roman', 12),
            width=12,
            state='readonly'
        )
        self.latin_type_dropdown.grid(row=0, column=1, sticky='w')
        self.latin_type_dropdown.bind('<<ComboboxSelected>>', self.on_latin_type_change)
        
        # Lock current type checkbox (only visible when randomize is enabled)
        self.latin_lock_type_cb = ttk.Checkbutton(
            mode_frame,
            text="Lock current type",
            variable=self.config.lock_current_type
        )
        self.latin_lock_type_cb.grid(row=0, column=1, sticky='w', padx=(120, 0))
        # Show/hide based on current randomize state
        if self.config.randomize_next.get():
            self.latin_lock_type_cb.grid()
        else:
            self.latin_lock_type_cb.grid_remove()  # Hidden by default
        
        # Select word label
        tk.Label(
            mode_frame,
            text="Select word:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11)
        ).grid(row=0, column=2, sticky='w', padx=(20, 10))
        
        # Initialize Latin mode variables
        self.latin_word_var = tk.StringVar(value="femina (woman)")
        
        # Create word dropdown - only show nouns initially since Type defaults to "Noun"
        latin_words = []
        seen_nouns = set()
        for word_key, word_data in self.latin_paradigms.items():
            # Only show nouns on initial load (matching the default Type selection)
            if word_data.get('type') == 'noun':
                word_value = word_data.get('word', word_key)
                if word_value not in seen_nouns:
                    seen_nouns.add(word_value)
                    english = word_data.get('english', '')
                    display_text = f"{word_value} ({english})"
                    latin_words.append(display_text)
        
        word_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.latin_word_var,
            values=latin_words,
            state='readonly',
            font=('Times New Roman', 12),
            width=46
        )
        word_dropdown.grid(row=0, column=3, sticky='w')
        word_dropdown.bind('<<ComboboxSelected>>', self.on_latin_word_change)
        
        # Store reference to the dropdown for later use
        self.latin_word_dropdown = word_dropdown
        
        # Verb-specific controls (Tense, Voice, Mood) - initially hidden
        # Initialize Latin verb variables
        self.latin_tense_var = tk.StringVar(value="present")
        self.latin_voice_var = tk.StringVar(value="active")
        self.latin_mood_var = tk.StringVar(value="indicative")
        
        # Word display frame (matching Greek layout)
        word_frame = tk.Frame(red_wrapper, bg='#8B0000')
        word_frame.grid(row=2, column=0, pady=(5, 3))
        
        # Instruction label (will update based on type)
        self.latin_instruction_label = tk.Label(
            word_frame,
            text="Decline the word:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        self.latin_instruction_label.grid(row=0, column=0, padx=(0, 10))
        
        # Word display
        self.latin_word_label = tk.Label(
            word_frame,
            text="femina",
            bg='#8B0000',
            fg='white',
            font=('Times New Roman', 16, 'bold')
        )
        self.latin_word_label.grid(row=0, column=1)
        
        # Star button for favoriting tables (next to word label, like Greek side)
        self.latin_star_button = tk.Button(
            word_frame,
            text="☆",
            font=('Arial', 16),
            foreground="white",
            background='#8B0000',
            activeforeground="gold",
            activebackground="#6B0000",
            relief="flat",
            borderwidth=0,
            command=self.toggle_latin_star,
            cursor="hand2"
        )
        self.latin_star_button.bind("<Enter>", self.on_latin_star_hover_enter)
        self.latin_star_button.bind("<Leave>", self.on_latin_star_hover_leave)
        self.latin_star_button.grid(row=0, column=2, padx=(10, 0))
        
        # Initialize star button state
        self.update_latin_star_button()
        
        # Create separate verb controls frame (below word display)
        self.latin_verb_controls_frame = tk.Frame(red_wrapper, bg='#8B0000')
        self.latin_verb_controls_frame.grid(row=3, column=0, pady=(3, 10))
        
        # Tense label and dropdown
        self.latin_tense_label = tk.Label(
            self.latin_verb_controls_frame,
            text="Tense:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11)
        )
        self.latin_tense_label.grid(row=0, column=0, padx=(0, 5), sticky='e')
        
        self.latin_tense_dropdown = ttk.Combobox(
            self.latin_verb_controls_frame,
            textvariable=self.latin_tense_var,
            values=["present", "imperfect", "future", "perfect", "pluperfect", "future perfect"],
            font=('Times New Roman', 12),
            width=15,
            state='readonly'
        )
        self.latin_tense_dropdown.grid(row=0, column=1, padx=5)
        self.latin_tense_dropdown.bind('<<ComboboxSelected>>', self.on_latin_verb_change)
        
        # Voice label and dropdown
        self.latin_voice_label = tk.Label(
            self.latin_verb_controls_frame,
            text="Voice:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11)
        )
        self.latin_voice_label.grid(row=0, column=2, padx=(10, 5), sticky='e')
        
        self.latin_voice_dropdown = ttk.Combobox(
            self.latin_verb_controls_frame,
            textvariable=self.latin_voice_var,
            values=["active", "passive"],
            font=('Times New Roman', 12),
            width=12,
            state='readonly'
        )
        self.latin_voice_dropdown.grid(row=0, column=3, padx=5)
        self.latin_voice_dropdown.bind('<<ComboboxSelected>>', self.on_latin_verb_change)
        
        # Mood label and dropdown
        self.latin_mood_label = tk.Label(
            self.latin_verb_controls_frame,
            text="Mood:",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11)
        )
        self.latin_mood_label.grid(row=0, column=4, padx=(10, 5), sticky='e')
        
        self.latin_mood_dropdown = ttk.Combobox(
            self.latin_verb_controls_frame,
            textvariable=self.latin_mood_var,
            values=["indicative", "subjunctive", "imperative"],
            font=('Times New Roman', 12),
            width=12,
            state='readonly'
        )
        self.latin_mood_dropdown.grid(row=0, column=5, padx=5)
        self.latin_mood_dropdown.bind('<<ComboboxSelected>>', self.on_latin_verb_change)
        
        # Initially hide verb controls (will show when verb is selected)
        self.latin_verb_controls_frame.grid_remove()
        
        # Table container
        table_container = tk.Frame(red_wrapper, bg='#8B0000')
        table_container.grid(row=4, column=0, sticky='nsew', padx=20, pady=(10, 0))
        table_container.grid_columnconfigure(0, weight=1)  # Left padding
        table_container.grid_columnconfigure(1, weight=0)  # Table content
        table_container.grid_columnconfigure(2, weight=1)  # Right padding
        table_container.grid_rowconfigure(0, weight=1)
        
        # Create the table frame with red background
        self.latin_table_frame = tk.Frame(table_container, bg='#8B0000')
        self.latin_table_frame.grid(row=0, column=1, sticky='n', padx=10, pady=0)
        
        # Initialize entries dictionary and tracking for Latin
        self.latin_entries = {}
        self.latin_incorrect_entries = set()  # Track which Latin entries were incorrect
        self.latin_has_revealed = False  # Track if Latin answers have been revealed
        
        # Create the appropriate Latin table based on initial word
        # Get the first word to determine type
        initial_word = self.latin_word_var.get().split(' (')[0]
        initial_paradigm = None
        for key, data in self.latin_paradigms.items():
            word_value = data.get('word') or data.get('lemma')
            if word_value == initial_word:
                initial_paradigm = data
                break
        
        # Create table based on type
        if initial_paradigm and initial_paradigm.get('type') == 'verb':
            self.create_latin_verb_table()
        else:
            self.create_latin_noun_table()
        
        # Button frame
        button_frame = tk.Frame(red_wrapper, bg='#8B0000')
        button_frame.grid(row=5, column=0, pady=(15, 20))
        
        # Reveal button
        self.latin_reveal_button = ttk.Button(
            button_frame,
            text="Reveal Answers",
            command=self.reveal_latin_answers,
            width=15
        )
        self.latin_reveal_button.pack(side='left', padx=5)
        
        # Combined Reset/Retry button
        self.latin_reset_retry_button = ttk.Button(
            button_frame,
            text="Reset",
            command=self.smart_latin_reset_retry,
            width=15
        )
        self.latin_reset_retry_button.pack(side='left', padx=5)
        
        # Next button
        latin_next_button = ttk.Button(
            button_frame,
            text="Next",
            command=self.next_latin_word,
            width=15
        )
        latin_next_button.pack(side='left', padx=5)
    
    def create_latin_noun_table(self):
        """Create table for Latin noun declensions."""
        # Clear any existing widgets in the table frame
        for widget in self.latin_table_frame.winfo_children():
            widget.destroy()
        
        self.latin_entries.clear()
        
        # Get current word
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]  # Extract just the word
        
        # Find paradigm - search through all paradigms for matching noun
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'noun' and data.get('word') == word:
                paradigm = data
                break
        
        if not paradigm:
            return
        
        # Reset all column configurations first (clear any leftover from adjective table)
        for col in range(10):
            self.latin_table_frame.grid_columnconfigure(col, weight=0, minsize=0)
        
        # Configure grid weights for 3 columns only
        self.latin_table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        self.latin_table_frame.grid_columnconfigure(1, weight=1, minsize=120)
        self.latin_table_frame.grid_columnconfigure(2, weight=1, minsize=120)
        
        # Headers
        tk.Label(
            self.latin_table_frame,
            text="Case",
            bg='#8B0000',
            fg='white',
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=0, padx=10, pady=(5,10), sticky='e')
        tk.Label(
            self.latin_table_frame,
            text="Singular",
            bg='#8B0000',
            fg='white',
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=1, padx=10, pady=(5,10))
        tk.Label(
            self.latin_table_frame,
            text="Plural",
            bg='#8B0000',
            fg='white',
            font=('Arial', 14, 'bold')
        ).grid(row=0, column=2, padx=10, pady=(5,10))
        
        # Create input fields for each case (Latin has 6 cases including Ablative)
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative", "Ablative"]
        for i, case in enumerate(cases, 1):
            # Case label
            case_label = tk.Label(
                self.latin_table_frame,
                text=case,
                bg='#8B0000',
                fg='white',
                font=('Arial', 12, 'bold')
            )
            case_label.grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            # Singular entry
            entry_sg = tk.Entry(
                self.latin_table_frame,
                width=15,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_sg.grid(row=i, column=1, padx=5, pady=6, sticky='ew')
            self.latin_entries[f"{case}_sg"] = entry_sg
            entry_sg.bind('<Return>', lambda e, c=case: self.check_latin_single_entry(f"{c}_sg"))
            
            # Plural entry
            entry_pl = tk.Entry(
                self.latin_table_frame,
                width=15,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_pl.grid(row=i, column=2, padx=5, pady=6, sticky='ew')
            self.latin_entries[f"{case}_pl"] = entry_pl
            entry_pl.bind('<Return>', lambda e, c=case: self.check_latin_single_entry(f"{c}_pl"))
        
        # Apply prefill stems if enabled
        if self.config.prefill_stems.get():
            self.apply_latin_prefill_stems()
    
    def create_latin_adjective_table(self):
        """Create table for Latin adjective declensions (masculine, feminine, neuter)."""
        # Clear any existing widgets in the table frame
        for widget in self.latin_table_frame.winfo_children():
            widget.destroy()
        
        self.latin_entries.clear()
        
        # Get current word
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]  # Extract just the word
        
        # Find paradigm - search through all paradigms for matching adjective
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'adjective' and data.get('word') == word:
                paradigm = data
                break
        
        if not paradigm:
            return
        
        # Configure grid weights for 4 columns (case + 3 genders x 2 numbers = 7 cols total)
        self.latin_table_frame.grid_columnconfigure(0, weight=0, minsize=100)
        for col in range(1, 7):
            self.latin_table_frame.grid_columnconfigure(col, weight=1, minsize=100)
        
        # Top headers for genders
        tk.Label(
            self.latin_table_frame,
            text="",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, padx=5, pady=(5,2))
        
        tk.Label(
            self.latin_table_frame,
            text="Masculine",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=1, columnspan=2, padx=5, pady=(5,2))
        
        tk.Label(
            self.latin_table_frame,
            text="Feminine",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=3, columnspan=2, padx=5, pady=(5,2))
        
        tk.Label(
            self.latin_table_frame,
            text="Neuter",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=5, columnspan=2, padx=5, pady=(5,2))
        
        # Sub-headers for singular/plural
        tk.Label(
            self.latin_table_frame,
            text="Case",
            bg='#8B0000',
            fg='white',
            font=('Arial', 11, 'bold')
        ).grid(row=1, column=0, padx=5, pady=(2,10), sticky='e')
        
        for col_offset, gender in enumerate(['Masculine', 'Feminine', 'Neuter']):
            base_col = 1 + (col_offset * 2)
            tk.Label(
                self.latin_table_frame,
                text="Sg",
                bg='#8B0000',
                fg='white',
                font=('Arial', 10)
            ).grid(row=1, column=base_col, padx=3, pady=(2,10))
            
            tk.Label(
                self.latin_table_frame,
                text="Pl",
                bg='#8B0000',
                fg='white',
                font=('Arial', 10)
            ).grid(row=1, column=base_col+1, padx=3, pady=(2,10))
        
        # Create input fields for each case
        cases = ["nominative", "vocative", "accusative", "genitive", "dative", "ablative"]
        case_labels = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative", "Ablative"]
        
        for i, (case, label) in enumerate(zip(cases, case_labels), 2):
            # Case label
            tk.Label(
                self.latin_table_frame,
                text=label,
                bg='#8B0000',
                fg='white',
                font=('Arial', 11, 'bold')
            ).grid(row=i, column=0, padx=10, pady=4, sticky='e')
            
            # Create entries for each gender (masculine, feminine, neuter) and number (sg, pl)
            for gender_idx, gender in enumerate(['masculine', 'feminine', 'neuter']):
                base_col = 1 + (gender_idx * 2)
                
                # Singular entry
                entry_sg = tk.Entry(
                    self.latin_table_frame,
                    width=12,
                    font=('Times New Roman', 12),
                    relief='solid',
                    borderwidth=1
                )
                entry_sg.grid(row=i, column=base_col, padx=2, pady=4, sticky='ew')
                key_sg = f"{case}_{gender}_sg"
                self.latin_entries[key_sg] = entry_sg
                entry_sg.bind('<Return>', lambda e, k=key_sg: self.check_latin_single_entry(k))
                
                # Plural entry
                entry_pl = tk.Entry(
                    self.latin_table_frame,
                    width=12,
                    font=('Times New Roman', 12),
                    relief='solid',
                    borderwidth=1
                )
                entry_pl.grid(row=i, column=base_col+1, padx=2, pady=4, sticky='ew')
                key_pl = f"{case}_{gender}_pl"
                self.latin_entries[key_pl] = entry_pl
                entry_pl.bind('<Return>', lambda e, k=key_pl: self.check_latin_single_entry(k))
    
    def create_latin_verb_table(self):
        """Create the Latin verb conjugation table."""
        # Clear existing table
        for widget in self.latin_table_frame.winfo_children():
            widget.destroy()
        
        # Clear entries
        self.latin_entries.clear()
        
        # Get the selected verb and tense/voice/mood
        word_display = self.latin_word_var.get()
        lemma = word_display.split(' (')[0]
        tense = self.latin_tense_var.get()
        voice = self.latin_voice_var.get()
        mood = self.latin_mood_var.get()
        
        # Find the matching verb paradigm with specific tense/voice/mood
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if (data.get('type') == 'verb' and 
                data.get('lemma') == lemma and
                data.get('tense') == tense and
                data.get('voice') == voice and
                data.get('mood') == mood):
                paradigm = data
                break
        
        if not paradigm:
            # Show message that this combination doesn't exist yet
            tk.Label(
                self.latin_table_frame,
                text=f"The {tense} {mood} {voice} form is not yet available.",
                bg='#8B0000',
                fg='white',
                font=('Arial', 12)
            ).grid(row=0, column=0, pady=20)
            return
        
        # Reset all column configurations first (clear any leftover from adjective table)
        for col in range(10):
            self.latin_table_frame.grid_columnconfigure(col, weight=0, minsize=0)
        
        # Configure grid columns for verb table (3 columns only)
        self.latin_table_frame.grid_columnconfigure(0, weight=1)  # Person column
        self.latin_table_frame.grid_columnconfigure(1, weight=1)  # Singular column
        self.latin_table_frame.grid_columnconfigure(2, weight=1)  # Plural column
        
        # Create table headers
        tk.Label(
            self.latin_table_frame,
            text="Person",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        tk.Label(
            self.latin_table_frame,
            text="Singular",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(
            self.latin_table_frame,
            text="Plural",
            bg='#8B0000',
            fg='white',
            font=('Arial', 12, 'bold')
        ).grid(row=0, column=2, padx=10, pady=10)
        
        # Create rows for each person (1st, 2nd, 3rd)
        persons = ["1st", "2nd", "3rd"]
        
        for i, person in enumerate(persons, start=1):
            # Person label
            person_label = tk.Label(
                self.latin_table_frame,
                text=person,
                bg='#8B0000',
                fg='white',
                font=('Arial', 12, 'bold')
            )
            person_label.grid(row=i, column=0, padx=10, pady=6, sticky='e')
            
            # Singular entry
            entry_sg = tk.Entry(
                self.latin_table_frame,
                width=15,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_sg.grid(row=i, column=1, padx=5, pady=6, sticky='ew')
            self.latin_entries[f"{person}_sg"] = entry_sg
            entry_sg.bind('<Return>', lambda e, p=person: self.check_latin_single_entry(f"{p}_sg"))
            
            # Plural entry
            entry_pl = tk.Entry(
                self.latin_table_frame,
                width=15,
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_pl.grid(row=i, column=2, padx=5, pady=6, sticky='ew')
            self.latin_entries[f"{person}_pl"] = entry_pl
            entry_pl.bind('<Return>', lambda e, p=person: self.check_latin_single_entry(f"{p}_pl"))
        
        # Apply prefill stems if enabled
        if self.config.prefill_stems.get():
            self.apply_latin_prefill_stems()
    
    def on_latin_word_change(self, event=None):
        """Handle Latin word selection change."""
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        self.latin_word_label.config(text=word)
        
        # Update star button
        self.update_latin_star_button()
        
        # Reset tracking variables when changing words
        self.latin_has_revealed = False
        self.latin_incorrect_entries.clear()
        
        # Re-enable reveal button
        if hasattr(self, 'latin_reveal_button'):
            self.latin_reveal_button.configure(state='normal')
        
        # Update Reset/Retry button
        if hasattr(self, 'latin_reset_retry_button'):
            self.update_latin_reset_retry_button()
        
        # Check if we're in Starred mode - parse the display differently
        latin_type = self.latin_type_var.get()
        if latin_type == "Starred":
            # Parse starred item format
            # For verbs: "word (voice tense mood)"
            # For nouns: "word (english)"
            if '(' in word_display:
                params = word_display.split('(')[1].rstrip(')').strip()
                param_parts = params.split()
                
                if len(param_parts) == 3:
                    # It's a verb with voice/tense/mood - lock to this conjugation
                    voice, tense, mood = param_parts
                    self.latin_voice_var.set(voice)
                    self.latin_tense_var.set(tense)
                    self.latin_mood_var.set(mood)
                    self.latin_instruction_label.config(text="Conjugate the verb:")
                    self.show_latin_verb_controls()
                    # Disable the dropdowns so user can't change them in Starred mode
                    if hasattr(self, 'latin_tense_dropdown'):
                        self.latin_tense_dropdown.configure(state='disabled')
                    if hasattr(self, 'latin_voice_dropdown'):
                        self.latin_voice_dropdown.configure(state='disabled')
                    if hasattr(self, 'latin_mood_dropdown'):
                        self.latin_mood_dropdown.configure(state='disabled')
                    self.create_latin_verb_table()
                    return
                else:
                    # It's a noun
                    self.latin_instruction_label.config(text="Decline the word:")
                    self.hide_latin_verb_controls()
                    self.create_latin_noun_table()
                    return
        else:
            # Not in Starred mode - enable the verb dropdowns
            if hasattr(self, 'latin_tense_dropdown'):
                self.latin_tense_dropdown.configure(state='readonly')
            if hasattr(self, 'latin_voice_dropdown'):
                self.latin_voice_dropdown.configure(state='readonly')
            if hasattr(self, 'latin_mood_dropdown'):
                self.latin_mood_dropdown.configure(state='readonly')
        
        # Regular (non-starred) word change
        # Find paradigm to determine type
        paradigm = None
        for key, data in self.latin_paradigms.items():
            word_value = data.get('word') or data.get('lemma')
            if word_value == word:
                paradigm = data
                break
        
        # Update instruction label and show/hide verb controls based on type
        if paradigm and paradigm.get('type') == 'verb':
            self.latin_instruction_label.config(text="Conjugate the verb:")
            self.show_latin_verb_controls()
            # Update dropdown options based on available forms for this verb
            self.update_latin_verb_dropdown_options(word)
            self.create_latin_verb_table()
        elif paradigm and paradigm.get('type') == 'adjective':
            self.latin_instruction_label.config(text="Decline the adjective:")
            self.hide_latin_verb_controls()
            self.create_latin_adjective_table()
        else:
            self.latin_instruction_label.config(text="Decline the word:")
            self.hide_latin_verb_controls()
            self.create_latin_noun_table()
    
    def show_latin_verb_controls(self):
        """Show the Latin verb tense/voice/mood controls."""
        self.latin_verb_controls_frame.grid()
    
    def hide_latin_verb_controls(self):
        """Hide the Latin verb tense/voice/mood controls."""
        self.latin_verb_controls_frame.grid_remove()
    
    def update_latin_verb_dropdown_options(self, lemma):
        """Update the verb dropdown options to only show forms that exist for this lemma."""
        # Find all forms that exist for this lemma
        available_tenses = set()
        available_voices = set()
        available_moods = set()
        
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'verb' and data.get('lemma') == lemma:
                tense = data.get('tense')
                voice = data.get('voice')
                mood = data.get('mood')
                if tense:
                    available_tenses.add(tense)
                if voice:
                    available_voices.add(voice)
                if mood:
                    available_moods.add(mood)
        
        # Define the preferred order for dropdowns
        tense_order = ["present", "imperfect", "future", "perfect", "pluperfect", "future perfect"]
        voice_order = ["active", "passive"]
        mood_order = ["indicative", "subjunctive", "imperative"]
        
        # Sort the available values according to the preferred order
        sorted_tenses = [t for t in tense_order if t in available_tenses]
        sorted_voices = [v for v in voice_order if v in available_voices]
        sorted_moods = [m for m in mood_order if m in available_moods]
        
        # Update the dropdown values
        if hasattr(self, 'latin_tense_dropdown'):
            self.latin_tense_dropdown['values'] = sorted_tenses
            # Reset to first available if current selection is not available
            current_tense = self.latin_tense_var.get()
            if current_tense not in sorted_tenses and sorted_tenses:
                self.latin_tense_var.set(sorted_tenses[0])
        
        if hasattr(self, 'latin_voice_dropdown'):
            self.latin_voice_dropdown['values'] = sorted_voices
            current_voice = self.latin_voice_var.get()
            if current_voice not in sorted_voices and sorted_voices:
                self.latin_voice_var.set(sorted_voices[0])
        
        if hasattr(self, 'latin_mood_dropdown'):
            self.latin_mood_dropdown['values'] = sorted_moods
            current_mood = self.latin_mood_var.get()
            if current_mood not in sorted_moods and sorted_moods:
                self.latin_mood_var.set(sorted_moods[0])
    
    def on_latin_verb_change(self, event=None):
        """Handle Latin verb tense/voice/mood selection change."""
        # Reset tracking variables when changing verb forms
        self.latin_has_revealed = False
        self.latin_incorrect_entries.clear()
        
        # Re-enable reveal button
        if hasattr(self, 'latin_reveal_button'):
            self.latin_reveal_button.configure(state='normal')
        
        # Update Reset/Retry button
        if hasattr(self, 'latin_reset_retry_button'):
            self.update_latin_reset_retry_button()
        
        # Update available options based on current selections
        word_display = self.latin_word_var.get()
        lemma = word_display.split(' (')[0]
        self.update_latin_verb_dropdown_options_filtered(lemma)
        
        # Recreate the verb table with new tense/voice/mood
        self.create_latin_verb_table()
        
        # Update star button
        self.update_latin_star_button()
    
    def update_latin_verb_dropdown_options_filtered(self, lemma):
        """Update dropdown options based on current selections to show only valid combinations."""
        # Get current selections
        current_tense = self.latin_tense_var.get()
        current_voice = self.latin_voice_var.get()
        current_mood = self.latin_mood_var.get()
        
        # Find all forms that exist for this lemma with at least one current constraint
        available_tenses = set()
        available_voices = set()
        available_moods = set()
        
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'verb' and data.get('lemma') == lemma:
                tense = data.get('tense')
                voice = data.get('voice')
                mood = data.get('mood')
                
                # Collect options that work with current selections
                # For tenses: show tenses that exist with current voice and mood
                if voice == current_voice and mood == current_mood and tense:
                    available_tenses.add(tense)
                
                # For voices: show voices that exist with current tense and mood
                if tense == current_tense and mood == current_mood and voice:
                    available_voices.add(voice)
                
                # For moods: show moods that exist with current tense and voice
                if tense == current_tense and voice == current_voice and mood:
                    available_moods.add(mood)
        
        # Define the preferred order for dropdowns
        tense_order = ["present", "imperfect", "future", "perfect", "pluperfect", "future perfect"]
        voice_order = ["active", "passive"]
        mood_order = ["indicative", "subjunctive", "imperative"]
        
        # Sort the available values according to the preferred order
        sorted_tenses = [t for t in tense_order if t in available_tenses]
        sorted_voices = [v for v in voice_order if v in available_voices]
        sorted_moods = [m for m in mood_order if m in available_moods]
        
        # Update the dropdown values (only if not empty - keep previous values if filtering results in empty)
        if hasattr(self, 'latin_tense_dropdown') and sorted_tenses:
            self.latin_tense_dropdown['values'] = sorted_tenses
        
        if hasattr(self, 'latin_voice_dropdown') and sorted_voices:
            self.latin_voice_dropdown['values'] = sorted_voices
        
        if hasattr(self, 'latin_mood_dropdown') and sorted_moods:
            self.latin_mood_dropdown['values'] = sorted_moods
    
    def on_latin_type_change(self, event=None):
        """Handle Latin type selection change."""
        latin_type = self.latin_type_var.get()
        
        # Update word dropdown based on type
        latin_words = []
        seen_verbs = set()  # Track unique verb lemmas
        seen_nouns = set()  # Track unique nouns
        seen_adjectives = set()  # Track unique adjectives
        
        if latin_type == "Starred":
            # Show starred Latin items
            for item_key in self.latin_starred_items:
                parts = item_key.split(':')
                if len(parts) >= 3 and parts[0] == "Latin":
                    word_type = parts[1]
                    word = parts[2]
                    
                    if word_type == "Verb" and len(parts) >= 6:
                        # Format: Latin:Verb:word:voice:tense:mood
                        voice = parts[3]
                        tense = parts[4]
                        mood = parts[5]
                        display = f"{word} ({voice} {tense} {mood})"
                        latin_words.append(display)
                    elif word_type == "Noun":
                        # Find English translation
                        english = ""
                        for key, data in self.latin_paradigms.items():
                            word_value = data.get('word', '')
                            if word_value == word and data.get('type') == 'noun':
                                english = data.get('english', '')
                                break
                        display = f"{word} ({english})" if english else word
                        latin_words.append(display)
                    elif word_type == "Adjective":
                        # Find English translation
                        english = ""
                        for key, data in self.latin_paradigms.items():
                            word_value = data.get('word', '')
                            if word_value == word and data.get('type') == 'adjective':
                                english = data.get('english', '')
                                break
                        display = f"{word} ({english})" if english else word
                        latin_words.append(display)
        else:
            # Regular type selection
            for word_key, word_data in self.latin_paradigms.items():
                if latin_type == "Noun" and word_data.get('type') == 'noun':
                    word_value = word_data.get('word', word_key)
                    # Only add unique nouns (avoid duplicates)
                    if word_value not in seen_nouns:
                        seen_nouns.add(word_value)
                        english = word_data.get('english', '')
                        display_text = f"{word_value} ({english})"
                        latin_words.append(display_text)
                elif latin_type == "Verb" and word_data.get('type') == 'verb':
                    lemma = word_data.get('lemma', word_key)
                    # Only add unique lemmas (not every tense/voice/mood combination)
                    if lemma not in seen_verbs:
                        seen_verbs.add(lemma)
                        english = word_data.get('english', '')
                        display_text = f"{lemma} ({english})"
                        latin_words.append(display_text)
                elif latin_type == "Adjective" and word_data.get('type') == 'adjective':
                    word_value = word_data.get('word', word_key)
                    # Only add unique adjectives
                    if word_value not in seen_adjectives:
                        seen_adjectives.add(word_value)
                        english = word_data.get('english', '')
                        display_text = f"{word_value} ({english})"
                        latin_words.append(display_text)
        
        if latin_words:
            # Find the word dropdown and update it
            for widget in self.main_frame.winfo_children():
                if isinstance(widget, tk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Combobox) and grandchild.cget('textvariable') == str(self.latin_word_var):
                                    grandchild['values'] = latin_words
                                    if latin_words:
                                        self.latin_word_var.set(latin_words[0])
                                        self.on_latin_word_change()
                                    break
    
    def on_latin_prefill_stems_toggle(self):
        """Handle the Latin prefill stems toggle change"""
        if self.config.prefill_stems.get():
            # Prefill stems are now enabled, apply to current table
            self.apply_latin_prefill_stems()
        else:
            # Prefill stems disabled, clear the prefilled content
            self.clear_latin_prefill_stems()
    
    def apply_latin_prefill_stems(self):
        """Apply prefill stems to the current Latin table"""
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        
        # Find paradigm
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'noun' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'verb' and data.get('lemma') == word:
                # For verbs, match current tense/voice/mood
                if (data.get('tense') == self.latin_tense_var.get() and
                    data.get('voice') == self.latin_voice_var.get() and
                    data.get('mood') == self.latin_mood_var.get()):
                    paradigm = data
                    break
        
        if not paradigm:
            return
        
        if paradigm.get('type') == 'noun':
            # Apply noun stems
            stem = paradigm.get('stem', '')
            stem_nom_sg = paradigm.get('stem_nom_sg', stem)  # Some nouns have different nominative singular stem
            
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative", "Ablative"]
            
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    if entry_key in self.latin_entries:
                        entry = self.latin_entries[entry_key]
                        # Use special nom sg stem if it's nominative singular, otherwise regular stem
                        if case == "Nominative" and number == "sg":
                            entry.delete(0, tk.END)
                            entry.insert(0, stem_nom_sg)
                        else:
                            entry.delete(0, tk.END)
                            entry.insert(0, stem)
                        # Don't change text color - keep it black for readability
        
        elif paradigm.get('type') == 'verb':
            # Hardcoded verb stems for accuracy
            lemma = paradigm.get('lemma')
            tense = paradigm.get('tense')
            voice = paradigm.get('voice')
            
            # Define hardcoded stems for each verb
            verb_stems = {
                'amo': {
                    'present': 'am',
                    'imperfect': 'am',
                    'future': 'am',
                    'perfect_active': 'amav',
                    'pluperfect_active': 'amav',
                    'future_perfect_active': 'amav',
                    'perfect_passive': 'amat',
                    'pluperfect_passive': 'amat',
                    'future_perfect_passive': 'amat'
                },
                'audio': {
                    'present': 'audi',
                    'imperfect': 'audi',
                    'future': 'audi',
                    'perfect_active': 'audiv',
                    'pluperfect_active': 'audiv',
                    'future_perfect_active': 'audiv',
                    'perfect_passive': 'audit',
                    'pluperfect_passive': 'audit',
                    'future_perfect_passive': 'audit'
                },
                'rego': {
                    'present': 'reg',
                    'imperfect': 'reg',
                    'future': 'reg',
                    'perfect_active': 'rex',
                    'pluperfect_active': 'rex',
                    'future_perfect_active': 'rex',
                    'perfect_passive': 'rect',
                    'pluperfect_passive': 'rect',
                    'future_perfect_passive': 'rect'
                },
                'moneo': {
                    'present': 'mone',
                    'imperfect': 'mone',
                    'future': 'mone',
                    'perfect_active': 'monu',
                    'pluperfect_active': 'monu',
                    'future_perfect_active': 'monu',
                    'perfect_passive': 'monit',
                    'pluperfect_passive': 'monit',
                    'future_perfect_passive': 'monit'
                },
                'sum': {
                    # sum has no stems - will be empty string
                }
            }
            
            stem = ''
            if lemma in verb_stems:
                stems = verb_stems[lemma]
                
                # Determine which stem to use based on tense and voice
                if tense in ['present', 'imperfect', 'future']:
                    stem = stems.get(tense, '')
                elif tense in ['perfect', 'pluperfect', 'future perfect']:
                    if voice == 'passive':
                        stem = stems.get(f'{tense.replace(" ", "_")}_passive', '')
                    else:
                        stem = stems.get(f'{tense.replace(" ", "_")}_active', '')
            
            # Apply stem to all entries (only if stem is not empty)
            if stem:
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        if entry_key in self.latin_entries:
                            entry = self.latin_entries[entry_key]
                            entry.delete(0, tk.END)
                            entry.insert(0, stem)
                            # Don't change text color - keep it black for readability
    
    def clear_latin_prefill_stems(self):
        """Clear only the user-entered endings, preserve the prefilled stems."""
        if not self.config.prefill_stems.get():
            return
            
        # Get the current paradigm to determine stems
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        
        # Find paradigm
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'noun' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'verb' and data.get('lemma') == word:
                # For verbs, match current tense/voice/mood
                if (data.get('tense') == self.latin_tense_var.get() and
                    data.get('voice') == self.latin_voice_var.get() and
                    data.get('mood') == self.latin_mood_var.get()):
                    paradigm = data
                    break
        
        if not paradigm:
            return
            
        if paradigm.get('type') == 'noun':
            # Get the stems
            stem = paradigm.get('stem', '')
            stem_nom_sg = paradigm.get('stem_nom_sg', stem)
            
            # Reset to just the stems
            cases = ["Nominative", "Genitive", "Dative", "Accusative", "Ablative", "Vocative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    if entry_key in self.latin_entries:
                        entry = self.latin_entries[entry_key]
                        entry.delete(0, tk.END)
                        # Use special nom sg stem if it's nominative singular, otherwise regular stem
                        if case == "Nominative" and number == "sg":
                            entry.insert(0, stem_nom_sg)
                        else:
                            entry.insert(0, stem)
                        
        elif paradigm.get('type') == 'verb':
            # Hardcoded verb stems for accuracy (same as apply_latin_prefill_stems)
            lemma = paradigm.get('lemma')
            tense = paradigm.get('tense')
            voice = paradigm.get('voice')
            
            # Define hardcoded stems for each verb
            verb_stems = {
                'amo': {
                    'present': 'am',
                    'imperfect': 'am',
                    'future': 'am',
                    'perfect_active': 'amav',
                    'pluperfect_active': 'amav',
                    'future_perfect_active': 'amav',
                    'perfect_passive': 'amat',
                    'pluperfect_passive': 'amat',
                    'future_perfect_passive': 'amat'
                },
                'audio': {
                    'present': 'audi',
                    'imperfect': 'audi',
                    'future': 'audi',
                    'perfect_active': 'audiv',
                    'pluperfect_active': 'audiv',
                    'future_perfect_active': 'audiv',
                    'perfect_passive': 'audit',
                    'pluperfect_passive': 'audit',
                    'future_perfect_passive': 'audit'
                },
                'rego': {
                    'present': 'reg',
                    'imperfect': 'reg',
                    'future': 'reg',
                    'perfect_active': 'rex',
                    'pluperfect_active': 'rex',
                    'future_perfect_active': 'rex',
                    'perfect_passive': 'rect',
                    'pluperfect_passive': 'rect',
                    'future_perfect_passive': 'rect'
                },
                'moneo': {
                    'present': 'mone',
                    'imperfect': 'mone',
                    'future': 'mone',
                    'perfect_active': 'monu',
                    'pluperfect_active': 'monu',
                    'future_perfect_active': 'monu',
                    'perfect_passive': 'monit',
                    'pluperfect_passive': 'monit',
                    'future_perfect_passive': 'monit'
                },
                'sum': {
                    # sum has no stems - will be empty string
                }
            }
            
            stem = ''
            if lemma in verb_stems:
                stems = verb_stems[lemma]
                
                # Determine which stem to use based on tense and voice
                if tense in ['present', 'imperfect', 'future']:
                    stem = stems.get(tense, '')
                elif tense in ['perfect', 'pluperfect', 'future perfect']:
                    if voice == 'passive':
                        stem = stems.get(f'{tense.replace(" ", "_")}_passive', '')
                    else:
                        stem = stems.get(f'{tense.replace(" ", "_")}_active', '')
            
            # Reset to just the stems (only if stem is not empty)
            if stem:
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        if entry_key in self.latin_entries:
                            entry = self.latin_entries[entry_key]
                            entry.delete(0, tk.END)
                            entry.insert(0, stem)
    
    def reveal_latin_answers(self):
        """Reveal answers for Latin table and track incorrect ones."""
        # Prevent revealing twice in a row
        if self.latin_has_revealed:
            return
        
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        
        # Find paradigm - could be noun, adjective, or verb
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'noun' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'adjective' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'verb' and data.get('lemma') == word:
                # For verbs, also match tense/voice/mood
                if (data.get('tense') == self.latin_tense_var.get() and
                    data.get('voice') == self.latin_voice_var.get() and
                    data.get('mood') == self.latin_mood_var.get()):
                    paradigm = data
                    break
        
        if not paradigm:
            return
        
        # Clear previous incorrect entries tracking
        self.latin_incorrect_entries.clear()
        
        if paradigm.get('type') == 'adjective':
            # Handle adjective declension (all 3 genders)
            cases = ["nominative", "vocative", "accusative", "genitive", "dative", "ablative"]
            genders = ["masculine", "feminine", "neuter"]
            
            for case in cases:
                for gender in genders:
                    for number in ["sg", "pl"]:
                        entry_key = f"{case}_{gender}_{number}"
                        if entry_key in self.latin_entries:
                            entry = self.latin_entries[entry_key]
                            user_answer = entry.get().strip()
                            correct_answer = paradigm['forms'][gender][case][number]
                            
                            if user_answer.lower() == correct_answer.lower():
                                entry.configure(state='readonly', readonlybackground='#B8860B')  # Dark goldenrod
                            else:
                                # Track as incorrect
                                self.latin_incorrect_entries.add(entry_key)
                                # First delete and insert the correct answer
                                entry.delete(0, tk.END)
                                entry.insert(0, correct_answer)
                                # Then set to readonly with red background
                                entry.configure(state='readonly', readonlybackground='#FFB6C6')  # Light red
        
        elif paradigm.get('type') == 'noun':
            # Handle noun declension
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative", "Ablative"]
            
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    if entry_key in self.latin_entries:
                        entry = self.latin_entries[entry_key]
                        user_answer = entry.get().strip()
                        correct_answer = paradigm['forms'][case.lower()][number]
                        
                        if user_answer.lower() == correct_answer.lower():
                            entry.configure(state='readonly', readonlybackground='#B8860B')  # Dark goldenrod
                        else:
                            # Track as incorrect
                            self.latin_incorrect_entries.add(entry_key)
                            # First delete and insert the correct answer
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            # Then set to readonly with red background
                            entry.configure(state='readonly', readonlybackground='#FFB6C6')  # Light red
        
        elif paradigm.get('type') == 'verb':
            # Handle verb conjugation
            persons = ["1st", "2nd", "3rd"]
            
            for person in persons:
                for number in ["sg", "pl"]:
                    entry_key = f"{person}_{number}"
                    if entry_key in self.latin_entries:
                        entry = self.latin_entries[entry_key]
                        user_answer = entry.get().strip()
                        correct_answer = paradigm.get(entry_key, '')
                        
                        if user_answer.lower() == correct_answer.lower():
                            entry.configure(state='readonly', readonlybackground='#B8860B')  # Dark goldenrod
                        else:
                            # Track as incorrect
                            self.latin_incorrect_entries.add(entry_key)
                            # First delete and insert the correct answer
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            # Then set to readonly with red background
                            entry.configure(state='readonly', readonlybackground='#FFB6C6')  # Light red
        
        # Mark as revealed and disable reveal button
        self.latin_has_revealed = True
        self.latin_reveal_button.configure(state='disabled')
        
        # Update the Reset/Retry button
        self.update_latin_reset_retry_button()
    
    def reset_latin_table(self):
        """Reset the Latin table."""
        # Reset tracking variables first
        self.latin_has_revealed = False
        self.latin_incorrect_entries.clear()
        
        # Re-enable reveal button
        self.latin_reveal_button.configure(state='normal')
        
        # Reset all entries to normal state
        for entry in self.latin_entries.values():
            entry.configure(state='normal', bg='white')
            entry.delete(0, tk.END)
        
        # If prefill stems is enabled, reapply stems
        if self.config.prefill_stems.get():
            self.apply_latin_prefill_stems()
        
        # Update Reset/Retry button
        self.update_latin_reset_retry_button()
    
    def retry_latin_incorrect_answers(self):
        """Clear only the incorrect/missing answers for retry, keeping correct ones locked."""
        if not self.latin_has_revealed:
            return  # Should not happen since button is disabled before reveal

        # Get paradigm info for stem preservation
        paradigm = self.get_current_paradigm()
        prefill_enabled = self.config.prefill_stems.get()

        # Clear only the incorrect entries
        for entry_key in self.latin_incorrect_entries:
            if entry_key in self.latin_entries:
                entry = self.latin_entries[entry_key]
                entry.configure(state='normal')
                entry.configure(bg='white')  # Reset to normal background

                # If prefill is enabled, preserve the stem
                if prefill_enabled and paradigm:
                    if paradigm.get('type') == 'noun':
                        stem = paradigm.get('stem', '')
                        stem_nom_sg = paradigm.get('stem_nom_sg', stem)

                        # Parse entry_key to determine if it's nominative singular
                        if entry_key == "Nominative_sg":
                            entry.delete(0, tk.END)
                            entry.insert(0, stem_nom_sg)
                        else:
                            entry.delete(0, tk.END)
                            entry.insert(0, stem)

                    elif paradigm.get('type') == 'verb':
                        pp = paradigm.get('principal_parts', {})
                        tense = paradigm.get('tense')
                        voice = paradigm.get('voice')

                        stem = ''
                        if tense in ['present', 'imperfect', 'future']:
                            stem = pp.get('present_stem', '')
                        elif tense in ['perfect', 'pluperfect', 'future perfect']:
                            if voice == 'active':
                                stem = pp.get('perfect_stem', '')
                            else:
                                stem = pp.get('perfect_passive_stem', '')

                        entry.delete(0, tk.END)
                        entry.insert(0, stem)
                else:
                    # Full clear if prefill is disabled
                    entry.delete(0, tk.END)

        # After clearing, re-apply prefill stems if enabled (robust, like Greek)
        if prefill_enabled:
            self.apply_latin_prefill_stems()

        # Reset tracking
        self.latin_has_revealed = False

        # Re-enable the reveal button
        self.latin_reveal_button.configure(state='normal')

        # Update Reset/Retry button
        self.update_latin_reset_retry_button()
    
    def smart_latin_reset_retry(self):
        """Smart button that acts as Reset before reveal, Retry after reveal."""
        if self.latin_has_revealed and self.latin_incorrect_entries:
            # After reveal with incorrect entries - act as Retry
            self.retry_latin_incorrect_answers()
        else:
            # Before reveal or no incorrect entries - act as Reset
            self.reset_latin_table()
    
    def update_latin_reset_retry_button(self):
        """Update the Latin Reset/Retry button text and state based on current context."""
        if not hasattr(self, 'latin_reset_retry_button'):
            return
            
        if self.latin_has_revealed and self.latin_incorrect_entries:
            # After reveal with incorrect entries - show as Retry
            self.latin_reset_retry_button.configure(text="Retry", state='normal')
        else:
            # Before reveal or no incorrect entries - show as Reset
            self.latin_reset_retry_button.configure(text="Reset", state='normal')
    
    def next_latin_word(self):
        """Navigate to the next Latin word/verb combination in the dropdown list."""
        current_type = self.latin_type_var.get()
        
        # Special handling for Starred mode - just go to next starred item
        if current_type == "Starred":
            self.next_latin_starred_item()
            return
        
        # Check if randomize is enabled - use full random logic
        if self.config.randomize_next.get():
            self.random_latin_next()
            return
        
        # Check if we're dealing with a verb
        current_word = self.latin_word_var.get().split(' (')[0]
        
        # Find if current word is a verb
        is_verb = False
        for key, data in self.latin_paradigms.items():
            if data.get('lemma') == current_word and data.get('type') == 'verb':
                is_verb = True
                break
        
        if is_verb:
            # For verbs, cycle through tense → voice → mood → next verb
            self.next_latin_verb_combination()
        else:
            # For nouns, just go to next word
            self.next_latin_noun()
    
    def next_latin_starred_item(self):
        """Navigate to the next starred Latin item in the list."""
        current_values = list(self.latin_word_dropdown['values'])
        if not current_values:
            return
        
        current_word = self.latin_word_var.get()
        
        try:
            current_index = current_values.index(current_word)
            next_index = (current_index + 1) % len(current_values)
            self.latin_word_var.set(current_values[next_index])
            self.on_latin_word_change(None)
        except ValueError:
            # Current word not in list, just select first
            self.latin_word_var.set(current_values[0])
            self.on_latin_word_change(None)

    
    def random_latin_next(self):
        """Navigate to a completely random table (type, word, and for verbs: voice/tense/mood)."""
        import random
        
        # Check if type is locked
        current_type = self.latin_type_var.get()
        
        # Special handling for Starred mode - randomize within starred items
        if current_type == "Starred":
            current_values = list(self.latin_word_dropdown['values'])
            if current_values:
                random_word = random.choice(current_values)
                self.latin_word_var.set(random_word)
                self.on_latin_word_change(None)
            return
        
        if self.config.lock_current_type.get():
            # Keep current type, only randomize within that type
            random_type = current_type
        else:
            # Randomly select a type
            available_types = ["Noun", "Verb"]
            random_type = random.choice(available_types)
        
        # Set the type (only changes if not locked)
        if not self.config.lock_current_type.get():
            self.latin_type_var.set(random_type)
            self.on_latin_type_change(None)  # Update the available words
        
        # Randomly select a word from the available words for this type
        current_values = list(self.latin_word_dropdown['values'])
        if current_values:
            random_word = random.choice(current_values)
            self.latin_word_var.set(random_word)
            self.on_latin_word_change(None)
        
        # If it's a verb, also randomize tense, voice, and mood
        if random_type == "Verb":
            # Get available combinations for this verb
            current_lemma = self.latin_word_var.get().split(' (')[0]
            
            available_combinations = []
            for key, data in self.latin_paradigms.items():
                if data.get('lemma') == current_lemma and data.get('type') == 'verb':
                    tense = data.get('tense')
                    voice = data.get('voice')
                    mood = data.get('mood')
                    if tense and voice and mood:
                        available_combinations.append((tense, voice, mood))
            
            if available_combinations:
                # Randomly select a combination
                random_combo = random.choice(available_combinations)
                tense, voice, mood = random_combo
                
                # Set the random combination
                self.latin_tense_var.set(tense)
                self.latin_voice_var.set(voice)
                self.latin_mood_var.set(mood)
                self.on_latin_verb_change(None)
    
    def next_latin_noun(self):
        """Navigate to the next noun in the dropdown list."""
        # Normal sequential next
        current_word = self.latin_word_var.get()
        current_values = list(self.latin_word_dropdown['values'])
        
        if not current_values:
            return
        
        try:
            current_index = current_values.index(current_word)
            next_index = (current_index + 1) % len(current_values)
            next_word = current_values[next_index]
            
            self.latin_word_var.set(next_word)
            self.on_latin_word_change(None)
        except ValueError:
            if current_values:
                self.latin_word_var.set(current_values[0])
                self.on_latin_word_change(None)
    
    def next_latin_verb_combination(self):
        """Navigate through verb combinations: tense → voice → mood → next verb."""
        current_lemma = self.latin_word_var.get().split(' (')[0]
        current_tense = self.latin_tense_var.get()
        current_voice = self.latin_voice_var.get()
        current_mood = self.latin_mood_var.get()
        
        # Define ordering
        tense_order = ["present", "imperfect", "future", "perfect", "pluperfect", "future perfect"]
        voice_order = ["active", "passive"]
        mood_order = ["indicative", "subjunctive", "imperative"]
        
        # Get all available combinations for current verb
        available_combinations = []
        for key, data in self.latin_paradigms.items():
            if data.get('lemma') == current_lemma and data.get('type') == 'verb':
                tense = data.get('tense')
                voice = data.get('voice')
                mood = data.get('mood')
                if tense and voice and mood:
                    available_combinations.append((tense, voice, mood))
        
        if not available_combinations:
            return
        
        # Step 1: Try to advance tense within current voice/mood
        current_combinations = [(t, v, m) for t, v, m in available_combinations 
                               if v == current_voice and m == current_mood]
        available_tenses = sorted(list(set([t for t, v, m in current_combinations])),
                                key=lambda x: tense_order.index(x) if x in tense_order else 999)
        
        if current_tense in available_tenses:
            current_tense_index = available_tenses.index(current_tense)
            if current_tense_index < len(available_tenses) - 1:
                # Move to next tense
                next_tense = available_tenses[current_tense_index + 1]
                self.latin_tense_var.set(next_tense)
                self.on_latin_verb_change(None)
                return
        
        # Step 2: Tense wrapped, try to advance voice within current mood
        current_mood_combinations = [(t, v, m) for t, v, m in available_combinations if m == current_mood]
        available_voices = sorted(list(set([v for t, v, m in current_mood_combinations])),
                                key=lambda x: voice_order.index(x) if x in voice_order else 999)
        
        if current_voice in available_voices:
            current_voice_index = available_voices.index(current_voice)
            if current_voice_index < len(available_voices) - 1:
                # Move to next voice, reset tense to first available
                next_voice = available_voices[current_voice_index + 1]
                
                # Get first tense for this voice/mood combination
                next_combinations = [(t, v, m) for t, v, m in available_combinations 
                                   if v == next_voice and m == current_mood]
                next_tenses = sorted(list(set([t for t, v, m in next_combinations])),
                                   key=lambda x: tense_order.index(x) if x in tense_order else 999)
                
                if next_tenses:
                    self.latin_voice_var.set(next_voice)
                    self.latin_tense_var.set(next_tenses[0])
                    self.on_latin_verb_change(None)
                    return
        
        # Step 3: Voice wrapped, try to advance mood
        available_moods = sorted(list(set([m for t, v, m in available_combinations])),
                               key=lambda x: mood_order.index(x) if x in mood_order else 999)
        
        if current_mood in available_moods:
            current_mood_index = available_moods.index(current_mood)
            if current_mood_index < len(available_moods) - 1:
                # Move to next mood, reset voice and tense to first available
                next_mood = available_moods[current_mood_index + 1]
                
                # Get first voice for this mood
                next_mood_combinations = [(t, v, m) for t, v, m in available_combinations if m == next_mood]
                next_voices = sorted(list(set([v for t, v, m in next_mood_combinations])),
                                   key=lambda x: voice_order.index(x) if x in voice_order else 999)
                
                if next_voices:
                    next_voice = next_voices[0]
                    # Get first tense for this mood/voice
                    next_combinations = [(t, v, m) for t, v, m in available_combinations 
                                       if m == next_mood and v == next_voice]
                    next_tenses = sorted(list(set([t for t, v, m in next_combinations])),
                                       key=lambda x: tense_order.index(x) if x in tense_order else 999)
                    
                    if next_tenses:
                        self.latin_mood_var.set(next_mood)
                        self.latin_voice_var.set(next_voice)
                        self.latin_tense_var.set(next_tenses[0])
                        self.on_latin_verb_change(None)
                        return
        
        # Step 4: Everything wrapped, move to next verb
        self.next_latin_noun()  # This will cycle to next verb in the list
        
        # Reset to first available combination for new verb
        new_lemma = self.latin_word_var.get().split(' (')[0]
        new_combinations = []
        for key, data in self.latin_paradigms.items():
            if data.get('lemma') == new_lemma and data.get('type') == 'verb':
                tense = data.get('tense')
                voice = data.get('voice')
                mood = data.get('mood')
                if tense and voice and mood:
                    new_combinations.append((tense, voice, mood))
        
        if new_combinations:
            # Sort to get indicative/active/present first
            new_combinations.sort(key=lambda x: (
                mood_order.index(x[2]) if x[2] in mood_order else 999,
                voice_order.index(x[1]) if x[1] in voice_order else 999,
                tense_order.index(x[0]) if x[0] in tense_order else 999
            ))
            first_combo = new_combinations[0]
            self.latin_tense_var.set(first_combo[0])
            self.latin_voice_var.set(first_combo[1])
            self.latin_mood_var.set(first_combo[2])
            self.on_latin_verb_change(None)
    
    def check_latin_single_entry(self, entry_key):
        """Check a single Latin entry when Enter is pressed."""
        if entry_key not in self.latin_entries:
            return
        
        entry = self.latin_entries[entry_key]
        user_answer = entry.get().strip()
        
        if not user_answer:
            return
        
        # Get correct answer
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        
        # Find paradigm - could be noun, adjective, or verb
        paradigm = None
        for key, data in self.latin_paradigms.items():
            if data.get('type') == 'noun' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'adjective' and data.get('word') == word:
                paradigm = data
                break
            elif data.get('type') == 'verb' and data.get('lemma') == word:
                # For verbs, also match tense/voice/mood
                if (data.get('tense') == self.latin_tense_var.get() and
                    data.get('voice') == self.latin_voice_var.get() and
                    data.get('mood') == self.latin_mood_var.get()):
                    paradigm = data
                    break
        
        if not paradigm:
            return
        
        # Get correct answer based on type
        correct_answer = None
        
        if paradigm.get('type') == 'adjective':
            # Parse entry key: "case_gender_number" (e.g., "nominative_masculine_sg")
            parts = entry_key.split('_')
            if len(parts) == 3:
                case, gender, number = parts
                correct_answer = paradigm['forms'][gender][case][number]
        elif paradigm.get('type') == 'noun':
            # Parse entry key: "case_number" (e.g., "Nominative_sg")
            parts = entry_key.split('_')
            if len(parts) == 2:
                identifier, number = parts
                correct_answer = paradigm['forms'][identifier.lower()][number]
        else:  # verb
            # entry_key is like "1st_sg" or "2nd_pl"
            correct_answer = paradigm.get(entry_key, '')
        
        if correct_answer is None:
            return
        
        is_correct = user_answer.lower() == correct_answer.lower()
        
        if is_correct:
            entry.configure(state='readonly', readonlybackground='#B8860B')  # Dark goldenrod
            
            # Check if all entries are now readonly and auto-advance is enabled
            auto_advance_enabled = False
            if hasattr(self, 'config') and hasattr(self.config, 'auto_advance'):
                auto_advance_enabled = self.config.auto_advance.get()
            
            all_correct = all(str(e.cget('state')) == 'readonly' for e in self.latin_entries.values())
            
            if all_correct and auto_advance_enabled:
                # Auto-advance to next table
                self.next_latin_word()
                # Focus on first Latin entry after table loads
                self.root.after(50, self.focus_first_latin_entry)
            else:
                # Move to next entry
                self.move_to_next_latin_entry(entry_key)
        else:
            entry.configure(bg='#FFB6C6')  # Light red
    
    def move_to_next_latin_entry(self, current_key):
        """Move focus to the next logical Latin entry."""
        # Parse current key
        parts = current_key.split('_')
        
        # Check if it's an adjective (3 parts: case_gender_number)
        if len(parts) == 3:
            case, gender, number = parts
            cases = ["nominative", "vocative", "accusative", "genitive", "dative", "ablative"]
            genders = ["masculine", "feminine", "neuter"]
            numbers = ["sg", "pl"]
            
            try:
                case_idx = cases.index(case)
                gender_idx = genders.index(gender)
                number_idx = numbers.index(number)
            except ValueError:
                return
            
            # Navigation order: move right (sg->pl), then down (next case), then to next gender column
            # Current order in table: masculine_sg, masculine_pl, feminine_sg, feminine_pl, neuter_sg, neuter_pl
            
            # Try moving to plural in same case and gender
            if number == "sg":
                next_key = f"{case}_{gender}_pl"
                if next_key in self.latin_entries:
                    next_entry = self.latin_entries[next_key]
                    if str(next_entry.cget('state')) != 'readonly':
                        next_entry.focus()
                        return
            
            # Move to next gender's singular
            if number == "pl" and gender_idx < len(genders) - 1:
                next_gender = genders[gender_idx + 1]
                next_key = f"{case}_{next_gender}_sg"
                if next_key in self.latin_entries:
                    next_entry = self.latin_entries[next_key]
                    if str(next_entry.cget('state')) != 'readonly':
                        next_entry.focus()
                        return
            
            # Move to next case, first gender, singular
            if case_idx < len(cases) - 1:
                next_case = cases[case_idx + 1]
                next_key = f"{next_case}_masculine_sg"
                if next_key in self.latin_entries:
                    next_entry = self.latin_entries[next_key]
                    if str(next_entry.cget('state')) != 'readonly':
                        next_entry.focus()
                        return
            
            return
        
        # Original logic for nouns (2 parts) and verbs
        if len(parts) != 2:
            return
        
        identifier, number = parts
        
        # Check if we're dealing with nouns (cases) or verbs (persons)
        cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative", "Ablative"]
        persons = ["1st", "2nd", "3rd"]
        
        if identifier in cases:
            # Noun logic
            case_idx = cases.index(identifier)
            
            # Try next case in same number column first (downward movement)
            if case_idx < len(cases) - 1:
                for i in range(case_idx + 1, len(cases)):
                    next_key = f"{cases[i]}_{number}"
                    if next_key in self.latin_entries:
                        next_entry = self.latin_entries[next_key]
                        # Only move if entry is not already marked correct (readonly)
                        if str(next_entry.cget('state')) != 'readonly':
                            next_entry.focus()
                            return
            
            # If we've finished all cases in sg column, move to pl column
            if number == "sg":
                for i in range(len(cases)):
                    next_key = f"{cases[i]}_pl"
                    if next_key in self.latin_entries:
                        next_entry = self.latin_entries[next_key]
                        if str(next_entry.cget('state')) != 'readonly':
                            next_entry.focus()
                            return
        
        elif identifier in persons:
            # Verb logic
            person_idx = persons.index(identifier)
            
            # Try next person in same number column first (downward movement)
            if person_idx < len(persons) - 1:
                for i in range(person_idx + 1, len(persons)):
                    next_key = f"{persons[i]}_{number}"
                    if next_key in self.latin_entries:
                        next_entry = self.latin_entries[next_key]
                        # Only move if entry is not already marked correct (readonly)
                        if str(next_entry.cget('state')) != 'readonly':
                            next_entry.focus()
                            return
            
            # If we've finished all persons in sg column, move to pl column
            if number == "sg":
                for i in range(len(persons)):
                    next_key = f"{persons[i]}_pl"
                    if next_key in self.latin_entries:
                        next_entry = self.latin_entries[next_key]
                        if str(next_entry.cget('state')) != 'readonly':
                            next_entry.focus()
                            return
    
    def show_tables_view(self):
        """Show the main tables interface."""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Configure main_frame rows to expand properly
        self.main_frame.grid_rowconfigure(0, weight=0)  # Title - fixed
        self.main_frame.grid_rowconfigure(1, weight=0)  # Type selector - fixed
        self.main_frame.grid_rowconfigure(2, weight=0)  # Mode selector - fixed
        self.main_frame.grid_rowconfigure(3, weight=1)  # Table area - expands
        self.main_frame.grid_rowconfigure(4, weight=0)  # Buttons - fixed
        for i in range(3):
            self.main_frame.grid_columnconfigure(i, weight=1)  # Center everything horizontally

        # Title and Instructions
        title_frame = tk.Frame(self.main_frame, bg='#F8F6F1')
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        title_frame.grid_columnconfigure(0, weight=1)  # Allow title to expand
        title_frame.grid_columnconfigure(1, weight=0)  # Practice options column
        title_frame.grid_columnconfigure(2, weight=0)  # Latin button column
        title_frame.grid_columnconfigure(3, weight=0)  # Help button column
        
        # Logo or title
        if self.header_logo:
            # Use header logo (long logo) - make it clickable
            logo_label = tk.Label(title_frame, image=self.header_logo, bg='#F8F6F1', cursor='hand2')
            logo_label.grid(row=0, column=0, sticky='w')
            # Keep a reference to prevent garbage collection
            logo_label.image = self.header_logo
            # Bind click event to return to startup page
            logo_label.bind('<Button-1>', lambda e: self.show_startup_page())
        else:
            # Fallback to text title - also make it clickable
            title_label = tk.Label(
                title_frame, 
                text="Bellerophon Grammar Study",
                bg='#F8F6F1',
                fg='#2C2C2C',  # Obsidian Ink
                font=('Arial', 24, 'bold'),
                cursor='hand2'
            )
            title_label.grid(row=0, column=0, sticky='w')
            # Bind click event to return to startup page
            title_label.bind('<Button-1>', lambda e: self.show_startup_page())
            
        # Practice options in top corner (simplified)
        practice_options_frame = tk.Frame(title_frame, bg='#F8F6F1')
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
            variable=self.config.randomize_next,
            command=self.on_randomize_toggle
        )
        randomize_next_cb.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        # Auto advance checkbox
        auto_advance_cb = ttk.Checkbutton(
            practice_options_frame,
            text="Auto advance",
            variable=self.config.auto_advance
        )
        auto_advance_cb.grid(row=0, column=2, sticky='e', padx=(10, 0))
        
        # Latin button in top right corner
        latin_button = ttk.Button(
            title_frame,
            text="Latin",
            command=self.show_latin_view,
            width=8
        )
        latin_button.grid(row=0, column=2, sticky='ne', padx=(0, 5))
        
        # Help button in top right corner
        help_button = ttk.Button(
            title_frame,
            text="Help",
            command=self.show_help,
            width=8
        )
        help_button.grid(row=0, column=3, sticky='ne')

        # Initialize verb navigation state for complex verb navigation
        self.verb_voice_order = ["Active", "Middle", "Passive"]
        self.verb_tense_order = ["Present", "Imperfect", "Future", "Aorist", "Perfect", "Pluperfect"] 
        self.verb_mood_order = ["Indicative", "Subjunctive", "Optative", "Imperative"]

        # Create the mode selection frame
        mode_frame = tk.Frame(self.main_frame, bg='#F8F6F1')
        mode_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky='ew')
        mode_frame.columnconfigure(1, weight=0, minsize=250)  # Type dropdown column - fixed width with minimum size
        mode_frame.columnconfigure(2, weight=0, minsize=100)  # Label column - fixed width with minimum size
        mode_frame.columnconfigure(3, weight=1)  # Dropdown column - expandable

        # Add type selector (Noun vs Adjective)
        ttk.Label(mode_frame, text="Type:").grid(
            row=0, column=0, padx=(0, 10)
        )
        
        self.type_var = tk.StringVar(value="Noun")
        self.type_dropdown = ttk.Combobox(
            mode_frame,
            textvariable=self.type_var,
            values=self.get_available_types(),
            font=('Times New Roman', 12),
            width=12,
            state='readonly'
        )
        self.type_dropdown.grid(row=0, column=1, sticky='w', padx=(0, 0))
        self.type_dropdown.bind('<<ComboboxSelected>>', self.on_type_change)
        
        # Lock current type checkbox (only visible when randomize is enabled)
        self.lock_type_cb = ttk.Checkbutton(
            mode_frame,
            text="Lock current type",
            variable=self.config.lock_current_type
        )
        self.lock_type_cb.grid(row=0, column=1, sticky='w', padx=(120, 0))
        self.lock_type_cb.grid_remove()  # Hidden by default

        ttk.Label(mode_frame, text="Select word:").grid(
            row=0, column=2, sticky='w', padx=(20, 0)
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
        
        # Load pronoun modes dynamically from JSON
        self.pronoun_modes = self.load_pronoun_modes_from_json()
        
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
            width=46
        )
        self.mode_dropdown.grid(row=0, column=3, sticky='w', padx=(0, 0))
        self.mode_dropdown.state(['readonly'])
        self.mode_dropdown.bind('<<ComboboxSelected>>', self.on_mode_change)

        # Word display frame
        word_frame = tk.Frame(self.main_frame, bg='#F8F6F1')
        word_frame.grid(row=2, column=0, columnspan=3, pady=(10, 20))
        
        self.instruction_label = tk.Label(
            word_frame,
            text="Decline the word:",
            bg='#F8F6F1',
            fg='#2C2C2C',  # Obsidian Ink
            font=('Arial', 12, 'bold')
        )
        self.instruction_label.grid(row=0, column=0, padx=(0, 10))
        
        self.word_label = tk.Label(
            word_frame,
            text="—",
            bg='#F8F6F1',
            fg='#2C2C2C',  # Obsidian Ink
            font=('Times New Roman', 16, 'bold')
        )
        self.word_label.grid(row=0, column=1)

        # Star button for favoriting tables
        self.star_button = tk.Button(
            word_frame,
            text="☆",
            font=('Arial', 16),
            foreground="black",
            background='#F8F6F1',  # Match background
            activeforeground="gold",
            activebackground="#f0f0f0",
            relief="flat",
            borderwidth=0,
            command=self.toggle_star,
            cursor="hand2"
        )
        
        # Add hover effects to star button
        self.star_button.bind("<Enter>", self.on_star_hover_enter)
        self.star_button.bind("<Leave>", self.on_star_hover_leave)
        
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
    
    def on_randomize_toggle(self):
        """Handle randomize next toggle - show/hide lock type checkbox"""
        if self.config.randomize_next.get():
            # Show lock type checkbox when randomize is enabled
            if hasattr(self, 'lock_type_cb'):
                try:
                    self.lock_type_cb.grid()
                except tk.TclError:
                    pass  # Widget may not be visible/active
            if hasattr(self, 'latin_lock_type_cb'):
                try:
                    self.latin_lock_type_cb.grid()
                except tk.TclError:
                    pass  # Widget may not be visible/active
        else:
            # Hide lock type checkbox when randomize is disabled
            if hasattr(self, 'lock_type_cb'):
                try:
                    self.lock_type_cb.grid_remove()
                except tk.TclError:
                    pass  # Widget may not be visible/active
            if hasattr(self, 'latin_lock_type_cb'):
                try:
                    self.latin_lock_type_cb.grid_remove()
                except tk.TclError:
                    pass  # Widget may not be visible/active
            # Also uncheck it when hiding
            self.config.lock_current_type.set(False)

    def update_word_display(self):
        """Update the word display by extracting the word from the mode name."""
        mode = self.mode_var.get()
        # Use effective type so "Starred" items map back to their original type
        current_type = self.get_effective_type()
        
        # Check if we're in Starred tab (raw type check, not effective type)
        is_starred = self.type_var.get() == "Starred"

        # Handle starred items with robust verb extraction
        if is_starred:
            verb_names = ["λύω", "εἰμί", "φιλέω", "τιμάω", "δηλόω", "βάλλω", "βαίνω", "δίδωμι", "τίθημι", "ἵστημι", "οἶδα", "εἶμι", "φημί", "ἵημι"]
            found_verb = None
            for v in verb_names:
                if v in mode:
                    found_verb = v
                    break
            if found_verb:
                word = found_verb
                self.word_label.config(text=word)
                # Use the centralized instruction update so wording is consistent
                self.update_instruction_text()
                self.update_star_button()
                return
            # Not a verb, fallback to noun/adjective/pronoun logic
            if "(" in mode and ")" in mode:
                parentheses_content = mode.split("(")[1].split(")")[0]
                if ", " in parentheses_content:
                    word = parentheses_content.split(", ")[0]
                else:
                    word = parentheses_content
            elif " - " in mode:
                word = mode.split(" - ")[0]
            else:
                word = mode
        else:
            # Extract the word from the mode name (usually in parentheses)
            if "(" in mode and ")" in mode:
                # Extract text within parentheses - handle multiple words
                parentheses_content = mode.split("(")[1].split(")")[0]
                if ", " in parentheses_content:
                    word = parentheses_content.split(", ")[0]
                else:
                    word = parentheses_content
            else:
                # Fallback for modes without parentheses
                word = "—"

        # Update the word label and instruction text
        if hasattr(self, 'word_label') and self.word_label.winfo_exists():
            self.word_label.config(text=word)
        self.update_instruction_text()

        # Update star button state
        self.update_star_button()

    def save_current_state(self, force=False):
        """Save the current table state to history."""
        current_type = self.get_effective_type()
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
            return

        # If this state is different from the current one
        if current_state != self.table_history[self.current_history_index]:
            # If we're not at the end of the history, truncate the forward history
            if self.current_history_index < len(self.table_history) - 1:
                self.table_history = self.table_history[:self.current_history_index + 1]
            
            # Add the new state
            self.table_history.append(current_state)
            self.current_history_index = len(self.table_history) - 1

    def next_answer(self):
        """Navigate to the next item in the current dropdown list."""
        # Check if randomize next is enabled
        if self.config.randomize_next.get():
            self.random_next()
            return

        # Save current state before navigation with force=True to ensure it's saved
        self.save_current_state(force=True)

        # Check raw type_var first - if we're in Starred tab, navigate within starred items
        # even if the effective type is Verb
        raw_type = self.type_var.get()
        current_mode = self.mode_var.get()

        if raw_type == "Starred":
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
                pass
        elif self.get_effective_type() == "Verb":
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
                pass

    def get_current_word_identifier(self):
        """Get a unique identifier for the current word state."""
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
        
        if current_type == "Verb":
            # For verbs, include tense, mood, and voice
            return f"{current_type}:{current_mode}:{self.tense_var.get()}:{self.mood_var.get()}:{self.voice_var.get()}"
        else:
            # For nouns, adjectives, pronouns, and starred items
            return f"{current_type}:{current_mode}"
    
    def random_next(self):
        """Navigate to a completely random table (type, mode, and for verbs: voice/tense/mood)."""
        import random
        
        # Save current state before random navigation
        self.save_current_state()
        # Resolve starred items back to their original type
        current_type = self.get_effective_type()

        if current_type == "Starred":
            # If we're in starred mode, randomize within starred items only
            available_modes = self.modes
            if available_modes and available_modes != ["No starred items"]:
                # Filter out recently seen words
                max_history_size = min(len(available_modes) - 1, 10) if len(available_modes) > 1 else 0
                filtered_modes = [mode for mode in available_modes 
                                 if f"Starred:{mode}" not in list(self.recent_word_history)[:max_history_size]]
                
                # If all modes are in history (unlikely but possible), use all modes
                if not filtered_modes:
                    filtered_modes = available_modes
                
                random_mode = random.choice(filtered_modes)
                self.mode_var.set(random_mode)
                self.on_mode_change(None)
                # Add to history
                self.recent_word_history.append(f"Starred:{random_mode}")
            return
        
        # Check if type is locked
        if self.config.lock_current_type.get():
            # Keep current type, only randomize within that type
            random_type = current_type
        else:
            # For non-locked types, use normal random logic
            # Randomly select a type
            available_types = ["Noun", "Adjective", "Pronoun", "Verb"]
            random_type = random.choice(available_types)
        
        # Set the type (only changes if not locked)
        if not self.config.lock_current_type.get():
            self.type_var.set(random_type)
            self.on_type_change(None)  # Update the available modes
        
        # Randomly select a mode from the available modes for this type
        available_modes = self.modes
        if available_modes:
            # For non-verb types, filter out recently seen words
            if random_type != "Verb":
                max_history_size = min(len(available_modes) - 1, 10) if len(available_modes) > 1 else 0
                filtered_modes = [mode for mode in available_modes 
                                 if f"{random_type}:{mode}" not in list(self.recent_word_history)[:max_history_size]]
                
                # If all modes are in history, use all modes
                if not filtered_modes:
                    filtered_modes = available_modes
                    
                random_mode = random.choice(filtered_modes)
                # Add to history for non-verb types
                self.recent_word_history.append(f"{random_type}:{random_mode}")
            else:
                # For verbs, we'll filter after getting combinations
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
                    # Filter out recently seen verb combinations
                    max_history_size = min(len(available_combinations) - 1, 10) if len(available_combinations) > 1 else 0
                    filtered_combinations = [combo for combo in available_combinations
                                           if f"Verb:{random_mode}:{combo[0]}:{combo[1]}:{combo[2]}" 
                                           not in list(self.recent_word_history)[:max_history_size]]
                    
                    # If all combinations are in history, use all combinations
                    if not filtered_combinations:
                        filtered_combinations = available_combinations
                    
                    # Randomly select a combination
                    random_combo = random.choice(filtered_combinations)
                    tense, mood, voice = random_combo
                    
                    # Set the random combination
                    self.tense_var.set(tense)
                    self.mood_var.set(mood)
                    self.voice_var.set(voice)
                    self.update_tense_mood_constraints()
                    # Recreate the table to handle infinitive vs finite verb layouts
                    self.reset_table()
                    
                    # Add to history for verbs (including tense/mood/voice)
                    self.recent_word_history.append(f"Verb:{random_mode}:{tense}:{mood}:{voice}")
        
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
                                self.reset_table()
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
                        self.reset_table()
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
                            self.reset_table()
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
                    self.reset_table()
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
            pass

    def get_table_signature(self):
        """Get a signature representing the current table structure to avoid unnecessary rebuilds."""
        current_type = self.get_effective_type()
        current_mode = self.mode_var.get()
        
        # Create a signature that uniquely identifies the table structure
        signature = {
            'type': current_type,
            'mode': current_mode  # Include mode to be more conservative
        }
        
        # For now, let's be very conservative and only optimize for identical modes
        # This prevents issues while still reducing some flashing
        return signature

    def update_noun_table_content(self):
        """Update noun table content without rebuilding the structure."""
        # Clear all existing entries and reset their state
        for entry in self.entries.values():
            if entry and entry.winfo_exists():
                entry.delete(0, tk.END)
                entry.configure(bg='white')  # Reset background color
        
        # Clear and hide all error labels
        for error_label in self.error_labels.values():
            if error_label and error_label.winfo_exists():
                error_label.config(text="")
                error_label.grid_remove()  # Hide the error label
        
        # Clear incorrect entries tracking
        if hasattr(self, 'incorrect_entries'):
            self.incorrect_entries.clear()
        
        # Update word display for the new paradigm
        self.update_word_display()
        
        # Apply stem prefilling if enabled
        self.apply_prefill_stems_to_all_entries()

    def update_pronoun_table_content(self):
        """Update pronoun table content without rebuilding the structure."""
        # Clear all existing entries and reset their state
        for entry in self.entries.values():
            if entry and entry.winfo_exists():
                entry.delete(0, tk.END)
                entry.configure(bg='white')  # Reset background color
        
        # Clear and hide all error labels
        for error_label in self.error_labels.values():
            if error_label and error_label.winfo_exists():
                error_label.config(text="")
                error_label.grid_remove()  # Hide the error label
        
        # Clear incorrect entries tracking
        if hasattr(self, 'incorrect_entries'):
            self.incorrect_entries.clear()
        
        # Update word display for the new paradigm
        self.update_word_display()
        
        # Apply stem prefilling if enabled
        self.apply_prefill_stems_to_all_entries()

    def should_rebuild_table(self):
        """Check if we need to rebuild the table or can just clear entries."""
        new_signature = self.get_table_signature()
        
        # If no previous signature, we need to build
        if not hasattr(self, '_last_table_signature'):
            self._last_table_signature = new_signature
            return True
            
        # If signatures match, we can just clear entries
        if self._last_table_signature == new_signature:
            return False
            
        # Signatures differ, need to rebuild
        self._last_table_signature = new_signature
        return True
    
    def clear_table_entries(self):
        """Clear all entry values without rebuilding the table structure."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return
            
        current_type = self.get_effective_type()
        
        # We need to rebuild the table content (entries) but not the structure
        # Clear existing table content but keep the frame
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        # Recreate the table content with the new paradigm
        if current_type == "Adjective":
            self.create_adjective_table(current_paradigm)
        elif current_type == "Pronoun":
            self.create_pronoun_table(current_paradigm)
        elif current_type == "Verb":
            self.create_verb_table(current_paradigm)
        else:
            self.create_noun_table(current_paradigm)
        
        # Apply stem prefilling if enabled
        self.apply_prefill_stems_to_all_entries()

    def create_declension_table(self):
        """Create the declension table with input fields for each case."""
        current_type = self.get_effective_type()
        
        # Optimize for nouns: all nouns use the same table structure (Case x Singular/Plural)
        # Don't use optimization in starred context or if entries are empty
        if (current_type == "Noun" and 
            hasattr(self, 'table_frame') and self.table_frame and 
            hasattr(self, '_last_table_type') and self._last_table_type == "Noun" and
            len(self.entries) > 0 and
            not getattr(self, '_in_starred_context', False) and
            self.table_frame.winfo_exists()):
            
            # Same table structure, just update the content
            self.update_noun_table_content()
            return
        
        # Optimize for pronouns: pronouns of the same subtype use consistent structure
        # Check if pronoun subtype hasn't changed (Personal vs Gender)
        if (current_type == "Pronoun" and 
            hasattr(self, 'table_frame') and self.table_frame and 
            hasattr(self, '_last_table_type') and self._last_table_type == "Pronoun" and
            hasattr(self, '_last_pronoun_subtype') and
            len(self.entries) > 0 and
            not getattr(self, '_in_starred_context', False) and
            self.table_frame.winfo_exists()):
            
            # Check if pronoun subtype is the same
            mode = self.mode_var.get()
            current_subtype = "Personal" if ("Personal I" in mode or "Personal You" in mode) else "Gender"
            
            if self._last_pronoun_subtype == current_subtype:
                # Same table structure, just update the content
                self.update_pronoun_table_content()
                return
        
        # Store the current table type for future optimization
        self._last_table_type = current_type
        
        # Store pronoun subtype if applicable
        if current_type == "Pronoun":
            mode = self.mode_var.get()
            self._last_pronoun_subtype = "Personal" if ("Personal I" in mode or "Personal You" in mode) else "Gender"
            
        # Need to rebuild the table
        if self.table_frame:
            self.table_frame.destroy()
        
        # Clear the entries and error_labels dictionaries when rebuilding
        self.entries.clear()
        self.error_labels.clear()
            
        # Create a container frame that can expand and center content
        # Table can now use full space since buttons are floating
        table_container = tk.Frame(self.main_frame, bg='#F8F6F1')
        table_container.grid(row=3, column=0, columnspan=3, rowspan=2, sticky='nsew')
        table_container.grid_columnconfigure(0, weight=1)  # Left padding
        table_container.grid_columnconfigure(1, weight=0)  # Table content
        table_container.grid_columnconfigure(2, weight=1)  # Right padding
        table_container.grid_rowconfigure(0, weight=1)
        
        # Create the table frame in the center column - add bottom padding for floating buttons
        self.table_frame = tk.Frame(table_container, bg='#F8F6F1')
        self.table_frame.grid(row=0, column=1, sticky='nsew', padx=20, pady=(0, 80))
        
        # Configure grid weights for responsive design
        for i in range(10):  # Allow for up to 10 columns (adjectives can have 6+ columns)
            self.table_frame.grid_columnconfigure(i, weight=1)
        
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
        
        # Bottom button frame positioned as overlay to allow table to extend underneath
        bottom_button_frame = ttk.Frame(self.main_frame)
        # Use place instead of grid to create floating buttons that don't constrain table space
        bottom_button_frame.place(relx=0.0, rely=1.0, anchor='sw', relwidth=1.0)
        
        # Container frame for buttons to allow centering
        button_container = ttk.Frame(bottom_button_frame)
        button_container.grid(row=0, column=1, pady=10)
        
        # Configure the bottom frame for centering floating buttons
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
            text="Case",
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
            # Create a frame to hold both entry and error label
            entry_frame_sg = tk.Frame(self.table_frame)
            entry_frame_sg.grid(row=i, column=1, padx=5, pady=6, sticky='ew')
            entry_frame_sg.grid_columnconfigure(0, weight=1)
            
            entry_sg = tk.Entry(
                entry_frame_sg,
                width=15,  # Reduced by 50%
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_sg.grid(row=0, column=0, sticky='ew')
            self.entries[f"{case}_sg"] = entry_sg
            entry_sg.bind('<KeyPress>', self.handle_key_press)
            entry_sg.bind('<KeyRelease>', lambda e, k=f"{case}_sg": (self.handle_text_change(e, k), self.clear_error(k)))
            entry_sg.bind('<Return>', lambda e, c=case, s='sg': self.handle_enter(e, f"{c}_{s}"))
            entry_sg.bind('<Up>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'up'))
            entry_sg.bind('<Down>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'down'))
            entry_sg.bind('<Left>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'left'))
            entry_sg.bind('<Right>', lambda e, c=case, s='sg': self.handle_arrow(e, f"{c}_{s}", 'right'))

            # Error label for singular
            error_label_sg = ttk.Label(
                entry_frame_sg,
                text="X",
                foreground='red',
                font=('Arial', 10, 'bold')
            )
            error_label_sg.grid(row=0, column=1, padx=(5, 0))
            self.error_labels[f"{case}_sg"] = error_label_sg
            error_label_sg.grid_remove()

            # Plural entry with consistent sizing
            # Create a frame to hold both entry and error label
            entry_frame_pl = tk.Frame(self.table_frame)
            entry_frame_pl.grid(row=i, column=2, padx=5, pady=6, sticky='ew')
            entry_frame_pl.grid_columnconfigure(0, weight=1)
            
            entry_pl = tk.Entry(
                entry_frame_pl,
                width=15,  # Reduced by 50%
                font=('Times New Roman', 14),
                relief='solid',
                borderwidth=1
            )
            entry_pl.grid(row=0, column=0, sticky='ew')
            self.entries[f"{case}_pl"] = entry_pl
            entry_pl.bind('<KeyPress>', self.handle_key_press)
            entry_pl.bind('<KeyRelease>', lambda e, k=f"{case}_pl": (self.handle_text_change(e, k), self.clear_error(k)))
            entry_pl.bind('<Return>', lambda e, c=case, s='pl': self.handle_enter(e, f"{c}_{s}"))
            entry_pl.bind('<Up>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'up'))
            entry_pl.bind('<Down>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'down'))
            entry_pl.bind('<Left>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'left'))
            entry_pl.bind('<Right>', lambda e, c=case, s='pl': self.handle_arrow(e, f"{c}_{s}", 'right'))

            # Error label for plural
            error_label_pl = ttk.Label(
                entry_frame_pl,
                text="X",
                foreground='red',
                font=('Arial', 10, 'bold')
            )
            error_label_pl.grid(row=0, column=1, padx=(5, 0))
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
                text="Case",
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
                    font=('Arial', 12, 'bold')
                )
                case_label.grid(row=i, column=0, padx=10, pady=6, sticky='e')

                # Masculine/Feminine columns (use masculine data since they're identical)
                for j, number in enumerate(["sg", "pl"]):
                    # Create a frame to hold both entry and error label
                    entry_frame = tk.Frame(self.table_frame)
                    entry_frame.grid(row=i, column=j + 1, padx=5, pady=6, sticky='ew')
                    entry_frame.grid_columnconfigure(0, weight=1)
                    
                    entry = tk.Entry(
                        entry_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=0, column=0, sticky='ew')
                    entry_key = f"{case}_masculine_{number}"  # Use masculine data
                    self.entries[entry_key] = entry
                    entry.bind('<KeyPress>', self.handle_key_press)
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: (self.handle_text_change(e, k), self.clear_error(k)))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))

                    # Error label
                    error_label = ttk.Label(
                        entry_frame,
                        text="X",
                        foreground='red',
                        font=('Arial', 10, 'bold')
                    )
                    error_label.grid(row=0, column=1, padx=(5, 0))
                    self.error_labels[entry_key] = error_label
                    error_label.grid_remove()

                # Neuter columns
                for j, number in enumerate(["sg", "pl"]):
                    # Create a frame to hold both entry and error label
                    entry_frame = tk.Frame(self.table_frame)
                    entry_frame.grid(row=i, column=j + 3, padx=5, pady=6, sticky='ew')
                    entry_frame.grid_columnconfigure(0, weight=1)
                    
                    entry = tk.Entry(
                        entry_frame,
                        width=15,  # Reduced by 50%
                        font=('Times New Roman', 14),
                        relief='solid',
                        borderwidth=1
                    )
                    entry.grid(row=0, column=0, sticky='ew')
                    entry_key = f"{case}_neuter_{number}"
                    self.entries[entry_key] = entry
                    entry.bind('<KeyPress>', self.handle_key_press)
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: (self.handle_text_change(e, k), self.clear_error(k)))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))

                    # Error label
                    error_label = ttk.Label(
                        entry_frame,
                        text="X",
                        foreground='red',
                        font=('Arial', 10, 'bold')
                    )
                    error_label.grid(row=0, column=1, padx=(5, 0))
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
                text="Case",
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
                    font=('Arial', 12, 'bold')
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
                    entry_sg.bind('<KeyPress>', self.handle_key_press)
                    entry_sg.bind('<KeyRelease>', lambda e, k=entry_key_sg: (self.handle_text_change(e, k), self.clear_error(k)))
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
                    entry_pl.bind('<KeyPress>', self.handle_key_press)
                    entry_pl.bind('<KeyRelease>', lambda e, k=entry_key_pl: (self.handle_text_change(e, k), self.clear_error(k)))
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
                    entry.bind('<KeyPress>', self.handle_key_press)
                    entry.bind('<KeyRelease>', lambda e, k=entry_key: (self.handle_text_change(e, k), self.clear_error(k)))
                    entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                    entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                    entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))

                    # Create error label in the same frame
                    error_label = ttk.Label(
                        entry_frame,
                        text="X",
                        foreground='red',
                        font=('Arial', 10, 'bold')
                    )
                    error_label.grid(row=0, column=1, padx=(5, 0))
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
                        entry.bind('<KeyPress>', self.handle_key_press)
                        entry.bind('<KeyRelease>', lambda e, k=entry_key: (self.handle_text_change(e, k), self.clear_error(k)))
                        entry.bind('<Return>', lambda e, k=entry_key: self.handle_enter(e, k))
                        entry.bind('<Up>', lambda e, k=entry_key: self.handle_arrow(e, k, 'up'))
                        entry.bind('<Down>', lambda e, k=entry_key: self.handle_arrow(e, k, 'down'))

                        # Create error label in the same frame
                        error_label = ttk.Label(
                            entry_frame,
                            text="X",
                            foreground='red',
                            font=('Arial', 10, 'bold')
                        )
                        error_label.grid(row=0, column=1, padx=(5, 0))
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
        
        # Determine if dropdowns should be disabled (in Starred mode or during starred context)
        dropdown_state = "disabled" if (self.type_var.get() == "Starred" or getattr(self, '_in_starred_context', False)) else "readonly"
        
        self.tense_dropdown = ttk.Combobox(
            selectors_frame,
            textvariable=self.tense_var,
            values=available_tenses,
            state=dropdown_state,
            width=12,
            font=('Arial', 10)
        )
        self.tense_dropdown.grid(row=1, column=0, sticky='ew', padx=(0, 10))
        if dropdown_state != "disabled":
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
            state=dropdown_state,
            width=12,
            font=('Arial', 10)
        )
        self.voice_dropdown.grid(row=1, column=1, sticky='ew', padx=(0, 10))
        if dropdown_state != "disabled":
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
            state=dropdown_state,
            width=12,
            font=('Arial', 10)
        )
        self.mood_dropdown.grid(row=1, column=2, sticky='ew')
        if dropdown_state != "disabled":
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
            entry.bind('<KeyPress>', self.handle_key_press)
            entry.bind('<KeyRelease>', lambda e, key=entry_key: (self.handle_text_change(e, key), self.clear_error(key)))
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
                entry.bind('<KeyPress>', self.handle_key_press)
                entry.bind('<KeyRelease>', lambda e, key=entry_key: (self.handle_text_change(e, key), self.clear_error(key)))
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

    def on_verb_form_change(self, event=None):
        """Handle changes to tense/voice/mood comboboxes for verbs.

        This handler updates available options, rebuilds the table, and
        refreshes the displayed word and instruction. It is intentionally
        defensive to avoid crashing the UI from transient state.
        """
        # Don't allow form changes when in Starred mode - forms should be locked
        if self.type_var.get() == "Starred" or getattr(self, '_in_starred_context', False):
            return
        
        # Update constraints; prefer the normal updater but fall back if it fails
        try:
            self.update_tense_mood_constraints()
        except Exception:
            try:
                self.update_tense_mood_constraints_fallback()
            except Exception:
                pass

        # Recreate the table and refresh labels
        try:
            self.reset_table()
            self.update_word_display()
        except Exception:
            pass

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
            cursor_pos = entry.index(tk.INSERT)
            
            # Get the character before the cursor
            if cursor_pos > 0:
                text = entry.get()
                prev_char = text[cursor_pos-1:cursor_pos]
                
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
        
        # Clear starred verb data when switching away from starred mode
        if self.type_var.get() != "Starred":
            if hasattr(self, 'current_starred_paradigm'):
                delattr(self, 'current_starred_paradigm')
            if hasattr(self, '_starred_verb_data'):
                delattr(self, '_starred_verb_data')
        
        # Use the raw type_var to check for Starred
        if self.type_var.get() == "Starred":
            # Handle starred items (should only be accessible if items exist)
            display_items = self.get_starred_display_items()
            
            if display_items:
                self.modes = display_items
                self.mode_var.set(display_items[0])
                
                # Update the dropdown values
                self.mode_dropdown['values'] = self.modes
                
                # Update instruction text
                self.update_instruction_text()
                
                # For starred items, delegate to on_mode_change to handle proper initialization
                # This ensures starred verbs get properly initialized with their specific data
                self.on_mode_change(None)
            else:
                # This shouldn't happen since "Starred" shouldn't be available without items
                # But as a safety fallback, switch to Noun
                self.type_var.set("Noun")
                self.on_type_change(None)
            return
            
        elif self.type_var.get() == "Noun":
            self.modes = self.noun_modes.copy()
            self.mode_var.set("First Declension (μουσα)")
        elif self.type_var.get() == "Adjective":
            self.modes = self.adjective_modes.copy()
            self.mode_var.set("Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)")
        elif self.type_var.get() == "Pronoun":
            self.modes = self.pronoun_modes.copy()
            self.mode_var.set("Personal I (ἐγώ)")
        else:  # Verb
            self.modes = self.verb_modes.copy()
            self.mode_var.set("Present Indicative Active - Release (λύω)")

        # Update the dropdown values
        self.mode_dropdown['values'] = self.modes

        # Update instruction text
        self.update_instruction_text()

        # Reset optimization trackers to force full table rebuild when switching types
        self._last_table_type = None
        self._last_pronoun_subtype = None

        # Recreate the table for the new type
        # Note: reset_table() will handle cleanup, then create_declension_table() will rebuild
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
            
            # Use the display map to find the correct starred item key
            display_map = self.get_starred_display_map()
            starred_item_key = display_map.get(selected_display)
            
            if not starred_item_key:
                print(f"Warning: Could not find starred item for display: {selected_display}")
                return
            
            # Parse the starred item key
            parts = starred_item_key.split(':')
            if len(parts) < 2:
                print(f"Warning: Invalid starred item key: {starred_item_key}")
                return
            
            item_type = parts[0]
            mode = parts[1]
            
            # Set a flag to indicate we're in starred context
            self._in_starred_context = True
            
            # Temporarily set type for table creation, but DON'T change mode_var
            # mode_var must stay as the display name for get_effective_type() to work
            self.type_var.set(item_type)
            # DO NOT SET mode_var here - it must remain as selected_display
            
            # Handle verb-specific logic with dedicated starred verb system
            if item_type == "Verb":
                # Use the dedicated starred verb system
                if self.init_starred_verb(starred_item_key):
                    paradigm = self.get_starred_verb_paradigm()
                    if paradigm:
                        self.create_starred_verb_table(paradigm)
                    else:
                        print(f"Warning: No paradigm found for starred verb: {starred_item_key}")
                        self.create_declension_table()
                else:
                    # Fallback for malformed verb keys
                    print(f"Warning: Could not initialize starred verb: {starred_item_key}")
                    self.create_declension_table()
            else:
                # Non-verb: use declension table
                self.create_declension_table()
            
            # Restore type_var to Starred BEFORE updating UI
            # This is critical so update_word_display() can detect we're in starred mode
            self.type_var.set("Starred")
            
            # Update UI (now that type_var is restored)
            self.update_word_display()
            
            # Clear the starred context flag
            self._in_starred_context = False
            return
        # Ensure we always have the current mode and verb form variables
        # defined for the logic below, whether or not we're in Starred mode.
        mode = self.mode_var.get()

        # Read current selections from the StringVars if they exist
        current_tense = self.tense_var.get() if hasattr(self, 'tense_var') else None
        current_mood = self.mood_var.get() if hasattr(self, 'mood_var') else None
        current_voice = self.voice_var.get() if hasattr(self, 'voice_var') else None

        # Extract lemma if mode contains a parenthesized lemma like '... (λύω)'
        if "(" in mode and ")" in mode:
            lemma = mode.split("(")[1].split(")")[0]
        else:
            lemma = None

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
            
            # Update tense dropdown if the widget exists
            if hasattr(self, 'tense_dropdown') and getattr(self.tense_dropdown, 'winfo_exists', lambda: False)():
                try:
                    self.tense_dropdown['values'] = available_tenses
                except Exception:
                    pass
            
            # Extract available moods for current tense and sort them according to hierarchy
            available_moods = list(set([combo[1] for combo in available_combinations if combo[0] == current_tense]))
            available_moods.sort(key=lambda x: self.verb_mood_order.index(x) if x in self.verb_mood_order else 999)
            
            # If current mood is not available for this tense, reset to first available
            if current_mood not in available_moods:
                if available_moods:
                    self.mood_var.set(available_moods[0])
                    current_mood = available_moods[0]
            
            # Update mood dropdown if the widget exists
            if hasattr(self, 'mood_dropdown') and getattr(self.mood_dropdown, 'winfo_exists', lambda: False)():
                try:
                    self.mood_dropdown['values'] = available_moods
                except Exception:
                    pass
            
            # Handle voice dropdown based on mood
            if current_mood == "Infinitive":
                # For infinitives, all voices are shown in the table, so voice selection is not needed
                # Set voice dropdown to show "All" or just the first available voice
                available_voices = list(set([combo[2] for combo in available_combinations 
                                           if combo[0] == current_tense and combo[1] == "Infinitive"]))
                if available_voices:
                    available_voices.sort(key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                    # For infinitives, just set to the first voice (but table shows all)
                    if hasattr(self, 'voice_dropdown') and getattr(self.voice_dropdown, 'winfo_exists', lambda: False)():
                        try:
                            self.voice_dropdown['values'] = [available_voices[0]]  # Only show one option
                            self.voice_var.set(available_voices[0])
                        except Exception:
                            pass
            else:
                # Extract available voices for current tense and mood and sort them according to hierarchy
                available_voices = list(set([combo[2] for combo in available_combinations 
                                           if combo[0] == current_tense and combo[1] == current_mood]))
                available_voices.sort(key=lambda x: self.verb_voice_order.index(x) if x in self.verb_voice_order else 999)
                
                # Update voice dropdown if it exists
                if hasattr(self, 'voice_dropdown') and getattr(self.voice_dropdown, 'winfo_exists', lambda: False)():
                    try:
                        self.voice_dropdown['values'] = available_voices
                        
                        # Reset voice if current selection is not available
                        if current_voice not in available_voices:
                            if available_voices:
                                self.voice_var.set(available_voices[0])
                    except Exception:
                        pass
        else:
            # Fallback to original logic if no lemma found
            self.update_tense_mood_constraints_fallback()

        # Always reset the table and update the word/instruction label after any mode change
        self.reset_table()
        self.update_word_display()

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
        
        # Update mood dropdown if the widget exists
        if hasattr(self, 'mood_dropdown') and getattr(self.mood_dropdown, 'winfo_exists', lambda: False)():
            try:
                self.mood_dropdown['values'] = available_moods
            except Exception:
                pass
        
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
        if hasattr(self, 'voice_dropdown') and getattr(self.voice_dropdown, 'winfo_exists', lambda: False)():
            current_voice = self.voice_var.get()
            current_mood = self.mood_var.get()
            
            # Handle infinitive mood specially
            if current_mood == "Infinitive":
                # For infinitives, only show one voice option since all are displayed in table
                if available_voices:
                    try:
                        self.voice_dropdown['values'] = [available_voices[0]]
                        self.voice_var.set(available_voices[0])
                    except Exception:
                        pass
            else:
                try:
                    self.voice_dropdown['values'] = available_voices
                except Exception:
                    pass
                
                # Reset voice if current selection is not available
                if current_voice not in available_voices:
                    self.voice_var.set("Active")

    def update_tense_mood_constraints(self):
        """Compatibility wrapper: call the fallback constraints updater.

        Some parts of the code expect a full update_tense_mood_constraints
        implementation. If it's missing, delegate to the fallback so the
        UI remains functional.
        """
        try:
            # If a more complete implementation exists elsewhere, it will
            # override this method. Otherwise, use the fallback.
            return self.update_tense_mood_constraints_fallback()
        except Exception:
            return
    
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
        
        # For starred verbs, return the stored paradigm directly
        if hasattr(self, 'current_starred_paradigm') and self.current_starred_paradigm:
            return self.current_starred_paradigm
        
        mode = self.mode_var.get()
        current_type = self.type_var.get()
        
        # Handle starred items - need to get the original mode for paradigm lookup
        original_mode = mode
        original_type = current_type
        starred_verb_forms = None  # Will hold (voice, tense, mood) for starred verbs
        
        if current_type == "Starred":
            # Use the display map to find the starred item key
            display_map = self.get_starred_display_map()
            starred_item_key = display_map.get(mode)
            
            if starred_item_key:
                parts = starred_item_key.split(':')
                if len(parts) >= 2:
                    original_type = parts[0]
                    original_mode = parts[1]
                    
                    # For starred verbs, extract the exact tense/mood/voice from the key
                    if original_type == "Verb" and len(parts) >= 5:
                        starred_verb_forms = (parts[2], parts[3], parts[4])  # (voice, tense, mood)
        
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
            
            # Get tense, voice, mood - prioritize starred forms, then dropdowns
            if starred_verb_forms:
                # Use the exact forms from the starred item key
                voice_val, tense_val, mood_val = starred_verb_forms
                voice_val = voice_val.lower()
                tense_val = tense_val.lower()
                mood_val = mood_val.lower()
            else:
                # Get from dropdowns (if they exist)
                tense = getattr(self, 'tense_var', None)
                voice = getattr(self, 'voice_var', None)
                mood = getattr(self, 'mood_var', None)
                
                if tense and voice and mood:
                    tense_val = tense.get().lower()
                    voice_val = voice.get().lower()
                    mood_val = mood.get().lower()
                else:
                    # No dropdown values available, use fallback
                    tense_val = voice_val = mood_val = None
            
            # Only proceed if we have all three values
            if tense_val and voice_val and mood_val:
                
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
            "Demonstrative This near (ὅδε, ἥδε, τόδε)": "hode",
            "Demonstrative That (ἐκεῖνος, ἐκείνη, ἐκεῖνο)": "ekeinos",
            "Indefinite Relative Whoever (ὅστις, ἥτις, ὅτι)": "hostis",
            "Reflexive Myself (ἐμαυτοῦ)": "emautou",
            "Reflexive Yourself (σεαυτοῦ)": "seautou",
            "Present Indicative Active - Release (λύω)": "luo_pres_ind_act",
            "Present Indicative Active - To Be (εἰμί)": "eimi_pres_ind_act",
            "Present Indicative Active - Step (βαίνω)": "baino_pres_ind_act"
        }
        
        paradigm_key = paradigm_map.get(original_mode)
        if not paradigm_key:
            # Debug: print what mode we're looking for
            print(f"Warning: Could not find paradigm mapping for mode: '{original_mode}'")
            print(f"Current type: {current_type}, Original type: {original_type}")
            if current_type == "Starred":
                print(f"Mode from dropdown: '{mode}'")
            return None
        return self.paradigms.get(paradigm_key)

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

        current_type = self.get_effective_type()
        
        # Iterate through all entries and prefill them
        for entry_key, entry in list(self.entries.items()):  # Use list() to avoid dict change during iteration
            try:
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
            except tk.TclError:
                # Widget was destroyed, skip it
                continue

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
        # Prevent revealing twice in a row
        if self.has_revealed:
            return
        
        # Disable the reveal button immediately to prevent double-clicking
        if hasattr(self, 'reveal_button'):
            self.reveal_button.configure(state='disabled')
        
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            # Re-enable reveal button if paradigm not found
            if hasattr(self, 'reveal_button'):
                self.reveal_button.configure(state='normal')
            return
        
        # Capture user answers BEFORE revealing
        user_answers_before_reveal = {}
        for entry_key, entry in self.entries.items():
            try:
                user_answers_before_reveal[entry_key] = entry.get().strip()
            except tk.TclError:
                # Widget has been destroyed, skip it
                continue
        
        # Clear error indicators
        for error_label in self.error_labels.values():
            try:
                error_label.grid_remove()
            except tk.TclError:
                # Widget has been destroyed, skip it
                continue
        
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
                                
                                try:
                                    user_answer = entry.get().strip()
                                    
                                    # Check if answer is correct
                                    is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                    
                                    entry.configure(state='normal')
                                    entry.delete(0, tk.END)
                                    entry.insert(0, correct_answer)
                                    
                                    if is_correct:
                                        # Correct answer - make it Olive Laurel and readonly
                                        entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Olive Laurel
                                    else:
                                        # Incorrect or missing answer - make it Terracotta Red and readonly
                                        entry.configure(state='readonly', readonlybackground='#B6523C')  # Terracotta Red
                                        self.incorrect_entries.add(entry_key)
                                except tk.TclError:
                                    # Widget has been destroyed, skip it
                                    continue
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
                            
                            try:
                                user_answer = entry.get().strip()
                                
                                # Check if answer is correct
                                is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                
                                entry.configure(state='normal')
                                entry.delete(0, tk.END)
                                entry.insert(0, correct_answer)
                                
                                if is_correct:
                                    # Correct answer - make it gold and readonly
                                    entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                                else:
                                    # Incorrect or missing answer - make it red and readonly
                                    entry.configure(state='readonly', readonlybackground='#B6523C')  # Light red color
                                    self.incorrect_entries.add(entry_key)
                            except tk.TclError:
                                # Widget has been destroyed, skip it
                                continue
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
                                    
                                    try:
                                        user_answer = entry.get().strip()
                                        
                                        # Check if answer is correct
                                        is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                        
                                        entry.configure(state='normal')
                                        entry.delete(0, tk.END)
                                        entry.insert(0, correct_answer)
                                        
                                        if is_correct:
                                            # Correct answer - make it gold and readonly
                                            entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                                        else:
                                            # Incorrect or missing answer - make it red and readonly
                                            entry.configure(state='readonly', readonlybackground='#B6523C')  # Light red color
                                            self.incorrect_entries.add(entry_key)
                                    except tk.TclError:
                                        # Widget has been destroyed, skip it
                                        continue
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
                        
                        try:
                            user_answer = entry.get().strip()
                            
                            # Check if answer is correct
                            is_correct = self.check_answer_correctness(user_answer, correct_answer)
                            
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            
                            if is_correct:
                                # Correct answer - make it gold and readonly
                                entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                            else:
                                # Incorrect or missing answer - make it red and readonly
                                entry.configure(state='readonly', readonlybackground='#B6523C')  # Light red color
                                self.incorrect_entries.add(entry_key)
                        except tk.TclError:
                            # Widget has been destroyed, skip it
                            continue
            else:
                # Check and fill finite verb answers (person/number structure)
                persons = ["1st", "2nd", "3rd"]
                for person in persons:
                    for number in ["sg", "pl"]:
                        entry_key = f"{person}_{number}"
                        
                        if entry_key in self.entries and entry_key in current_paradigm:
                            entry = self.entries[entry_key]
                            correct_answer = current_paradigm[entry_key]
                            
                            try:
                                user_answer = entry.get().strip()
                                
                                # Check if answer is correct
                                is_correct = self.check_answer_correctness(user_answer, correct_answer)
                                
                                entry.configure(state='normal')
                                entry.delete(0, tk.END)
                                entry.insert(0, correct_answer)
                                
                                if is_correct:
                                    # Correct answer - make it gold and readonly
                                    entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                                else:
                                    # Incorrect or missing answer - make it red and readonly
                                    entry.configure(state='readonly', readonlybackground='#B6523C')  # Light red color
                                    self.incorrect_entries.add(entry_key)
                            except tk.TclError:
                                # Widget has been destroyed, skip it
                                continue
        else:
            # Check and fill noun answers (simple structure)
            cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
            for case in cases:
                for number in ["sg", "pl"]:
                    entry_key = f"{case}_{number}"
                    
                    if entry_key in self.entries and entry_key in current_paradigm:
                        entry = self.entries[entry_key]
                        correct_answer = current_paradigm[entry_key]
                        
                        try:
                            user_answer = entry.get().strip()
                            
                            # Check if answer is correct
                            is_correct = self.check_answer_correctness(user_answer, correct_answer)
                            
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, correct_answer)
                            
                            if is_correct:
                                # Correct answer - make it gold and readonly
                                entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                            else:
                                # Incorrect or missing answer - make it red and readonly
                                entry.configure(state='readonly', readonlybackground='#B6523C')  # Light red color
                                self.incorrect_entries.add(entry_key)
                        except tk.TclError:
                            # Widget has been destroyed, skip it
                            continue
        
        # Mark that answers have been revealed and update button
        self.has_revealed = True
        self.update_reset_retry_button()

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
        
        # Re-enable the reveal button
        if hasattr(self, 'reveal_button'):
            self.reveal_button.configure(state='normal')
        
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
        
        # Re-enable the reveal button
        if hasattr(self, 'reveal_button'):
            self.reveal_button.configure(state='normal')
        
        self.update_reset_retry_button()

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
        
        # Re-enable the reveal button
        if hasattr(self, 'reveal_button'):
            self.reveal_button.configure(state='normal')
        
        self.update_reset_retry_button()
        
        # DON'T clear dictionaries if we're about to use optimization
        # Only clear them if we need to rebuild from scratch
        current_type = self.get_effective_type()
        
        # Check if noun optimization will be used
        will_use_noun_optimization = (current_type == "Noun" and 
                                     hasattr(self, 'table_frame') and self.table_frame and 
                                     hasattr(self, '_last_table_type') and self._last_table_type == "Noun" and
                                     len(self.entries) > 0 and
                                     not getattr(self, '_in_starred_context', False) and
                                     self.table_frame.winfo_exists())
        
        # Check if pronoun optimization will be used
        will_use_pronoun_optimization = False
        if (current_type == "Pronoun" and 
            hasattr(self, 'table_frame') and self.table_frame and 
            hasattr(self, '_last_table_type') and self._last_table_type == "Pronoun" and
            hasattr(self, '_last_pronoun_subtype') and
            len(self.entries) > 0 and
            not getattr(self, '_in_starred_context', False) and
            self.table_frame.winfo_exists()):
            
            mode = self.mode_var.get()
            current_subtype = "Personal" if ("Personal I" in mode or "Personal You" in mode) else "Gender"
            will_use_pronoun_optimization = (self._last_pronoun_subtype == current_subtype)
        
        if not will_use_noun_optimization and not will_use_pronoun_optimization:
            # Clear dictionaries and recreate the table based on type
            self.entries.clear()
            self.error_labels.clear()
        
        # Get the effective type to determine which table to create
        current_type = self.get_effective_type()
        
        # Set starred context flag if we're in starred mode
        is_starred = self.type_var.get() == "Starred"
        
        if is_starred:
            self._in_starred_context = True
        
        try:
            if current_type == "Verb":
                # For verbs, check if this is a starred verb
                if is_starred:
                    # Starred verb - need to use starred verb system
                    # First ensure starred verb data is initialized
                    if not hasattr(self, '_starred_verb_data') or not hasattr(self, 'current_starred_paradigm'):
                        # Try to reinitialize from current mode selection
                        selected_display = self.mode_var.get()
                        display_map = self.get_starred_display_map()
                        starred_item_key = display_map.get(selected_display)
                        
                        if starred_item_key:
                            # Reinitialize the starred verb
                            self.init_starred_verb(starred_item_key)
                    
                    # Now get paradigm and create table
                    paradigm = self.get_starred_verb_paradigm()
                    if paradigm:
                        self.create_starred_verb_table(paradigm)
                    else:
                        print(f"Warning: No paradigm found for starred verb in reset_table")
                        self.create_declension_table()
                else:
                    # Regular verb - use normal system (create_declension_table creates both table and buttons)
                    self.create_declension_table()
            elif current_type == "Adjective":
                # Create adjective table
                current_paradigm = self.get_current_paradigm()
                if current_paradigm:
                    self.create_adjective_table(current_paradigm)
                else:
                    self.create_declension_table()
            elif current_type == "Pronoun":
                # Create pronoun table
                current_paradigm = self.get_current_paradigm()
                if current_paradigm:
                    self.create_pronoun_table(current_paradigm)
                else:
                    self.create_declension_table()
            else:
                # For nouns and fallback cases, use the standard declension table creator
                self.create_declension_table()
        finally:
            # Clear the starred context flag
            if is_starred:
                self._in_starred_context = False

    def show_help(self):
        """Show help dialog."""
        help_text = '''Bellerophon Grammar Study

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
        help_window.title("Bellerophon Grammar Help")
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

    def handle_text_change(self, event, entry_key):
        """Handle text changes in entry fields to reset red background."""
        # Only reset if it's a text-modifying key (not navigation keys)
        text_keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                     'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                     '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ' ', '-', '_', '=', '+', ';', "'", ',', '.', '/', '`',
                     'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',
                     'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω',
                     'ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ', 'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ', 'ᾶ', 'ῆ', 'ῖ', 'ῦ', 'ῶ', 'ᾳ', 'ῃ', 'ῳ', 'ῇ', 'ῷ',
                     'ἀ', 'ἁ', 'ἂ', 'ἃ', 'ἄ', 'ἅ', 'ἆ', 'ἇ', 'ἐ', 'ἑ', 'ἒ', 'ἓ', 'ἔ', 'ἕ', 'ἠ', 'ἡ', 'ἢ', 'ἣ', 'ἤ', 'ἥ', 'ἦ', 'ἧ', 'ἰ', 'ἱ', 'ἲ', 'ἳ', 'ἴ', 'ἵ', 'ἶ', 'ἷ',
                     'ὀ', 'ὁ', 'ὂ', 'ὃ', 'ὄ', 'ὅ', 'ὐ', 'ὑ', 'ὒ', 'ὓ', 'ὔ', 'ὕ', 'ὖ', 'ὗ', 'ὠ', 'ὡ', 'ὢ', 'ὣ', 'ὤ', 'ὥ', 'ὦ', 'ὧ', 'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ', 'ᾶ', 'ῆ', 'ῖ', 'ῦ', 'ῶ']

        # Check if the key pressed is a text-modifying key
        key_char = event.char
        if key_char in text_keys or event.keysym in ['BackSpace', 'Delete', 'space', 'Return']:
            entry = self.entries.get(entry_key)
            if entry and entry.cget('bg') == '#FFB6B6':  # If currently red
                entry.configure(bg='white')  # Reset to white
                # Remove from incorrect entries tracking
                if entry_key in self.incorrect_entries:
                    self.incorrect_entries.remove(entry_key)
        return None

    def handle_enter(self, event, current_key):
        """Handle Enter key press in form fields."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm:
            return "break"

        # Check if this entry is correct before moving to next
        if self.check_single_entry(current_key):
            self.check_and_auto_advance()
            # Only move to next entry if not auto-advanced
            # (If auto-advance happened, the table will have changed)
            # So, only move if not all correct or auto-advance is off
            auto_advance_enabled = False
            if hasattr(self, 'config') and hasattr(self.config, 'auto_advance'):
                auto_advance_enabled = self.config.auto_advance.get() if hasattr(self.config.auto_advance, 'get') else self.config.auto_advance
            elif hasattr(self, 'auto_advance'):
                auto_advance_enabled = self.auto_advance.get() if hasattr(self.auto_advance, 'get') else self.auto_advance
            all_correct = all(str(entry.cget('state')) == 'readonly' for entry in self.entries.values())
            if not (all_correct and auto_advance_enabled):
                self.move_to_next_entry(current_key)

        return "break"

    def check_single_entry(self, entry_key):
        """Check if a single entry is correct and apply visual feedback."""
        current_paradigm = self.get_current_paradigm()
        if not current_paradigm or entry_key not in self.entries:
            return False

        # Use effective type so Starred items are checked as their original type
        current_type = self.get_effective_type()
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
                entry.configure(state='readonly', readonlybackground='#7C8C4E')  # Gold color
                if error_label:
                    error_label.grid_remove()
                # Check auto-advance after setting readonly
                self.check_and_auto_advance()
            else:
                # Mark as incorrect - turn red like reveal button, no red cross
                entry.configure(bg='#B6523C')  # Light red color, same as reveal
                entry.configure(state='normal')
                if error_label:
                    error_label.grid_remove()  # Hide red cross

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
        current_type = self.get_effective_type()
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
        # Only handle up/down navigation, let left/right work normally within entry
        if direction not in ['up', 'down']:
            return None  # Let Tkinter handle left/right normally
        
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

    def load_latin_starred_items(self):
        """Load Latin starred items from file."""
        try:
            import os
            if os.path.exists(self.latin_starred_file):
                import json
                with open(self.latin_starred_file, 'r', encoding='utf-8') as f:
                    starred_list = json.load(f)
                    self.latin_starred_items = set(starred_list)
        except Exception as e:
            print(f"Error loading Latin starred items: {e}")
            self.latin_starred_items = set()

    def save_latin_starred_items(self):
        """Save Latin starred items to file."""
        try:
            import json
            with open(self.latin_starred_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.latin_starred_items), f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.latin_starred_items)} Latin starred items")
        except Exception as e:
            print(f"Error saving Latin starred items: {e}")

    def get_available_latin_types(self):
        """Get the list of available Latin types based on whether starred items exist."""
        base_types = ["Noun", "Verb", "Adjective"]
        
        # Check if there are any starred items
        if self.latin_starred_items:
            # If starred items exist, add "Starred" at the end
            return base_types + ["Starred"]
        else:
            # If no starred items, just return base types
            return base_types
    
    def update_latin_type_dropdown(self):
        """Update the Latin type dropdown values based on current starred items."""
        available_types = self.get_available_latin_types()
        
        # Update the dropdown values
        if hasattr(self, 'latin_type_dropdown'):
            current_value = self.latin_type_var.get()
            self.latin_type_dropdown['values'] = available_types
            
            # If current selection is "Starred" but no starred items exist, switch to "Noun"
            if current_value == "Starred" and "Starred" not in available_types:
                self.latin_type_var.set("Noun")
                self.on_latin_type_change(None)

    def load_pronoun_modes_from_json(self):
        """Dynamically load pronoun modes from the JSON paradigms file."""
        pronoun_modes = []
        pronoun_types = ["pronoun", "pronoun_personal", "pronoun_gender", "article"]
        
        for paradigm in self.paradigms.values():
            if paradigm.get("type") in pronoun_types:
                lemma = paradigm.get("lemma", "")
                # Create a display name based on lemma and type
                if lemma.startswith("ὁ"):
                    pronoun_modes.append("Article (ὁ, ἡ, τό)")
                elif lemma.startswith("ἐγώ"):
                    pronoun_modes.append("Personal I (ἐγώ)")
                elif lemma.startswith("σύ"):
                    pronoun_modes.append("Personal You (σύ)")
                elif lemma.startswith("αὐτός"):
                    pronoun_modes.append("Personal Third Person (αὐτός, αὐτή, αὐτό)")
                elif lemma.startswith("οὗτος"):
                    pronoun_modes.append("Demonstrative This (οὗτος, αὕτη, τοῦτο)")
                elif lemma.startswith("ὅς"):
                    pronoun_modes.append("Relative Who/Which (ὅς, ἥ, ὅ)")
                elif lemma.startswith("τίς"):
                    pronoun_modes.append("Interrogative Who/What (τίς, τί)")
                elif lemma.startswith("τις"):
                    pronoun_modes.append("Indefinite Someone/Something (τις, τι)")
                elif lemma.startswith("ὅδε"):
                    pronoun_modes.append("Demonstrative This near (ὅδε, ἥδε, τόδε)")
                elif lemma.startswith("ἐκεῖνος"):
                    pronoun_modes.append("Demonstrative That (ἐκεῖνος, ἐκείνη, ἐκεῖνο)")
                elif lemma.startswith("ὅστις"):
                    pronoun_modes.append("Indefinite Relative Whoever (ὅστις, ἥτις, ὅτι)")
                elif lemma.startswith("ἐμαυτοῦ"):
                    pronoun_modes.append("Reflexive Myself (ἐμαυτοῦ)")
                elif lemma.startswith("σεαυτοῦ"):
                    pronoun_modes.append("Reflexive Yourself (σεαυτοῦ)")
                else:
                    # Fallback for any other pronouns
                    pronoun_modes.append(f"Pronoun ({lemma})")
        return pronoun_modes

    def update_instruction_text(self):
        """Update the instruction text based on current type and selections."""
        # Prefer the effective type so Starred maps back to its original
        current_type = self.get_effective_type()

        # Try to get the lemma from the displayed word label (if available)
        displayed_word = None
        try:
            displayed_word = self.word_label.cget('text')
        except Exception:
            displayed_word = None

        # Fallback: try to extract lemma from the mode string
        mode = self.mode_var.get()
        lemma = None
        if displayed_word and displayed_word != "—":
            lemma = displayed_word
        elif "(" in mode and ")" in mode:
            lemma = mode.split("(")[1].split(")")[0]

        # Build instruction text based on effective type and presence of lemma
        if current_type == "Verb":
            # Don't duplicate the verb name since it's already in the word label
            instruction_text = "Conjugate the verb:"

        elif current_type == "Starred":
            # If the starred original type is a verb (lemma present), conjugate
            if lemma and any(v in (mode + (lemma or "")) for v in ["λύω", "εἰμί", "φιλέω", "τιμάω", "δηλόω", "βάλλω", "βαίνω", "δίδωμι", "τίθημι", "ἵστημι", "οἶδα", "εἶμι", "φημί", "ἵημι"]):
                instruction_text = "Conjugate the verb:"
            else:
                instruction_text = "Decline the word:"

        else:
            # For nouns, adjectives, and pronouns
            instruction_text = "Decline the word:"

        self.instruction_label.config(text=instruction_text)

    def load_header_logo(self):
        """Load and resize the long logo for the app header."""
        logo_paths = [
            os.path.join('assets', 'Bellerphon_grammar_long-remove bg.png'),
            os.path.join('assets', 'Bellerphon_grammar_long-remove bg.jpg'),
            os.path.join('assets', 'Bellerphon_grammar_long-remove bg.jpeg'),
            'Bellerphon_grammar_long-remove bg.png',
            'Bellerphon_grammar_long-remove bg.jpg',
            'Bellerphon_grammar_long-remove bg.jpeg'
        ]
        
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                try:
                    if PIL_AVAILABLE:
                        # Use PIL for better resizing
                        image = Image.open(logo_path)
                        # Resize long logo to fit nicely in header
                        image = image.convert("RGBA")
                        original_width, original_height = image.size
                        
                        # Calculate new size maintaining aspect ratio
                        # Target height for header logo (120px for better visibility)
                        max_height = 120
                        max_width = 600  # Allow wider for long logo
                        
                        # Calculate scaling factor
                        height_ratio = max_height / original_height
                        width_ratio = max_width / original_width
                        ratio = min(height_ratio, width_ratio, 1.0)  # Don't upscale
                        
                        if ratio < 1.0:  # Only resize if needed
                            new_width = int(original_width * ratio)
                            new_height = int(original_height * ratio)
                            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        return ImageTk.PhotoImage(image)
                    else:
                        # Fallback: tkinter PhotoImage with subsample for size reduction
                        if logo_path.lower().endswith('.png'):
                            original_image = tk.PhotoImage(file=logo_path)
                            
                            # Get original dimensions
                            original_width = original_image.width()
                            original_height = original_image.height()
                            
                            # Calculate subsample factor to reduce size
                            # Target height ~100px for header logo
                            target_height = 100
                            if original_height > target_height:
                                subsample_factor = max(1, original_height // target_height)
                                return original_image.subsample(subsample_factor, subsample_factor)
                            else:
                                return original_image
                        else:
                            print(f"PIL not available. Cannot load {logo_path}. Please use PNG format or install PIL.")
                            continue
                            
                except Exception as e:
                    print(f"Error loading header logo from {logo_path}: {e}")
                    continue
        
        print("No header logo found. Searched paths:", logo_paths)
        return None

    def load_latin_header_logo(self):
        """Load and resize the Latin logo for the app header."""
        logo_paths = [
            os.path.join('assets', 'b grammar latin large logo gold.png'),
            os.path.join('assets', 'b grammar latin large logo gold.jpg'),
            os.path.join('assets', 'b grammar latin large logo gold.jpeg'),
            'b grammar latin large logo gold.png',
            'b grammar latin large logo gold.jpg',
            'b grammar latin large logo gold.jpeg'
        ]
        
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                try:
                    if PIL_AVAILABLE:
                        # Use PIL for better resizing
                        image = Image.open(logo_path)
                        # Resize long logo to fit nicely in header
                        image = image.convert("RGBA")
                        original_width, original_height = image.size
                        
                        # Calculate new size maintaining aspect ratio
                        # Target height for header logo (120px for better visibility)
                        max_height = 120
                        max_width = 600  # Allow wider for long logo
                        
                        # Calculate scaling factor
                        height_ratio = max_height / original_height
                        width_ratio = max_width / original_width
                        ratio = min(height_ratio, width_ratio, 1.0)  # Don't upscale
                        
                        if ratio < 1.0:  # Only resize if needed
                            new_width = int(original_width * ratio)
                            new_height = int(original_height * ratio)
                            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        return ImageTk.PhotoImage(image)
                    else:
                        # Fallback: tkinter PhotoImage with subsample for size reduction
                        if logo_path.lower().endswith('.png'):
                            original_image = tk.PhotoImage(file=logo_path)
                            
                            # Get original dimensions
                            original_width = original_image.width()
                            original_height = original_image.height()
                            
                            # Calculate subsample factor to reduce size
                            # Target height ~100px for header logo
                            target_height = 100
                            if original_height > target_height:
                                subsample_factor = max(1, original_height // target_height)
                                return original_image.subsample(subsample_factor, subsample_factor)
                            else:
                                return original_image
                        else:
                            print(f"PIL not available. Cannot load {logo_path}. Please use PNG format or install PIL.")
                            continue
                            
                except Exception as e:
                    print(f"Error loading Latin header logo from {logo_path}: {e}")
                    continue
        
        print("No Latin header logo found. Searched paths:", logo_paths)
        return None

    def load_app_icon(self):
        """Load the small icon for the app window."""
        icon_paths = [
            os.path.join('assets', 'bell simple.png'),
            os.path.join('assets', 'bell simple.jpg'),
            os.path.join('assets', 'bell simple.jpeg'),
            'bell simple.png',
            'bell simple.jpg',
            'bell simple.jpeg'
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    if PIL_AVAILABLE:
                        # Use PIL for better resizing
                        image = Image.open(icon_path)
                        # Keep icon small for window icon
                        image = image.convert("RGBA")
                        original_width, original_height = image.size
                        
                        # Target size for window icon (small)
                        max_size = 32  # Standard window icon size
                        
                        # Calculate scaling factor
                        ratio = min(max_size / original_width, max_size / original_height, 1.0)
                        
                        if ratio < 1.0:  # Only resize if needed
                            new_width = int(original_width * ratio)
                            new_height = int(original_height * ratio)
                            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        
                        return ImageTk.PhotoImage(image)
                    else:
                        # Fallback: tkinter PhotoImage
                        if icon_path.lower().endswith('.png'):
                            original_image = tk.PhotoImage(file=icon_path)
                            
                            # Get original dimensions
                            original_width = original_image.width()
                            original_height = original_image.height()
                            
                            # Calculate subsample factor for small icon
                            target_size = 32
                            if original_width > target_size or original_height > target_size:
                                subsample_factor = max(1, max(original_width, original_height) // target_size)
                                return original_image.subsample(subsample_factor, subsample_factor)
                            else:
                                return original_image
                        else:
                            print(f"PIL not available. Cannot load {icon_path}. Please use PNG format or install PIL.")
                            continue
                            
                except Exception as e:
                    print(f"Error loading app icon from {icon_path}: {e}")
                    continue
        
        print("No app icon found. Searched paths:", icon_paths)
        return None

    def get_current_item_key(self):
        """Get the current table's key for starring (format: 'type:mode' or 'Verb:mode:voice:tense:mood')."""
        current_type = self.type_var.get()
        current_mode = self.mode_var.get()
        
        # If we're in Starred tab, extract the actual item key from the display map
        if current_type == "Starred":
            display_map = self.get_starred_display_map()
            return display_map.get(current_mode, "")
        
        # For verbs, include voice/tense/mood in the key for specificity
        if current_type == "Verb":
            voice = getattr(self, 'voice_var', None)
            tense = getattr(self, 'tense_var', None)
            mood = getattr(self, 'mood_var', None)
            if voice and tense and mood:
                return f"Verb:{current_mode}:{voice.get()}:{tense.get()}:{mood.get()}"
            else:
                return f"Verb:{current_mode}"
        else:
            return f"{current_type}:{current_mode}"
    
    def get_current_latin_item_key(self):
        """Get the current Latin table's key for starring."""
        word_display = self.latin_word_var.get()
        word = word_display.split(' (')[0]
        
        # Find the paradigm to get type
        paradigm_type = None
        for key, data in self.latin_paradigms.items():
            word_value = data.get('word') or data.get('lemma')
            if word_value == word:
                paradigm_type = data.get('type')
                if paradigm_type == 'verb':
                    # For verbs, match tense/voice/mood
                    if (data.get('tense') == self.latin_tense_var.get() and
                        data.get('voice') == self.latin_voice_var.get() and
                        data.get('mood') == self.latin_mood_var.get()):
                        return f"Latin:Verb:{word}:{self.latin_voice_var.get()}:{self.latin_tense_var.get()}:{self.latin_mood_var.get()}"
                else:
                    # For nouns, just use type and word
                    return f"Latin:Noun:{word}"
        
        return ""

    def is_current_item_starred(self):
        """Check if the current table is starred."""
        return self.get_current_item_key() in self.starred_items
    
    def is_current_latin_item_starred(self):
        """Check if the current Latin table is starred."""
        return self.get_current_latin_item_key() in self.latin_starred_items

    def toggle_star(self):
        """Toggle star status of current table."""
        current_type = self.type_var.get()
        item_key = self.get_current_item_key()
        
        if item_key in self.starred_items:
            # Unstar the item
            self.starred_items.remove(item_key)
            self.save_starred_items()
            
            # Update type dropdown (might remove "Starred" if no items left)
            self.update_type_dropdown()
            
            # Special handling if we're in the Starred tab
            if current_type == "Starred":
                # Get remaining starred items
                display_map = self.get_starred_display_map()
                remaining_displays = list(display_map.keys())
                
                if remaining_displays:
                    # Update dropdown with remaining items
                    self.modes = remaining_displays
                    self.mode_dropdown['values'] = self.modes
                    
                    # Select the first remaining item
                    next_display = remaining_displays[0]
                    self.mode_var.set(next_display)
                    
                    # Trigger on_mode_change to display the next item properly
                    self.on_mode_change(None)
                else:
                    # No starred items left - type dropdown already updated above
                    # Switch to Noun and display first noun paradigm
                    self.type_var.set("Noun")
                    self.on_type_change(None)
            else:
                # We're in a regular tab - just update the star button
                self.update_star_button()
            
            return  # Exit early after unstarring
        
        elif current_type != "Starred":
            # Star the item (only allowed in normal tabs, not in Starred tab)
            self.starred_items.add(item_key)
            self.save_starred_items()
            print(f"Starred: {item_key}")
            
            # Update type dropdown (might add "Starred" if first item)
            self.update_type_dropdown()
        else:
            # In starred mode, only allow unstarring
            print("Cannot star items while in Starred mode - only unstarring is allowed")
            return
        
        # Update star button appearance
        self.update_star_button()

    def update_star_button(self):
        """Update the star button appearance based on current star status."""
        if self.star_button:
            current_type = self.type_var.get()
            is_starred = self.is_current_item_starred()
            
            if current_type == "Starred":
                # In starred mode, always show filled yellow star (can only unstar)
                self.star_button.config(text="★", foreground="gold")
            elif is_starred:
                # In normal mode but item is starred - filled yellow star
                self.star_button.config(text="★", foreground="gold")
            else:
                # In normal mode and item is not starred - outline black star
                self.star_button.config(text="☆", foreground="black")

    def on_star_hover_enter(self, event):
        """Handle mouse entering the star button area."""
        if self.star_button:
            is_starred = self.is_current_item_starred()
            if is_starred:
                # Hover effect for starred items - brighter yellow
                self.star_button.config(foreground="#FFD700", background="#FFF8DC")
            else:
                # Hover effect for unstarred items - preview yellow
                self.star_button.config(text="★", foreground="#FFD700", background="#FFF8DC")

    def on_star_hover_leave(self, event):
        """Handle mouse leaving the star button area."""
        if self.star_button:
            # Reset to normal appearance
            self.star_button.config(background="white")
            self.update_star_button()  # Restore normal state
    
    def toggle_latin_star(self):
        """Toggle star status of current Latin table."""
        current_type = self.latin_type_var.get()
        item_key = self.get_current_latin_item_key()
        
        if item_key in self.latin_starred_items:
            # Unstar the item
            self.latin_starred_items.remove(item_key)
            self.save_latin_starred_items()
            
            # Update type dropdown (might remove "Starred" if no items left)
            self.update_latin_type_dropdown()
            
            # Special handling if we're in the Starred tab
            if current_type == "Starred":
                # Get remaining starred items
                remaining_words = []
                for starred_key in self.latin_starred_items:
                    parts = starred_key.split(':')
                    if len(parts) >= 3 and parts[0] == "Latin":
                        word_type = parts[1]
                        word = parts[2]
                        
                        if word_type == "Verb" and len(parts) >= 6:
                            # Format: Latin:Verb:word:voice:tense:mood
                            voice = parts[3]
                            tense = parts[4]
                            mood = parts[5]
                            display = f"{word} ({voice} {tense} {mood})"
                            remaining_words.append(display)
                        elif word_type == "Noun":
                            # Find English translation
                            english = ""
                            for key, data in self.latin_paradigms.items():
                                word_value = data.get('word', '')
                                if word_value == word and data.get('type') == 'noun':
                                    english = data.get('english', '')
                                    break
                            display = f"{word} ({english})" if english else word
                            remaining_words.append(display)
                
                if remaining_words:
                    # Update dropdown with remaining items
                    if hasattr(self, 'latin_word_dropdown'):
                        self.latin_word_dropdown['values'] = remaining_words
                        
                        # Select the first remaining item
                        self.latin_word_var.set(remaining_words[0])
                        
                        # Trigger word change to display the next item properly
                        self.on_latin_word_change(None)
                else:
                    # No starred items left - type dropdown already updated above
                    # Switch to Noun and display first noun
                    self.latin_type_var.set("Noun")
                    self.on_latin_type_change(None)
            else:
                # We're in a regular tab - just update the star button
                self.update_latin_star_button()
            
            return  # Exit early after unstarring
        
        elif current_type != "Starred":
            # Star the item (only allowed in normal tabs, not in Starred tab)
            self.latin_starred_items.add(item_key)
            self.save_latin_starred_items()
            print(f"Starred Latin: {item_key}")
            
            # Update type dropdown (might add "Starred" if first item)
            self.update_latin_type_dropdown()
        else:
            # In starred mode, only allow unstarring
            print("Cannot star items while in Starred mode - only unstarring is allowed")
            return
        
        # Update star button appearance
        self.update_latin_star_button()
    
    def update_latin_star_button(self):
        """Update the Latin star button appearance based on current star status."""
        if hasattr(self, 'latin_star_button') and self.latin_star_button:
            current_type = self.latin_type_var.get()
            is_starred = self.is_current_latin_item_starred()
            
            if current_type == "Starred":
                # In starred mode, always show filled yellow star (can only unstar)
                self.latin_star_button.config(text="★", foreground="gold")
            elif is_starred:
                # In normal mode but item is starred - filled yellow star
                self.latin_star_button.config(text="★", foreground="gold")
            else:
                # In normal mode and item is not starred - outline white star
                self.latin_star_button.config(text="☆", foreground="white")
    
    def on_latin_star_hover_enter(self, event):
        """Handle mouse entering the Latin star button area."""
        if hasattr(self, 'latin_star_button') and self.latin_star_button:
            is_starred = self.is_current_latin_item_starred()
            if is_starred:
                self.latin_star_button.config(foreground="#FFD700", background="#6B0000")
            else:
                self.latin_star_button.config(text="★", foreground="#FFD700", background="#6B0000")
    
    def on_latin_star_hover_leave(self, event):
        """Handle mouse leaving the Latin star button area."""
        if hasattr(self, 'latin_star_button') and self.latin_star_button:
            self.latin_star_button.config(background="#8B0000")
            self.update_latin_star_button()

    def get_starred_display_items(self):
        """Get list of starred items formatted for dropdown display."""
        # Return just the display labels for the dropdown
        return list(self.get_starred_display_map().keys())

    def get_starred_display_map(self):
        """Return a mapping of display_label -> starred_item_key.

        Display labels are user-friendly strings shown in the dropdown; the
        keys are the internal stored item identifiers (e.g.,
        'Verb:Present Indicative Active - Release (λύω):Active:Present:Indicative').
        """
        display_map = {}
        for item_key in getattr(self, 'starred_items', set()):
            parts = item_key.split(':')
            if len(parts) < 2:
                # Invalid key format - skip
                continue
            
            item_type = parts[0]
            
            if item_type == 'Verb' and len(parts) >= 5:
                mode = parts[1]
                voice = parts[2]
                tense = parts[3]
                mood = parts[4]
                
                # Extract verb name from mode (e.g., "Present Indicative Active - Release (λύω)")
                if "(" in mode and ")" in mode:
                    verb_name = mode.split("(")[1].split(")")[0]
                    display_label = f"{verb_name} - {tense} {voice} {mood}"
                else:
                    display_label = f"{mode} - {tense} {voice} {mood}"
            else:
                # Non-verb starred entries: use the mode string as label
                display_label = parts[1]
            
            # Store the mapping (later items with same display override earlier ones)
            display_map[display_label] = item_key
        
        return display_map

    def update_starred_dropdown(self):
        """Update the mode dropdown when in starred mode."""
        if self.type_var.get() == "Starred":
            starred_items = self.get_starred_display_items()
            
            if starred_items:
                self.modes = starred_items
                self.mode_dropdown['values'] = starred_items
                
                # If current selection is no longer valid, select first item
                if self.mode_var.get() not in starred_items:
                    self.mode_var.set(starred_items[0])
                    self.on_mode_change(None)
            else:
                # No starred items left, set to "No starred items"
                self.modes = ["No starred items"]
                self.mode_dropdown['values'] = self.modes
                self.mode_var.set("No starred items")

def main():
    try:
        root = tk.Tk()
        root.title("Bellerophon Grammar Study")
        
        root.minsize(600, 400)
        root.geometry("800x600")
        
        style = ttk.Style()
        style.configure('Content.TFrame', background='white', relief='solid')
        
        app = BellerophonGrammarApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
