from typing import List, Dict, Any, Optional
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import csv
from io import StringIO

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            # Create transcripts table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    ai_summary TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create transcript categories table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcript_categories (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT REFERENCES transcripts(video_id),
                    category_type TEXT NOT NULL,
                    categories TEXT[] NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create personal stories table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS personal_stories (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT REFERENCES transcripts(video_id),
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()

    def insert_transcript(self, video_id: str, title: str, transcript: str) -> Optional[str]:
        """Insert a new transcript into the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO transcripts (video_id, title, transcript)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (video_id) DO UPDATE
                    SET title = EXCLUDED.title,
                        transcript = EXCLUDED.transcript,
                        created_at = CURRENT_TIMESTAMP
                    RETURNING video_id
                """, (video_id, title, transcript))
                self.conn.commit()
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error inserting transcript: {str(e)}")
            self.conn.rollback()
            return None

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get a single transcript by video_id."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transcripts WHERE video_id = %s", (video_id,))
            return cur.fetchone()

    def get_categories(self, video_id: str) -> Dict[str, list]:
        """Get categories for a transcript."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT category_type, categories 
                FROM transcript_categories 
                WHERE video_id = %s
            """, (video_id,))
            result = cur.fetchall()
            
            categories = {
                'christian_life': [],
                'church_ministry': [],
                'theology': []
            }
            
            for row in result:
                if row['category_type'] in categories:
                    categories[row['category_type']] = row['categories']
            
            return categories

    def update_categories(self, video_id: str, categories: Dict[str, list]) -> bool:
        """Update categories for a transcript."""
        try:
            with self.conn.cursor() as cur:
                # First, remove existing categories
                cur.execute("DELETE FROM transcript_categories WHERE video_id = %s", (video_id,))
                
                # Insert new categories
                for category_type, category_list in categories.items():
                    if category_list:  # Only insert if there are categories
                        cur.execute("""
                            INSERT INTO transcript_categories (video_id, category_type, categories)
                            VALUES (%s, %s, %s)
                        """, (video_id, category_type, category_list))
                
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error updating categories: {str(e)}")
            self.conn.rollback()
            return False

    def video_exists(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Check if a video exists and return its details."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, title FROM transcripts WHERE video_id = %s", (video_id,))
            return cur.fetchone()

    def get_all_transcripts(self) -> List[Dict[str, Any]]:
        """Get all transcripts."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM transcripts ORDER BY created_at DESC")
            return cur.fetchall()

    def search_transcripts(self, query: str) -> List[Dict[str, Any]]:
        """Search transcripts using full-text search."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    video_id,
                    title,
                    ts_headline(
                        transcript,
                        plainto_tsquery(%s),
                        'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20'
                    ) as highlight
                FROM transcripts
                WHERE transcript_tsvector @@ plainto_tsquery(%s)
                ORDER BY ts_rank(transcript_tsvector, plainto_tsquery(%s)) DESC
            """, (query, query, query))
            return cur.fetchall()

    def export_transcripts(self, format: str = "json") -> str:
        """Export all transcripts in the specified format."""
        transcripts = self.get_all_transcripts()
        
        if format == "json":
            return json.dumps(transcripts, default=str)
        elif format == "csv":
            output = StringIO()
            if transcripts:
                writer = csv.DictWriter(output, fieldnames=transcripts[0].keys())
                writer.writeheader()
                for t in transcripts:
                    writer.writerow({k: str(v) for k, v in t.items()})
            return output.getvalue()
        else:  # txt format
            return "\n\n".join([
                f"Title: {t['title']}\nVideo ID: {t['video_id']}\nTranscript:\n{t['transcript']}"
                for t in transcripts
            ])

    def update_transcript_summary(self, video_id: str, summary: str) -> bool:
        """Update the AI summary for a transcript."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE transcripts 
                    SET ai_summary = %s 
                    WHERE video_id = %s
                """, (summary, video_id))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error updating summary: {str(e)}")
            self.conn.rollback()
            return False

    def get_personal_stories(self, video_id: str) -> List[Dict[str, Any]]:
        """Get personal stories for a transcript."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM personal_stories 
                WHERE video_id = %s 
                ORDER BY created_at DESC
            """, (video_id,))
            return cur.fetchall()

    def update_personal_stories(self, video_id: str, stories: List[Dict[str, str]]) -> bool:
        """Update personal stories for a transcript."""
        try:
            with self.conn.cursor() as cur:
                # First, remove existing stories
                cur.execute("DELETE FROM personal_stories WHERE video_id = %s", (video_id,))
                
                # Insert new stories
                for story in stories:
                    cur.execute("""
                        INSERT INTO personal_stories (video_id, title, summary, message)
                        VALUES (%s, %s, %s, %s)
                    """, (video_id, story['title'], story['summary'], story['message']))
                
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Error updating personal stories: {str(e)}")
            self.conn.rollback()
            return False
