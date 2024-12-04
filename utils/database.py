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
        categories = {
            'christian_life': [],
            'church_ministry': [],
            'theology': []
        }
        
        try:
            # First get the transcript_id
            transcript = self.get_transcript(video_id)
            if not transcript:
                print(f"No transcript found for video_id: {video_id}")
                return categories
                
            transcript_id = transcript['id']
            
            # Then get categories using transcript_id
            result = self.supabase.table('categories').select('*').eq('transcript_id', transcript_id).execute()
            
            if result.data:
                data = result.data[0]
                categories['christian_life'] = data.get('christian_life', [])
                categories['church_ministry'] = data.get('church_ministry', [])
                categories['theology'] = data.get('theology', [])
            
            return categories
        except Exception as e:
            print(f"Error getting categories: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            return categories

    def update_categories(self, video_id: str, categories: Dict[str, list]) -> bool:
        """Update categories for a transcript."""
        try:
            print(f"Updating categories for video_id: {video_id}")
            print(f"Categories to update: {categories}")
            
            # First get the transcript_id
            transcript = self.get_transcript(video_id)
            if not transcript:
                print(f"No transcript found for video_id: {video_id}")
                return False
                
            transcript_id = transcript['id']
            print(f"Found transcript_id: {transcript_id}")
            
            # Then update categories
            data = {
                'transcript_id': transcript_id,
                'christian_life': categories.get('christian_life', []),
                'church_ministry': categories.get('church_ministry', []),
                'theology': categories.get('theology', [])
            }
            print(f"Preparing to upsert categories with data: {data}")
            
            result = self.supabase.table('categories').upsert(data).execute()
            
            print(f"Category update result: {result.data if hasattr(result, 'data') else 'No data'}")
            
            if not result.data:
                print("No data returned from categories update")
                return False
            
            print("Categories updated successfully")    
            return True
        except Exception as e:
            print(f"Error updating categories: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
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
            # First get the transcript to get its ID
            transcript = self.get_transcript(video_id)
            if not transcript:
                print(f"No transcript found for video_id: {video_id}")
                return []
                
            transcript_id = transcript['id']
            
            # Get stories through a join query
            result = self.supabase.from_('transcript_stories')\
                .select('stories(id, title, summary, message)')\
                .eq('transcript_id', transcript_id)\
                .execute()
            
            print(f"Stories retrieval result: {result.data if hasattr(result, 'data') else 'No data'}")
            
            # Extract stories from the nested structure
            stories = []
            if result.data:
                for item in result.data:
                    if item.get('stories'):
                        stories.append(item['stories'])
            
            return stories
        except Exception as e:
            print(f"Error getting personal stories: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            return []

    def update_personal_stories(self, video_id: str, stories: List[Dict[str, str]]) -> bool:
        """Update personal stories for a transcript."""
        try:
            print(f"Updating personal stories for video_id: {video_id}")
            print(f"Stories to update: {stories}")
            
            # First get transcript id
            transcript = self.get_transcript(video_id)
            if not transcript:
                print(f"No transcript found for video_id: {video_id}")
                return False
                
            transcript_id = transcript['id']
            print(f"Found transcript_id: {transcript_id}")
            
            # Begin by removing old relationships
            try:
                delete_result = self.supabase.table('transcript_stories').delete().eq('transcript_id', transcript_id).execute()
                print(f"Deleted old relationships: {delete_result.data if hasattr(delete_result, 'data') else 'No data'}")
            except Exception as e:
                print(f"Error deleting old relationships: {str(e)}")
            
            # Insert new stories and create relationships
            successful_stories = 0
            for story in stories:
                try:
                    print(f"Inserting story: {story['title']}")
                    # Insert story
                    story_data = {
                        'title': story['title'],
                        'summary': story['summary'],
                        'message': story['message']
                    }
                    story_result = self.supabase.table('stories').insert(story_data).execute()
                    
                    if story_result.data:
                        # Create relationship
                        story_id = story_result.data[0]['id']
                        print(f"Story inserted with id: {story_id}")
                        
                        relation_data = {
                            'transcript_id': transcript_id,
                            'story_id': story_id
                        }
                        relation_result = self.supabase.table('transcript_stories').insert(relation_data).execute()
                        print(f"Relationship created: {relation_result.data if hasattr(relation_result, 'data') else 'No data'}")
                        successful_stories += 1
                    else:
                        print(f"Failed to insert story: {story['title']}")
                except Exception as e:
                    print(f"Error processing story {story['title']}: {str(e)}")
                    if hasattr(e, 'response'):
                        print(f"Response details: {e.response}")
            
            print(f"Successfully processed {successful_stories} out of {len(stories)} stories")
            return successful_stories > 0
        except Exception as e:
            print(f"Error updating personal stories: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
            return False