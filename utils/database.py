import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
        except KeyError:
            self.conn = psycopg2.connect(
                dbname=os.environ['PGDATABASE'],
                user=os.environ['PGUSER'],
                password=os.environ['PGPASSWORD'],
                host=os.environ['PGHOST'],
                port=os.environ['PGPORT']
            )
        self.setup_database()

    def setup_database(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id SERIAL PRIMARY KEY,
                    video_id VARCHAR(20) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_transcript_search 
                ON transcripts USING gin(to_tsvector('english', transcript));
            """)
            self.conn.commit()

    def store_transcript(self, video_id: str, title: str, transcript: str):
        """Store a video transcript in the database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO transcripts (video_id, title, transcript)
                VALUES (%s, %s, %s)
                ON CONFLICT (video_id) DO UPDATE
                SET transcript = EXCLUDED.transcript,
                    title = EXCLUDED.title
            """, (video_id, title, transcript))
            self.conn.commit()

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
