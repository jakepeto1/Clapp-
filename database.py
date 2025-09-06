import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

class DatabaseManager:
    """Manages SQLite database for Learn Mode functionality"""
    
    def __init__(self, db_path: str = "greek_grammar_learn.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            mastery_scores TEXT DEFAULT '{}'
        )
        ''')
        
        # Sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            summary TEXT DEFAULT '{}',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Attempts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            paradigm_type TEXT NOT NULL,
            paradigm_name TEXT NOT NULL,
            form_attempted TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            time_taken INTEGER,
            attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')
        
        # Mastery table for detailed tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mastery (
            mastery_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            paradigm_type TEXT NOT NULL,
            paradigm_subtype TEXT,
            accuracy REAL DEFAULT 0.0,
            total_attempts INTEGER DEFAULT 0,
            correct_attempts INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            UNIQUE(user_id, paradigm_type, paradigm_subtype)
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_session_id ON attempts (session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mastery_user_id ON mastery (user_id)')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username: str, email: str = None) -> str:
        """Create a new user and return user_id"""
        user_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO users (user_id, username, email, last_login)
            VALUES (?, ?, ?, ?)
            ''', (user_id, username, email, datetime.now()))
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT user_id, username, email, created_at, last_login, mastery_scores
        FROM users WHERE username = ?
        ''', (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'created_at': row[3],
                'last_login': row[4],
                'mastery_scores': json.loads(row[5]) if row[5] else {}
            }
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users for selection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT user_id, username, last_login
        FROM users ORDER BY last_login DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'user_id': row[0], 'username': row[1], 'last_login': row[2]} for row in rows]
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users SET last_login = ? WHERE user_id = ?
        ''', (datetime.now(), user_id))
        
        conn.commit()
        conn.close()
    
    def start_session(self, user_id: str) -> str:
        """Start a new learning session"""
        session_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO sessions (session_id, user_id)
        VALUES (?, ?)
        ''', (session_id, user_id))
        
        conn.commit()
        conn.close()
        return session_id
    
    def end_session(self, session_id: str, summary: Dict = None):
        """End a learning session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary_json = json.dumps(summary) if summary else '{}'
        cursor.execute('''
        UPDATE sessions 
        SET end_time = ?, summary = ?
        WHERE session_id = ?
        ''', (datetime.now(), summary_json, session_id))
        
        conn.commit()
        conn.close()
    
    def record_attempt(self, session_id: str, paradigm_type: str, paradigm_name: str, 
                      form_attempted: str, user_answer: str, correct_answer: str, 
                      is_correct: bool, time_taken: int = None) -> str:
        """Record an individual attempt"""
        attempt_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO attempts 
        (attempt_id, session_id, paradigm_type, paradigm_name, form_attempted, 
         user_answer, correct_answer, is_correct, time_taken)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (attempt_id, session_id, paradigm_type, paradigm_name, form_attempted,
              user_answer, correct_answer, is_correct, time_taken))
        
        conn.commit()
        conn.close()
        return attempt_id
    
    def update_mastery(self, user_id: str, paradigm_type: str, paradigm_subtype: str = None):
        """Update mastery scores based on recent attempts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate accuracy from recent attempts
        cursor.execute('''
        SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
        FROM attempts a
        JOIN sessions s ON a.session_id = s.session_id
        WHERE s.user_id = ? AND a.paradigm_type = ?
        AND (? IS NULL OR a.paradigm_name LIKE ?)
        ''', (user_id, paradigm_type, paradigm_subtype, f'%{paradigm_subtype}%' if paradigm_subtype else None))
        
        result = cursor.fetchone()
        total_attempts = result[0] if result[0] else 0
        correct_attempts = result[1] if result[1] else 0
        accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Insert or update mastery record
        mastery_id = str(uuid.uuid4())
        cursor.execute('''
        INSERT OR REPLACE INTO mastery
        (mastery_id, user_id, paradigm_type, paradigm_subtype, accuracy, total_attempts, correct_attempts, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mastery_id, user_id, paradigm_type, paradigm_subtype, accuracy, total_attempts, correct_attempts, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return accuracy
    
    def get_user_mastery(self, user_id: str) -> Dict:
        """Get mastery scores for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT paradigm_type, paradigm_subtype, accuracy, total_attempts, correct_attempts
        FROM mastery WHERE user_id = ?
        ORDER BY paradigm_type, paradigm_subtype
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        mastery_data = {}
        for row in rows:
            paradigm_type, subtype, accuracy, total, correct = row
            key = f"{paradigm_type}_{subtype}" if subtype else paradigm_type
            mastery_data[key] = {
                'accuracy': accuracy,
                'total_attempts': total,
                'correct_attempts': correct
            }
        
        return mastery_data
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get summary of a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute('''
        SELECT start_time, end_time, summary FROM sessions WHERE session_id = ?
        ''', (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            conn.close()
            return {}
        
        # Get attempt statistics
        cursor.execute('''
        SELECT paradigm_type, paradigm_name, COUNT(*) as total,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
        FROM attempts WHERE session_id = ?
        GROUP BY paradigm_type, paradigm_name
        ''', (session_id,))
        
        attempt_rows = cursor.fetchall()
        conn.close()
        
        paradigm_stats = {}
        for row in attempt_rows:
            paradigm_type, paradigm_name, total, correct = row
            paradigm_stats[f"{paradigm_type}_{paradigm_name}"] = {
                'total': total,
                'correct': correct,
                'accuracy': (correct / total * 100) if total > 0 else 0
            }
        
        return {
            'start_time': session_row[0],
            'end_time': session_row[1],
            'summary': json.loads(session_row[2]) if session_row[2] else {},
            'paradigm_stats': paradigm_stats
        }
    
    def get_weak_areas(self, user_id: str, threshold: float = 70.0) -> List[Dict]:
        """Get paradigms where user accuracy is below threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT paradigm_type, paradigm_subtype, accuracy, total_attempts
        FROM mastery 
        WHERE user_id = ? AND accuracy < ? AND total_attempts >= 5
        ORDER BY accuracy ASC
        ''', (user_id, threshold))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'paradigm_type': row[0], 'paradigm_subtype': row[1], 
                'accuracy': row[2], 'total_attempts': row[3]} for row in rows]
    
    def get_user_progress_over_time(self, user_id: str, days: int = 30) -> Dict:
        """Get user progress over specified number of days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DATE(a.attempt_timestamp) as attempt_date,
               COUNT(*) as total_attempts,
               SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END) as correct_attempts
        FROM attempts a
        JOIN sessions s ON a.session_id = s.session_id
        WHERE s.user_id = ? AND a.attempt_timestamp >= datetime('now', '-{} days')
        GROUP BY DATE(a.attempt_timestamp)
        ORDER BY attempt_date
        '''.format(days), (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        progress_data = {}
        for row in rows:
            date, total, correct = row
            progress_data[date] = {
                'total_attempts': total,
                'correct_attempts': correct,
                'accuracy': (correct / total * 100) if total > 0 else 0
            }
        
        return progress_data
