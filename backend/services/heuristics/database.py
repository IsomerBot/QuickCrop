"""
SQLite database management for heuristics system.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import threading

class HeuristicsDB:
    """Manages SQLite database for heuristics parameters and audit trail."""
    
    def __init__(self, db_path: str = "data/model/heuristics.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._local = threading.local()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database schema
        self._init_database()
    
    @property
    def connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self.connection
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def _init_database(self):
        """Initialize database schema."""
        with self.transaction() as cursor:
            # Create params table for EMA parameters
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS params (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aspect_class TEXT NOT NULL,
                    zoom_level TEXT NOT NULL,
                    parameter_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    sample_count INTEGER DEFAULT 0,
                    alpha REAL DEFAULT 0.1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(aspect_class, zoom_level, parameter_name)
                )
            """)
            
            # Create samples table for audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT NOT NULL,
                    original_dimensions TEXT NOT NULL,
                    face_detected BOOLEAN NOT NULL,
                    pose_detected BOOLEAN NOT NULL,
                    aspect_class TEXT NOT NULL,
                    zoom_level TEXT NOT NULL,
                    initial_crop TEXT NOT NULL,
                    final_crop TEXT NOT NULL,
                    adjustment_delta TEXT NOT NULL,
                    features TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_params_lookup 
                ON params(aspect_class, zoom_level)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_samples_image 
                ON samples(image_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_samples_aspect_zoom 
                ON samples(aspect_class, zoom_level)
            """)
    
    def get_ema_parameters(
        self, 
        aspect_class: str, 
        zoom_level: str
    ) -> Dict[str, float]:
        """Get EMA parameters for specific aspect class and zoom level."""
        with self.transaction() as cursor:
            cursor.execute("""
                SELECT parameter_name, value 
                FROM params 
                WHERE aspect_class = ? AND zoom_level = ?
            """, (aspect_class, zoom_level))
            
            rows = cursor.fetchall()
            return {row['parameter_name']: row['value'] for row in rows}
    
    def update_ema_parameter(
        self,
        aspect_class: str,
        zoom_level: str,
        parameter_name: str,
        new_value: float,
        alpha: float = 0.1
    ) -> None:
        """Update EMA parameter using exponential moving average."""
        with self.transaction() as cursor:
            # Check if parameter exists
            cursor.execute("""
                SELECT value, sample_count 
                FROM params 
                WHERE aspect_class = ? AND zoom_level = ? AND parameter_name = ?
            """, (aspect_class, zoom_level, parameter_name))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing parameter
                old_value = row['value']
                sample_count = row['sample_count']
                
                # Calculate EMA
                ema_value = (1 - alpha) * old_value + alpha * new_value
                
                cursor.execute("""
                    UPDATE params 
                    SET value = ?, sample_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE aspect_class = ? AND zoom_level = ? AND parameter_name = ?
                """, (
                    ema_value, 
                    sample_count + 1,
                    aspect_class, 
                    zoom_level, 
                    parameter_name
                ))
            else:
                # Insert new parameter
                cursor.execute("""
                    INSERT INTO params (
                        aspect_class, zoom_level, parameter_name, value, sample_count, alpha
                    ) VALUES (?, ?, ?, ?, 1, ?)
                """, (aspect_class, zoom_level, parameter_name, new_value, alpha))
    
    def add_sample(
        self,
        image_hash: str,
        original_dimensions: Tuple[int, int],
        face_detected: bool,
        pose_detected: bool,
        aspect_class: str,
        zoom_level: str,
        initial_crop: Dict[str, int],
        final_crop: Dict[str, int],
        features: Dict[str, Any]
    ) -> None:
        """Add a sample to the audit trail."""
        with self.transaction() as cursor:
            # Calculate adjustment delta
            adjustment_delta = {
                'x': final_crop['x'] - initial_crop['x'],
                'y': final_crop['y'] - initial_crop['y'],
                'width': final_crop['width'] - initial_crop['width'],
                'height': final_crop['height'] - initial_crop['height']
            }
            
            cursor.execute("""
                INSERT INTO samples (
                    image_hash, original_dimensions, face_detected, pose_detected,
                    aspect_class, zoom_level, initial_crop, final_crop,
                    adjustment_delta, features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image_hash,
                json.dumps(original_dimensions),
                face_detected,
                pose_detected,
                aspect_class,
                zoom_level,
                json.dumps(initial_crop),
                json.dumps(final_crop),
                json.dumps(adjustment_delta),
                json.dumps(features)
            ))
    
    def get_samples(
        self,
        aspect_class: Optional[str] = None,
        zoom_level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve samples from audit trail."""
        with self.transaction() as cursor:
            query = "SELECT * FROM samples WHERE 1=1"
            params = []
            
            if aspect_class:
                query += " AND aspect_class = ?"
                params.append(aspect_class)
            
            if zoom_level:
                query += " AND zoom_level = ?"
                params.append(zoom_level)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            samples = []
            for row in rows:
                sample = dict(row)
                # Parse JSON fields
                sample['original_dimensions'] = json.loads(sample['original_dimensions'])
                sample['initial_crop'] = json.loads(sample['initial_crop'])
                sample['final_crop'] = json.loads(sample['final_crop'])
                sample['adjustment_delta'] = json.loads(sample['adjustment_delta'])
                sample['features'] = json.loads(sample['features'])
                samples.append(sample)
            
            return samples
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.transaction() as cursor:
            # Count parameters
            cursor.execute("SELECT COUNT(*) as count FROM params")
            param_count = cursor.fetchone()['count']
            
            # Count samples
            cursor.execute("SELECT COUNT(*) as count FROM samples")
            sample_count = cursor.fetchone()['count']
            
            # Get aspect class distribution
            cursor.execute("""
                SELECT aspect_class, COUNT(*) as count 
                FROM samples 
                GROUP BY aspect_class
            """)
            aspect_distribution = {
                row['aspect_class']: row['count'] 
                for row in cursor.fetchall()
            }
            
            # Get zoom level distribution
            cursor.execute("""
                SELECT zoom_level, COUNT(*) as count 
                FROM samples 
                GROUP BY zoom_level
            """)
            zoom_distribution = {
                row['zoom_level']: row['count'] 
                for row in cursor.fetchall()
            }
            
            return {
                'parameter_count': param_count,
                'sample_count': sample_count,
                'aspect_distribution': aspect_distribution,
                'zoom_distribution': zoom_distribution
            }
    
    def cleanup_old_samples(self, days_to_keep: int = 30) -> int:
        """Clean up old samples from audit trail."""
        with self.transaction() as cursor:
            cursor.execute("""
                DELETE FROM samples 
                WHERE julianday('now') - julianday(created_at) > ?
            """, (days_to_keep,))
            
            return cursor.rowcount
    
    def export_params(self) -> Dict[str, Any]:
        """Export all parameters for backup."""
        with self.transaction() as cursor:
            cursor.execute("""
                SELECT * FROM params 
                ORDER BY aspect_class, zoom_level, parameter_name
            """)
            
            params = []
            for row in cursor.fetchall():
                params.append(dict(row))
            
            return {
                'version': '1.0',
                'exported_at': datetime.utcnow().isoformat(),
                'parameters': params
            }
    
    def import_params(self, data: Dict[str, Any]) -> None:
        """Import parameters from backup."""
        with self.transaction() as cursor:
            for param in data['parameters']:
                cursor.execute("""
                    INSERT OR REPLACE INTO params (
                        aspect_class, zoom_level, parameter_name, value, 
                        sample_count, alpha, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    param['aspect_class'],
                    param['zoom_level'],
                    param['parameter_name'],
                    param['value'],
                    param.get('sample_count', 0),
                    param.get('alpha', 0.1),
                    param.get('created_at', datetime.utcnow().isoformat()),
                    param.get('updated_at', datetime.utcnow().isoformat())
                ))
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')