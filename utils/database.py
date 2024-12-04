import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
import time

class Database:
    def __init__(self):
        """Initialize database connection with retry logic"""
        self.conn = None
        self._connect()
        self.setup_database()
        
    def _connect(self):
        """Establish database connection with retries"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # First try with connection parameters
                self.conn = psycopg2.connect(
                    dbname=os.environ.get('PGDATABASE'),
                    user=os.environ.get('PGUSER'),
                    password=os.environ.get('PGPASSWORD'),
                    host=os.environ.get('PGHOST'),
                    port=os.environ.get('PGPORT'),
                    connect_timeout=10,
                    options="-c search_path=public -c statement_timeout=30000",
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
                return
            except Exception as e:
                try:
                    # Fallback to URL if parameters fail
                    self.conn = psycopg2.connect(
                        os.environ.get('DATABASE_URL'),
                        connect_timeout=10
                    )
                    return
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise Exception(f"Failed to connect to database after {max_retries} attempts") from e
                    time.sleep(1)  # Wait before retrying

    def setup_database(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id SERIAL PRIMARY KEY,
                    video_id VARCHAR(20) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_transcript_search 
                ON transcripts USING gin(to_tsvector('english', transcript));
            """)
            self.conn.commit()

    def store_transcript(self, video_id: str, title: str, transcript: str):
        """Store a transcript in the database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transcripts (video_id, title, transcript)
                VALUES (%s, %s, %s)
                ON CONFLICT (video_id) DO UPDATE
                SET transcript = EXCLUDED.transcript,
                    title = EXCLUDED.title
            """, (video_id, title, transcript))
            self.conn.commit()

    def export_transcripts(self, format: str = 'json') -> str:
        """Export all transcripts in the specified format (json, csv, or txt)."""
        transcripts = self.get_all_transcripts()
        if not transcripts:
            return ""
            
        if format == 'json':
            import json
            return json.dumps([{
                'video_id': t['video_id'],
                'title': t['title'],
                'transcript': t['transcript'],
                'created_at': t['created_at'].isoformat()
            } for t in transcripts], indent=2)
            
        elif format == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['video_id', 'title', 'transcript', 'created_at'])
            for t in transcripts:
                writer.writerow([
                    t['video_id'],
                    t['title'],
                    t['transcript'],
                    t['created_at'].isoformat()
                ])
            return output.getvalue()
            
        elif format == 'txt':
            lines = []
            for t in transcripts:
                lines.extend([
                    f"Title: {t['title']}",
                    f"Video ID: {t['video_id']}",
                    f"Created: {t['created_at'].isoformat()}",
                    "Transcript:",
                    t['transcript'],
                    "-" * 80,
                    ""
                ])
            return "\n".join(lines)
            
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def search_transcripts(self, query: str) -> List[Dict[str, Any]]:
        """Search transcripts using full-text search."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, video_id, title, transcript,
                       ts_headline('english', transcript, plainto_tsquery(%s)) as highlight
                FROM transcripts
                WHERE to_tsvector('english', transcript) @@ plainto_tsquery(%s)
                ORDER BY ts_rank(to_tsvector('english', transcript), plainto_tsquery(%s)) DESC
            """, (query, query, query))
            return cur.fetchall()

    def get_all_transcripts(self) -> List[Dict[str, Any]]:
        """Retrieve all stored transcripts."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transcripts ORDER BY created_at DESC")
            return cur.fetchall()
