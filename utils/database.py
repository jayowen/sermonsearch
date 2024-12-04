import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
import time

class Database:
    def __init__(self):
        """Initialize database connection with retry logic"""
        self.conn = None
        try:
            self._connect()
            self.setup_database()
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
            raise
        
    def _connect(self):
        """Establish database connection with robust error handling"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Basic connection parameters
                conn_params = {
                    'application_name': 'youtube_transcript_processor',
                    'connect_timeout': 10,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5
                }
                
                # Get database URL from environment
                database_url = os.environ.get('DATABASE_URL')
                if not database_url:
                    raise ValueError("DATABASE_URL environment variable is not set")
                
                # Establish connection using the database URL
                self.conn = psycopg2.connect(database_url, **conn_params)
                
                # Set session parameters
                with self.conn.cursor() as cur:
                    cur.execute("SET SESSION client_min_messages TO error;")
                    cur.execute("SET search_path TO public;")
                    cur.execute('SELECT 1')
                self.conn.commit()
                print("Database connection established successfully")
                return
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    print(f"All connection attempts failed. Last error: {str(e)}")
                    raise

    def setup_database(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id SERIAL PRIMARY KEY,
                    video_id VARCHAR(20) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    ai_summary TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Add ai_summary column if it doesn't exist
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'transcripts' AND column_name = 'ai_summary'
                    ) THEN
                        ALTER TABLE transcripts ADD COLUMN ai_summary TEXT;
                    END IF;
                END $$;
                
                CREATE INDEX IF NOT EXISTS idx_transcript_search 
                ON transcripts USING gin(to_tsvector('english', transcript));
            """)
            self.conn.commit()

    def store_transcript(self, video_id: str, title: str, transcript: str, ai_summary: str = None) -> None:
        """Store a transcript and its AI summary in the database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transcripts (video_id, title, transcript, ai_summary)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (video_id) DO UPDATE
                SET transcript = EXCLUDED.transcript,
                    title = EXCLUDED.title,
                    ai_summary = EXCLUDED.ai_summary;
            """, (video_id, title, transcript, ai_summary))
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
    def video_exists(self, video_id: str) -> Dict[str, Any]:
        """Check if a video exists in the database and return its info if it does."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title FROM transcripts WHERE video_id = %s", (video_id,))
            return cur.fetchone()

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get a single transcript by video_id."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transcripts WHERE video_id = %s", (video_id,))
            return cur.fetchone()

