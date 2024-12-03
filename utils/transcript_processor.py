from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict

class TranscriptProcessor:
    @staticmethod
    def extract_transcript(video_id: str) -> str:
        """Extract transcript from a YouTube video."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([entry['text'] for entry in transcript_list])
        except Exception as e:
            return ""  # Return empty string for videos without transcripts

    @staticmethod
    def format_transcript(transcript: str) -> str:
        """Format transcript text for better readability."""
        # Remove multiple spaces and normalize line endings
        formatted = " ".join(transcript.split())
        return formatted

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from YouTube URL."""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError("Invalid YouTube URL")
