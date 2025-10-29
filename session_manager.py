"""
Session Manager for Bellerophon Grammar Study Sessions

Tracks user progress, mastery, and session history for Greek grammar tables.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import os


class SessionManager:
    """Manages study session data and mastery tracking."""
    
    def __init__(self, db_path: str = "bellerophon_sessions.db"):
        """
        Initialize the session manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for tracking individual table mastery
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS table_mastery (
                table_id TEXT PRIMARY KEY,
                word_type TEXT NOT NULL,
                word TEXT NOT NULL,
                subtype TEXT,
                total_attempts INTEGER DEFAULT 0,
                correct_attempts INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                last_practiced TEXT,
                is_mastered INTEGER DEFAULT 0,
                mastery_date TEXT
            )
        """)
        
        # Table for tracking complete sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                num_tables INTEGER NOT NULL,
                word_types TEXT NOT NULL,
                focus_area TEXT NOT NULL,
                overall_accuracy REAL,
                completed INTEGER DEFAULT 0
            )
        """)
        
        # Table for tracking individual table results within sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                table_id TEXT NOT NULL,
                table_order INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                completed INTEGER DEFAULT 0,
                needs_review INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (table_id) REFERENCES table_mastery(table_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_table_id(self, word_type: str, word: str, subtype: Optional[str] = None) -> str:
        """
        Generate a unique ID for a table.
        
        Args:
            word_type: Type of word (noun, verb, adjective, pronoun)
            word: The actual word
            subtype: Optional subtype (e.g., verb tense/mood)
        
        Returns:
            Unique table identifier
        """
        if subtype:
            return f"{word_type}:{word}:{subtype}"
        return f"{word_type}:{word}"
    
    def record_table_attempt(self, table_id: str, word_type: str, word: str, 
                            accuracy: float, subtype: Optional[str] = None):
        """
        Record an attempt at completing a table.
        
        Args:
            table_id: Unique table identifier
            word_type: Type of word
            word: The actual word
            accuracy: Percentage correct (0.0 to 1.0)
            subtype: Optional subtype
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if table exists in mastery tracking
        cursor.execute("SELECT * FROM table_mastery WHERE table_id = ?", (table_id,))
        existing = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        if existing:
            # Update existing record
            total_attempts = existing[4] + 1
            correct_attempts = existing[5] + (1 if accuracy >= 0.9 else 0)
            success_rate = correct_attempts / total_attempts if total_attempts > 0 else 0.0
            
            # Check mastery criteria: 90%+ success rate, at least 3 correct completions
            is_mastered = 1 if success_rate >= 0.9 and correct_attempts >= 3 else 0
            mastery_date = now if is_mastered and existing[8] == 0 else existing[9]
            
            cursor.execute("""
                UPDATE table_mastery 
                SET total_attempts = ?, correct_attempts = ?, success_rate = ?,
                    last_practiced = ?, is_mastered = ?, mastery_date = ?
                WHERE table_id = ?
            """, (total_attempts, correct_attempts, success_rate, now, 
                  is_mastered, mastery_date, table_id))
        else:
            # Insert new record
            correct_attempts = 1 if accuracy >= 0.9 else 0
            success_rate = accuracy
            is_mastered = 0  # Can't be mastered on first attempt
            
            cursor.execute("""
                INSERT INTO table_mastery 
                (table_id, word_type, word, subtype, total_attempts, correct_attempts,
                 success_rate, last_practiced, is_mastered, mastery_date)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 0, NULL)
            """, (table_id, word_type, word, subtype, correct_attempts, 
                  success_rate, now))
        
        conn.commit()
        conn.close()
    
    def get_table_stats(self, table_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific table.
        
        Returns:
            Dictionary with table statistics or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM table_mastery WHERE table_id = ?", (table_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'table_id': row[0],
                'word_type': row[1],
                'word': row[2],
                'subtype': row[3],
                'total_attempts': row[4],
                'correct_attempts': row[5],
                'success_rate': row[6],
                'last_practiced': row[7],
                'is_mastered': bool(row[8]),
                'mastery_date': row[9]
            }
        return None
    
    def get_weak_tables(self, limit: int = 10) -> List[str]:
        """
        Get table IDs with low mastery (for focused practice).
        
        Args:
            limit: Maximum number of tables to return
        
        Returns:
            List of table IDs sorted by success rate (lowest first)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_id FROM table_mastery 
            WHERE is_mastered = 0 AND total_attempts > 0
            ORDER BY success_rate ASC, total_attempts DESC
            LIMIT ?
        """, (limit,))
        
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_untested_tables(self, all_table_ids: List[str], limit: int = 10) -> List[str]:
        """
        Get tables that have never been attempted.
        
        Args:
            all_table_ids: List of all possible table IDs in the app
            limit: Maximum number of tables to return
        
        Returns:
            List of untested table IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all tested table IDs
        cursor.execute("SELECT table_id FROM table_mastery")
        tested = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        # Return untested tables
        untested = [tid for tid in all_table_ids if tid not in tested]
        return untested[:limit]
    
    def get_tables_for_spaced_repetition(self, all_table_ids: List[str], 
                                         days_threshold: int = 2,
                                         limit: int = 10) -> List[str]:
        """
        Get tables that haven't been practiced recently (spaced repetition).
        
        Args:
            all_table_ids: List of all possible table IDs
            days_threshold: Number of days since last practice
            limit: Maximum number of tables to return
        
        Returns:
            List of table IDs not practiced in the threshold period
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        cursor.execute("""
            SELECT table_id FROM table_mastery 
            WHERE last_practiced < ? OR last_practiced IS NULL
            ORDER BY last_practiced ASC NULLS FIRST
            LIMIT ?
        """, (threshold_date, limit))
        
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def create_session(self, num_tables: int, word_types: List[str], 
                      focus_area: str) -> int:
        """
        Create a new study session.
        
        Returns:
            Session ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        word_types_str = json.dumps(word_types)
        
        cursor.execute("""
            INSERT INTO sessions 
            (start_time, num_tables, word_types, focus_area, completed)
            VALUES (?, ?, ?, ?, 0)
        """, (now, num_tables, word_types_str, focus_area))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def add_session_table(self, session_id: int, table_id: str, table_order: int):
        """Add a table to a session's queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO session_tables 
            (session_id, table_id, table_order, completed)
            VALUES (?, ?, ?, 0)
        """, (session_id, table_id, table_order))
        
        conn.commit()
        conn.close()
    
    def update_session_table(self, session_id: int, table_id: str, 
                            attempts: int, accuracy: float, needs_review: bool):
        """Update results for a table within a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE session_tables 
            SET attempts = ?, accuracy = ?, completed = 1, needs_review = ?
            WHERE session_id = ? AND table_id = ?
        """, (attempts, accuracy, 1 if needs_review else 0, session_id, table_id))
        
        conn.commit()
        conn.close()
    
    def complete_session(self, session_id: int, overall_accuracy: float):
        """Mark a session as completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE sessions 
            SET end_time = ?, overall_accuracy = ?, completed = 1
            WHERE session_id = ?
        """, (now, overall_accuracy, session_id))
        
        conn.commit()
        conn.close()
    
    def get_session_results(self, session_id: int) -> Dict:
        """Get complete results for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session_row = cursor.fetchone()
        
        # Get table results
        cursor.execute("""
            SELECT st.table_id, st.table_order, st.attempts, st.accuracy, 
                   st.needs_review, tm.word_type, tm.word, tm.subtype
            FROM session_tables st
            JOIN table_mastery tm ON st.table_id = tm.table_id
            WHERE st.session_id = ?
            ORDER BY st.table_order
        """, (session_id,))
        
        table_results = []
        for row in cursor.fetchall():
            table_results.append({
                'table_id': row[0],
                'order': row[1],
                'attempts': row[2],
                'accuracy': row[3],
                'needs_review': bool(row[4]),
                'word_type': row[5],
                'word': row[6],
                'subtype': row[7]
            })
        
        conn.close()
        
        return {
            'session_id': session_row[0],
            'start_time': session_row[1],
            'end_time': session_row[2],
            'num_tables': session_row[3],
            'word_types': json.loads(session_row[4]),
            'focus_area': session_row[5],
            'overall_accuracy': session_row[6],
            'completed': bool(session_row[7]),
            'tables': table_results
        }
    
    def get_mastery_summary(self) -> Dict:
        """Get overall mastery statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM table_mastery WHERE is_mastered = 1")
        mastered_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM table_mastery")
        total_attempted = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(success_rate) FROM table_mastery")
        avg_success = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            'mastered_count': mastered_count,
            'total_attempted': total_attempted,
            'average_success_rate': avg_success
        }
