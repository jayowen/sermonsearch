from typing import List, Dict, Any, Optional
import os
from supabase import create_client, Client
import json
from io import StringIO
import csv

class Database:
    def __init__(self):
        # Get credentials from environment variables
        self.supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
        self.supabase_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "").strip()
        
        # Validate credentials
        if not self.supabase_url:
            print("Error: NEXT_PUBLIC_SUPABASE_URL is missing or empty")
            raise ValueError("Missing NEXT_PUBLIC_SUPABASE_URL")
        if not self.supabase_key:
            print("Error: NEXT_PUBLIC_SUPABASE_ANON_KEY is missing or empty")
            raise ValueError("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY")
            
        try:
            # Log connection details (safely)
            url_prefix = self.supabase_url.split('.')[0] if self.supabase_url else 'None'
            print(f"Initializing Supabase client with URL prefix: {url_prefix}...")
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            
            # Test connection by trying to fetch one row from transcripts
            print("Testing Supabase connection with a sample query...")
            test_result = self.supabase.table('transcripts').select('*').limit(1).execute()
            print(f"Connection test result: {test_result.data if hasattr(test_result, 'data') else 'No data attribute'}")
            
            print("Successfully initialized Supabase client and verified connection")
        except Exception as e:
            print(f"Error initializing Supabase client: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
            raise

    def insert_transcript(self, video_id: str, title: str, transcript: str) -> Optional[str]:
        """Insert a new transcript into the database."""
        try:
            result = self.supabase.table('transcripts').upsert({
                'video_id': video_id,
                'title': title,
                'transcript': transcript
            }).execute()
            
            return video_id if result.data else None
        except Exception as e:
            print(f"Error inserting transcript: {str(e)}")
            return None

    def get_transcript(self, video_id: str) -> Dict[str, Any]:
        """Get a single transcript by video_id."""
        try:
            result = self.supabase.table('transcripts').select('*').eq('video_id', video_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting transcript: {str(e)}")
            return None

    def get_categories(self, video_id: str) -> Dict[str, list]:
        """Get categories for a transcript."""
        try:
            result = self.supabase.table('categories').select('*').eq('video_id', video_id).execute()
            
            categories = {
                'christian_life': [],
                'church_ministry': [],
                'theology': []
            }
            
            if result.data:
                data = result.data[0]
                categories['christian_life'] = data.get('christian_life', [])
                categories['church_ministry'] = data.get('church_ministry', [])
                categories['theology'] = data.get('theology', [])
            
            return categories
        except Exception as e:
            print(f"Error getting categories: {str(e)}")
            return categories

    def update_categories(self, video_id: str, categories: Dict[str, list]) -> bool:
        """Update categories for a transcript."""
        try:
            result = self.supabase.table('categories').upsert({
                'video_id': video_id,
                'christian_life': categories.get('christian_life', []),
                'church_ministry': categories.get('church_ministry', []),
                'theology': categories.get('theology', [])
            }).execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error updating categories: {str(e)}")
            return False

    def video_exists(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Check if a video exists and return its details."""
        try:
            result = self.supabase.table('transcripts').select('id, title').eq('video_id', video_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error checking video existence: {str(e)}")
            return None

    def get_all_transcripts(self) -> List[Dict[str, Any]]:
        """Get all transcripts."""
        try:
            print("Attempting to fetch transcripts from Supabase...")
            result = self.supabase.table('transcripts').select('*').execute()
            
            if result and hasattr(result, 'data'):
                if not result.data:
                    print("No transcripts found in Supabase database")
                    return []
                print(f"Successfully retrieved {len(result.data)} transcripts from Supabase")
                return result.data
            else:
                print("Invalid response format from Supabase")
                if result:
                    print(f"Response structure: {dir(result)}")
                return []
                
        except Exception as e:
            print(f"Error getting all transcripts: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
            return []

    def search_transcripts(self, query: str) -> List[Dict[str, Any]]:
        """Search transcripts using full-text search."""
        try:
            # Using ilike for basic text search - could be enhanced with proper full-text search
            result = self.supabase.table('transcripts').select('*').ilike('transcript', f'%{query}%').execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error searching transcripts: {str(e)}")
            return []

    def export_transcripts(self, format: str = "json") -> str:
        """Export all transcripts in the specified format."""
        try:
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
        except Exception as e:
            print(f"Error exporting transcripts: {str(e)}")
            return ""

    def update_transcript_summary(self, video_id: str, summary: str) -> bool:
        """Update the AI summary for a transcript."""
        try:
            result = self.supabase.table('transcripts').update({
                'ai_summary': summary
            }).eq('video_id', video_id).execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error updating summary: {str(e)}")
            return False

    def get_personal_stories(self, video_id: str) -> List[Dict[str, Any]]:
        """Get personal stories for a transcript."""
        try:
            # First get the transcript's stories through the junction table
            result = self.supabase.table('transcript_stories').select(
                'stories!inner(*)'
            ).eq('transcript_id', video_id).execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting personal stories: {str(e)}")
            return []

    def update_personal_stories(self, video_id: str, stories: List[Dict[str, str]]) -> bool:
        """Update personal stories for a transcript."""
        try:
            # First get transcript id
            transcript = self.get_transcript(video_id)
            if not transcript:
                return False
                
            transcript_id = transcript['id']
            
            # Begin by removing old relationships
            self.supabase.table('transcript_stories').delete().eq('transcript_id', transcript_id).execute()
            
            # Insert new stories and create relationships
            for story in stories:
                # Insert story
                story_result = self.supabase.table('stories').insert({
                    'title': story['title'],
                    'summary': story['summary'],
                    'message': story['message']
                }).execute()
                
                if story_result.data:
                    # Create relationship
                    story_id = story_result.data[0]['id']
                    self.supabase.table('transcript_stories').insert({
                        'transcript_id': transcript_id,
                        'story_id': story_id
                    }).execute()
            
            return True
        except Exception as e:
            print(f"Error updating personal stories: {str(e)}")
            return False