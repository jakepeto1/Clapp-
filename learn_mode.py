import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
from database import DatabaseManager

class UserManager:
    """Manages user authentication and profile selection"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_user = None
        self.login_window = None
    
    def show_user_selection(self, parent) -> Optional[Dict]:
        """Show user selection/creation dialog"""
        self.login_window = tk.Toplevel(parent)
        self.login_window.title("Select User Profile")
        self.login_window.geometry("450x600")
        self.login_window.resizable(False, False)
        self.login_window.grab_set()  # Make modal
        
        # Center the window
        self.login_window.transient(parent)
        self.login_window.geometry("+{}+{}".format(
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
        main_frame = ttk.Frame(self.login_window, padding="20")
        main_frame.grid(row=0, column=0, sticky='nsew')
        
        # Title
        title_label = ttk.Label(main_frame, text="Greek Grammar Learn Mode", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Existing users section
        ttk.Label(main_frame, text="Select Existing User:", 
                 font=('Arial', 12, 'bold')).grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # User listbox
        self.user_listbox = tk.Listbox(main_frame, height=8, width=40)
        self.user_listbox.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky='ew')
        
        # Populate existing users
        self.populate_user_list()
        
        # Buttons for existing users
        user_button_frame = ttk.Frame(main_frame)
        user_button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Button(user_button_frame, text="Select User", 
                  command=self.select_existing_user).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(user_button_frame, text="Delete User", 
                  command=self.delete_user).grid(row=0, column=1)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, 
                                                           sticky='ew', pady=20)
        
        # New user section
        ttk.Label(main_frame, text="Create New User:", 
                 font=('Arial', 12, 'bold')).grid(row=5, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # New user form
        ttk.Label(main_frame, text="Username:").grid(row=6, column=0, sticky='w')
        self.username_entry = ttk.Entry(main_frame, width=25)
        self.username_entry.grid(row=6, column=1, sticky='ew', padx=(10, 0))
        
        ttk.Label(main_frame, text="Email (optional):").grid(row=7, column=0, sticky='w', pady=(10, 0))
        self.email_entry = ttk.Entry(main_frame, width=25)
        self.email_entry.grid(row=7, column=1, sticky='ew', padx=(10, 0), pady=(10, 0))
        
        # Create user button
        ttk.Button(main_frame, text="Create User", 
                  command=self.create_new_user).grid(row=8, column=0, columnspan=2, pady=20)
        
        # Close button
        ttk.Button(main_frame, text="Cancel", 
                  command=self.close_login).grid(row=9, column=0, columnspan=2, pady=(10, 0))
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        self.login_window.columnconfigure(0, weight=1)
        self.login_window.rowconfigure(0, weight=1)
        
        # Wait for window to close
        self.login_window.wait_window()
        return self.current_user
    
    def populate_user_list(self):
        """Populate the user listbox with existing users"""
        self.user_listbox.delete(0, tk.END)
        users = self.db_manager.get_all_users()
        
        for user in users:
            last_login = user['last_login']
            if last_login:
                last_login_str = datetime.fromisoformat(last_login.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            else:
                last_login_str = "Never"
            
            display_text = f"{user['username']} (Last: {last_login_str})"
            self.user_listbox.insert(tk.END, display_text)
            # Store user data as a property of the listbox item
            self.user_listbox.insert(tk.END, "")  # Placeholder for user data
            self.user_listbox.delete(tk.END)  # Remove placeholder
        
        self.users_data = users  # Store for reference
    
    def select_existing_user(self):
        """Select an existing user from the list"""
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a user from the list.")
            return
        
        user_index = selection[0]
        if user_index < len(self.users_data):
            selected_user = self.users_data[user_index]
            self.db_manager.update_last_login(selected_user['user_id'])
            self.current_user = self.db_manager.get_user_by_username(selected_user['username'])
            self.close_login()
    
    def create_new_user(self):
        """Create a new user"""
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip() or None
        
        if not username:
            messagebox.showerror("Invalid Input", "Username is required.")
            return
        
        if len(username) < 3:
            messagebox.showerror("Invalid Input", "Username must be at least 3 characters long.")
            return
        
        try:
            user_id = self.db_manager.create_user(username, email)
            self.current_user = self.db_manager.get_user_by_username(username)
            messagebox.showinfo("Success", f"User '{username}' created successfully!")
            self.close_login()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def delete_user(self):
        """Delete selected user (with confirmation)"""
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a user to delete.")
            return
        
        user_index = selection[0]
        if user_index < len(self.users_data):
            user = self.users_data[user_index]
            
            # Confirmation dialog
            result = messagebox.askyesno(
                "Confirm Deletion", 
                f"Are you sure you want to delete user '{user['username']}'?\n\n"
                "This will permanently delete all their learning data and cannot be undone."
            )
            
            if result:
                # Note: Add actual deletion logic to DatabaseManager if needed
                messagebox.showinfo("Deletion", "User deletion not yet implemented for safety.")
                # self.db_manager.delete_user(user['user_id'])
                # self.populate_user_list()
    
    def close_login(self):
        """Close the login window"""
        if self.login_window:
            self.login_window.destroy()

class LearningSession:
    """Manages a single learning session"""
    
    def __init__(self, db_manager: DatabaseManager, user_id: str):
        self.db_manager = db_manager
        self.user_id = user_id
        self.session_id = None
        self.start_time = None
        self.current_paradigm = None
        self.paradigm_attempts = {}
        self.session_stats = {
            'total_attempts': 0,
            'correct_attempts': 0,
            'paradigms_practiced': set()
        }
    
    def start_session(self):
        """Start a new learning session"""
        self.session_id = self.db_manager.start_session(self.user_id)
        self.start_time = datetime.now()
        print(f"Learning session started: {self.session_id}")
    
    def end_session(self):
        """End the current learning session"""
        if not self.session_id:
            return
        
        # Calculate session summary
        session_duration = (datetime.now() - self.start_time).total_seconds()
        summary = {
            'duration_seconds': int(session_duration),
            'total_attempts': self.session_stats['total_attempts'],
            'correct_attempts': self.session_stats['correct_attempts'],
            'accuracy': (self.session_stats['correct_attempts'] / self.session_stats['total_attempts'] * 100) 
                       if self.session_stats['total_attempts'] > 0 else 0,
            'paradigms_practiced': list(self.session_stats['paradigms_practiced'])
        }
        
        self.db_manager.end_session(self.session_id, summary)
        
        # Update mastery scores for practiced paradigms
        for paradigm in self.session_stats['paradigms_practiced']:
            paradigm_type, paradigm_name = paradigm.split('|', 1)
            self.db_manager.update_mastery(self.user_id, paradigm_type, paradigm_name)
        
        print(f"Learning session ended: {self.session_id}")
        return summary
    
    def record_table_attempt(self, paradigm_type: str, paradigm_name: str, 
                           user_answers: Dict, correct_answers: Dict, 
                           time_taken: int = None):
        """Record an entire table attempt"""
        if not self.session_id:
            self.start_session()
        
        paradigm_key = f"{paradigm_type}|{paradigm_name}"
        self.session_stats['paradigms_practiced'].add(paradigm_key)
        
        # Record each field as a separate attempt
        for field, correct_answer in correct_answers.items():
            user_answer = user_answers.get(field, "").strip()
            is_correct = self.normalize_answer(user_answer) == self.normalize_answer(correct_answer)
            
            self.db_manager.record_attempt(
                self.session_id, paradigm_type, paradigm_name,
                field, user_answer, correct_answer, is_correct, time_taken
            )
            
            # Update session stats
            self.session_stats['total_attempts'] += 1
            if is_correct:
                self.session_stats['correct_attempts'] += 1
        
        return self.get_table_accuracy(user_answers, correct_answers)
    
    def normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison (remove accents, etc.)"""
        # This should match the normalization logic in the main app
        import unicodedata
        
        if not answer:
            return ""
        
        # Remove Greek diacritics
        nfd_text = unicodedata.normalize('NFD', answer.strip())
        diacritics_to_remove = [
            '\u0300', '\u0301', '\u0302', '\u0304', '\u0306', '\u0308',
            '\u0313', '\u0314', '\u0342', '\u0343', '\u0344', '\u0345'
        ]
        
        for diacritic in diacritics_to_remove:
            nfd_text = nfd_text.replace(diacritic, '')
        
        return unicodedata.normalize('NFC', nfd_text).lower()
    
    def get_table_accuracy(self, user_answers: Dict, correct_answers: Dict) -> float:
        """Calculate accuracy for a table attempt"""
        if not correct_answers:
            return 0.0
        
        correct_count = 0
        for field, correct_answer in correct_answers.items():
            user_answer = user_answers.get(field, "").strip()
            if self.normalize_answer(user_answer) == self.normalize_answer(correct_answer):
                correct_count += 1
        
        return (correct_count / len(correct_answers)) * 100
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        accuracy = (self.session_stats['correct_attempts'] / self.session_stats['total_attempts'] * 100) \
                  if self.session_stats['total_attempts'] > 0 else 0
        
        return {
            'total_attempts': self.session_stats['total_attempts'],
            'correct_attempts': self.session_stats['correct_attempts'],
            'accuracy': accuracy,
            'paradigms_practiced': len(self.session_stats['paradigms_practiced']),
            'session_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }

class ProgressTracker:
    """Tracks and displays user progress"""
    
    def __init__(self, parent_frame, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.parent_frame = parent_frame
        self.current_user = None
        self.progress_frame = None
        self.progress_vars = {}
        
    def create_progress_display(self):
        """Create a compact progress tracking UI"""
        if self.progress_frame:
            self.progress_frame.destroy()
        
        # Create a compact horizontal progress display
        self.progress_frame = ttk.Frame(self.parent_frame)
        self.progress_frame.grid(row=1, column=2, sticky='e', padx=(10, 0), pady=(0, 10))
        
        # Initialize progress variables with more compact display
        self.progress_vars = {
            'session_info': tk.StringVar(value="Learn Mode: 0/0 (0%) | 00:00"),
            'mastery_level': tk.StringVar(value="Mastery: --")
        }
        
        # Create compact labels in horizontal layout
        info_label = ttk.Label(self.progress_frame, textvariable=self.progress_vars['session_info'], 
                              font=('Arial', 9))
        info_label.grid(row=0, column=0, sticky='w')
        
        mastery_label = ttk.Label(self.progress_frame, textvariable=self.progress_vars['mastery_level'], 
                                 font=('Arial', 9))
        mastery_label.grid(row=1, column=0, sticky='w')
        
        # Analytics button (compact)
        ttk.Button(self.progress_frame, text="Analytics", 
                  command=self.show_analytics, width=8).grid(row=0, column=1, rowspan=2, padx=(10, 0))
    
    def set_user(self, user: Dict):
        """Set the current user for progress tracking"""
        self.current_user = user
        if self.progress_frame:
            self.update_display()
    
    def update_session_stats(self, session_stats: Dict):
        """Update session statistics display"""
        if not self.progress_vars:
            return
        
        # Update session info in compact format
        total = session_stats.get('total_attempts', 0)
        correct = session_stats.get('correct_attempts', 0)
        accuracy = session_stats.get('accuracy', 0)
        duration = session_stats.get('session_duration', 0)
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        self.progress_vars['session_info'].set(f"Learn Mode: {correct}/{total} ({accuracy:.1f}%) | {minutes:02d}:{seconds:02d}")
    
    def update_current_paradigm(self, paradigm_type: str, paradigm_name: str):
        """Update current paradigm and its mastery level"""
        if not self.progress_vars or not self.current_user:
            return
        
        # Get mastery for this paradigm
        mastery_data = self.db_manager.get_user_mastery(self.current_user['user_id'])
        paradigm_key = f"{paradigm_type}_{paradigm_name}"
        
        if paradigm_key in mastery_data:
            mastery = mastery_data[paradigm_key]
            accuracy = mastery['accuracy']
            total_attempts = mastery['total_attempts']
            
            self.progress_vars['mastery_level'].set(f"Mastery: {accuracy:.1f}% ({total_attempts} attempts)")
        else:
            self.progress_vars['mastery_level'].set("Mastery: New paradigm")
    
    def update_display(self):
        """Update the entire progress display"""
        if not self.current_user or not self.progress_vars:
            return
        
        # Reset to default values
        self.progress_vars['session_info'].set("Learn Mode: 0/0 (0%) | 00:00")
        self.progress_vars['mastery_level'].set("Mastery: --")
    
    def hide_progress_display(self):
        """Hide the progress display"""
        if self.progress_frame:
            self.progress_frame.destroy()
            self.progress_frame = None
    
    def show_analytics(self):
        """Show detailed analytics window"""
        if not self.current_user:
            return
        
        analytics_window = tk.Toplevel(self.parent_frame)
        analytics_window.title(f"Learning Analytics - {self.current_user['username']}")
        analytics_window.geometry("600x500")
        
        # Create notebook for different analytics tabs
        notebook = ttk.Notebook(analytics_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Mastery overview tab
        mastery_frame = ttk.Frame(notebook)
        notebook.add(mastery_frame, text="Mastery Overview")
        
        # Get user mastery data
        mastery_data = self.db_manager.get_user_mastery(self.current_user['user_id'])
        
        # Create treeview for mastery data
        mastery_tree = ttk.Treeview(mastery_frame, columns=('Accuracy', 'Attempts', 'Correct'), show='tree headings')
        mastery_tree.heading('#0', text='Paradigm')
        mastery_tree.heading('Accuracy', text='Accuracy %')
        mastery_tree.heading('Attempts', text='Total Attempts')
        mastery_tree.heading('Correct', text='Correct Attempts')
        
        for paradigm, data in mastery_data.items():
            mastery_tree.insert('', 'end', text=paradigm.replace('_', ' - '),
                              values=(f"{data['accuracy']:.1f}%", 
                                     data['total_attempts'], 
                                     data['correct_attempts']))
        
        mastery_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Weak areas tab
        weak_areas_frame = ttk.Frame(notebook)
        notebook.add(weak_areas_frame, text="Areas for Improvement")
        
        weak_areas = self.db_manager.get_weak_areas(self.current_user['user_id'])
        
        if weak_areas:
            weak_tree = ttk.Treeview(weak_areas_frame, columns=('Accuracy', 'Attempts'), show='tree headings')
            weak_tree.heading('#0', text='Paradigm')
            weak_tree.heading('Accuracy', text='Accuracy %')
            weak_tree.heading('Attempts', text='Attempts')
            
            for area in weak_areas:
                weak_tree.insert('', 'end', 
                               text=f"{area['paradigm_type']} - {area['paradigm_subtype'] or 'General'}",
                               values=(f"{area['accuracy']:.1f}%", area['total_attempts']))
            
            weak_tree.pack(fill='both', expand=True, padx=10, pady=10)
        else:
            ttk.Label(weak_areas_frame, text="No areas needing improvement found!\nKeep up the great work!", 
                     font=('Arial', 12), justify='center').pack(expand=True, pady=50)
