# Ancient Greek Grammar Study Application

## Overview

This is a comprehensive interactive learning application for studying Ancient Greek grammar, morphology, and paradigms. Built with Python and Tkinter, it provides an intuitive interface for practicing declensions, conjugations, and other grammatical forms of Ancient Greek.

## Features

### Core Functionality

**Multi-Category Grammar Practice**
- **Nouns**: Practice all major declension patterns (1st, 2nd, 3rd declensions)
- **Adjectives**: Study adjectival declensions with proper gender agreement
- **Pronouns**: Learn demonstrative, personal, and relative pronouns with gendered table layouts
- **Verbs**: Master verbal conjugations across all tenses, moods, and voices

**Interactive Learning Interface**
- Clean, organized table layouts for entering grammatical forms
- Real-time answer checking with visual feedback (green for correct, red for incorrect)
- "Reveal Answers" functionality to see correct forms
- "Check Answers" to validate your entries
- Smart navigation between fields using Enter, arrow keys, and Tab

### Advanced Verb Features

**Comprehensive Verbal System**
- **Tenses**: Present, Imperfect, Aorist, Future, Perfect, Pluperfect
- **Moods**: Indicative, Subjunctive, Optative, Imperative, Infinitive
- **Voices**: Active, Middle, Passive (where applicable)
- **Special handling for irregular verbs**: δίδωμι, τίθημι, ἵστημι, ἵημι, οἶδα, φημί, εἰμί

**Intelligent Stem System**
- Context-aware stem extraction for irregular verbs
- Special handling for verbs with different singular/plural stems (φημί: φη/φα, οἶδα: οἰ/ἰσ)
- Automatic stem prefilling option with toggle control
- Sophisticated parsing of root aorist forms and mi-verb paradigms

**Dynamic Table Layouts**
- **Finite Verbs**: Person × Number grid (1st/2nd/3rd person, Singular/Plural)
- **Infinitives**: Simplified Tense × Voice layout (no person/number distinctions)
- **Context-sensitive form availability**: Only shows valid tense/mood/voice combinations

### Navigation and User Experience

**Smart Navigation System**
- **Sequential Navigation**: Move through paradigms in logical order
- **Random Navigation**: "Randomize Next" toggle for varied practice
- **Hierarchical Progression**: Voice → Tense → Mood → Verb for systematic study
- **Special Infinitive Handling**: Skips voice navigation since all voices shown simultaneously

**User Interface Enhancements**
- **Prefill Stems Toggle**: Optional automatic stem insertion for faster practice
- **Randomize Next Toggle**: Enables random table selection for varied learning
- **Error Indicators**: Visual feedback with clear error marking
- **Responsive Layout**: Adapts table structure based on grammatical category

### Technical Features

**Data-Driven Architecture**
- **paradigms.json**: Comprehensive database of Greek morphological forms
- **Accurate Paradigms**: Corrected mi-verb forms with proper root aorist patterns
- **Flexible Schema**: Supports various grammatical categories and irregular forms

**Greek Text Support**
- **Unicode Compatibility**: Full support for polytonic Greek text
- **Special Character Input**: Automated breathing mark and accent insertion
- **Proper Font Rendering**: Clear display of Ancient Greek characters

## File Structure

```
greek_grammar.py     # Main application with GUI and learning logic
paradigms.json       # Complete database of Greek grammatical forms
test_*.py           # Various test files for functionality validation
debug_*.py          # Debugging utilities for specific features
check_*.py          # Verification scripts for paradigm accuracy
```

## Usage Instructions

### Getting Started
1. Run `python greek_grammar.py` to launch the application
2. Select a grammatical category (Noun, Adjective, Pronoun, or Verb)
3. Choose a specific paradigm from the dropdown menu
4. For verbs, select tense, voice, and mood combinations

### Study Workflow
1. **Practice**: Enter forms in the table fields
2. **Check**: Use "Check Answers" to validate entries
3. **Learn**: Use "Reveal Answers" to see correct forms
4. **Navigate**: Use "Next" to move to the next paradigm
5. **Randomize**: Enable "Randomize Next" for varied practice

### Keyboard Navigation
- **Enter**: Move to next field (only if current entry is correct)
- **Arrow Keys**: Navigate between cases/persons
- **Tab**: Move between any fields
- **Special Characters**: Type vowel + `]` for rough breathing, `[` for smooth breathing, `{` for iota subscript

## Educational Value

### Systematic Learning
- **Progressive Difficulty**: Start with simple nouns, advance to complex verbal paradigms
- **Comprehensive Coverage**: All major grammatical categories and irregular forms
- **Contextual Learning**: Understand forms within their grammatical contexts

### Advanced Features for Serious Study
- **Mi-Verbs**: Specialized handling for δίδωμι, τίθημι, ἵστημι, ἵημι with correct paradigms
- **Irregular Verbs**: Sophisticated logic for οἶδα, φημί, εἰμί with proper stem variations
- **Morphological Accuracy**: Based on standard grammars with verified paradigms
- **Comprehensive Voice System**: Proper handling of deponent and defective verbs

### Assessment and Progress
- **Immediate Feedback**: Real-time validation of entries
- **Error Tracking**: Visual indicators help identify problem areas
- **Flexible Practice**: Both guided and random practice modes
- **Answer Revelation**: Learn from mistakes with correct form display

## Technical Requirements

- **Python 3.x** with Tkinter (usually included)
- **Operating System**: Windows, macOS, or Linux
- **Display**: Support for Unicode Greek characters
- **Memory**: Minimal requirements (paradigms.json ~2MB)

## Recent Enhancements

### Version History Highlights
- **Paradigm Accuracy**: Corrected mi-verb conjugations with proper root aorist forms
- **Advanced Stems**: Context-aware stem extraction for irregular verbs
- **UI Improvements**: Added randomize toggle and enhanced navigation
- **Table Layouts**: Proper infinitive vs. finite verb formatting
- **Article Handling**: Moved from noun to pronoun section with gendered layout
- **Navigation Logic**: Fixed infinitive table formatting in random navigation

This application represents a sophisticated tool for Ancient Greek language learning, combining traditional grammatical study with modern interactive technology to provide an effective and engaging learning experience.
