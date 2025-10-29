# Starred Tab Implementation Guide

## Overview
The Starred tab feature allows users to bookmark specific paradigms (nouns, adjectives, pronouns, and verb forms) for quick access and focused practice.

## Implementation Details

### 1. Starred Item Format

Starred items are stored as keys with the following formats:

- **Nouns/Adjectives/Pronouns**: `"Type:Mode"`
  - Example: `"Noun:First Declension (μουσα)"`
  - Example: `"Adjective:Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)"`

- **Verbs**: `"Verb:Mode:Voice:Tense:Mood"`
  - Example: `"Verb:Present Indicative Active - Release (λύω):Active:Present:Indicative"`
  - The extra fields allow precise verb form bookmarking

### 2. Display Map System

The `get_starred_display_map()` method creates a mapping between user-friendly display labels and internal item keys:

```python
{
    "λύω - Present Active Indicative": "Verb:Present Indicative Active - Release (λύω):Active:Present:Indicative",
    "First Declension (μουσα)": "Noun:First Declension (μουσα)"
}
```

This allows:
- Clean dropdown display (user-friendly labels)
- Robust item lookup (no string matching ambiguity)
- Proper handling of duplicate display names

### 3. Type Selection Flow

When user selects "Starred" from the type dropdown (`on_type_change`):

1. Retrieve all starred item display labels via `get_starred_display_items()`
2. Populate the mode dropdown with these labels
3. If items exist, select the first one; otherwise show "No starred items"
4. Call `reset_table()` to display the appropriate table

### 4. Mode Selection in Starred Tab

When user selects a starred item from the mode dropdown (`on_mode_change`):

1. **Get the item key**: Use `get_starred_display_map()` to map display label → item key
2. **Parse the key**: Split by `:` to extract type, mode, and (for verbs) voice/tense/mood
3. **Set internal state**: 
   - Temporarily set `type_var` to the real type (Noun, Verb, etc.)
   - Set `mode_var` to the mode string
   - For verbs: set `voice_var`, `tense_var`, `mood_var`
4. **Create table**: Call appropriate table builder (`create_verb_table()` or `create_declension_table()`)
5. **Update UI**: Call `update_word_display()` to refresh labels
6. **Restore navigation**: Set `type_var` back to "Starred" so navigation remains in Starred tab

### 5. Starring/Unstarring Logic

#### Starring (in normal tabs):
```python
def toggle_star(self):
    current_type = self.type_var.get()
    item_key = self.get_current_item_key()
    
    if current_type != "Starred":
        self.starred_items.add(item_key)
        self.save_starred_items()
        self.update_star_button()
```

#### Unstarring (in Starred tab):
```python
if current_type == "Starred":
    self.starred_items.remove(item_key)
    self.save_starred_items()
    
    # Get remaining items
    display_map = self.get_starred_display_map()
    remaining_displays = list(display_map.keys())
    
    if remaining_displays:
        # Update dropdown and select next item
        self.modes = remaining_displays
        self.mode_dropdown['values'] = self.modes
        self.mode_var.set(remaining_displays[0])
        self.on_mode_change(None)  # Trigger display update
    else:
        # No items left - switch to Noun tab
        self.type_var.set("Noun")
        self.on_type_change(None)
```

### 6. Key Helper Methods

#### `get_current_item_key()`
Returns the item key for the currently displayed paradigm:
- In Starred tab: looks up the display label in the display map
- In normal tabs: constructs the key from current type/mode/verb-form

#### `get_effective_type()`
Returns the real type of the current paradigm:
- In Starred tab: extracts type from the starred item key
- In normal tabs: returns `type_var` directly

#### `get_effective_type_from_item_key(item_key)`
Extracts the type (first component) from an item key.

### 7. Robustness Features

✅ **Always parse from key**: Never relies on stale state; always extracts fresh data from starred item keys

✅ **Prevent invalid states**: When last starred item is removed, automatically switches to Noun tab

✅ **Verb form precision**: Stores and restores exact voice/tense/mood combinations for verbs

✅ **Display map lookup**: Eliminates string-matching ambiguity in item selection

✅ **UI consistency**: Star button always reflects current starred state; type_var restored to "Starred" after table creation

### 8. User Experience Flow

#### Adding a starred item:
1. User navigates to a paradigm (e.g., Present Active Indicative λύω)
2. User clicks star button (☆ → ★)
3. Item is added to starred set and persisted
4. Star button turns gold

#### Viewing starred items:
1. User selects "Starred" from type dropdown
2. Dropdown shows all starred items with friendly labels
3. User selects an item (e.g., "λύω - Present Active Indicative")
4. Correct table is displayed with proper dropdowns set
5. Star button shows as starred (gold ★)

#### Removing a starred item:
1. User is in Starred tab viewing a starred item
2. User clicks star button (★)
3. Item is removed from starred set
4. Dropdown updates to show remaining items
5. Next available item is automatically selected and displayed
6. If no items remain, user is switched to Noun tab

### 9. Testing Checklist

- [ ] Star a noun, switch to Starred tab, verify noun table displays
- [ ] Star an adjective, switch to Starred tab, verify adjective table displays
- [ ] Star a verb form, switch to Starred tab, verify verb table with correct voice/tense/mood
- [ ] Unstar an item in Starred tab, verify next item is selected
- [ ] Unstar the last item in Starred tab, verify switch to Noun tab
- [ ] Star multiple verb forms of same verb, verify each displays correctly
- [ ] Close and reopen app, verify starred items persist

### 10. File Persistence

Starred items are saved to `starred_items.json` as a JSON array:

```json
[
    "Noun:First Declension (μουσα)",
    "Verb:Present Indicative Active - Release (λύω):Active:Present:Indicative",
    "Adjective:Three-termination Good (ἀγαθός, ἀγαθή, ἀγαθόν)"
]
```

Methods:
- `save_starred_items()`: Writes set to JSON file
- `load_starred_items()`: Loads set from JSON file on startup

## Summary

The refactored Starred tab implementation provides:
- Reliable item key parsing and lookup
- Correct table display for all paradigm types
- Smooth user experience when adding/removing items
- Robust state management and UI consistency
- Persistent storage across sessions
