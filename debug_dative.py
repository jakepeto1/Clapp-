#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk
import json

# Quick test to see if dative entries are being created
def test_dative_creation():
    """Test if dative entries are properly created"""
    root = tk.Tk()
    root.title("Dative Test")
    root.geometry("600x400")
    
    # Create a simple frame
    frame = ttk.Frame(root)
    frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Test noun table creation similar to the main app
    entries = {}
    error_labels = {}
    
    # Configure grid
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=2) 
    frame.grid_columnconfigure(2, weight=2)
    
    # Headers
    ttk.Label(frame, text="", font=('Arial', 14, 'bold')).grid(row=0, column=0, padx=15, pady=15, sticky='e')
    ttk.Label(frame, text="Singular", font=('Arial', 14, 'bold')).grid(row=0, column=1, padx=15, pady=15)
    ttk.Label(frame, text="Plural", font=('Arial', 14, 'bold')).grid(row=0, column=2, padx=15, pady=15)
    
    # Create entries for all cases including Dative
    cases = ["Nominative", "Vocative", "Accusative", "Genitive", "Dative"]
    
    for i, case in enumerate(cases, 1):
        # Case label
        ttk.Label(frame, text=case, font=('Arial', 12, 'bold')).grid(row=i, column=0, padx=15, pady=10, sticky=tk.E)
        
        # Singular entry
        entry_sg = tk.Entry(frame, width=25, font=('Times New Roman', 14), relief='solid', borderwidth=1)
        entry_sg.grid(row=i, column=1, padx=15, pady=10, sticky='ew')
        entries[f"{case}_sg"] = entry_sg
        
        # Plural entry
        entry_pl = tk.Entry(frame, width=25, font=('Times New Roman', 14), relief='solid', borderwidth=1)
        entry_pl.grid(row=i, column=2, padx=15, pady=10, sticky='ew')
        entries[f"{case}_pl"] = entry_pl
    
    # Test if dative entries were created
    print("Entries created:")
    for key in entries:
        print(f"  {key}: {entries[key]}")
    
    print(f"\nDative_sg created: {'Dative_sg' in entries}")
    print(f"Dative_pl created: {'Dative_pl' in entries}")
    
    # Fill with test data from μούσα paradigm to verify
    with open('paradigms.json', 'r', encoding='utf-8') as f:
        paradigms = json.load(f)
    
    if 'mousa' in paradigms:
        mousa_data = paradigms['mousa']
        for key, entry in entries.items():
            if key in mousa_data:
                entry.insert(0, mousa_data[key])
                print(f"Filled {key} with: {mousa_data[key]}")
    
    root.mainloop()

if __name__ == "__main__":
    test_dative_creation()
