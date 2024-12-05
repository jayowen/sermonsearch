from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict

class TranscriptProcessor:
    @staticmethod
    def extract_transcript(video_id: str, raw: bool = False) -> str:
        """Extract transcript from a YouTube video."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            if raw:
                return transcript_list
            # Store the transcript with timestamps in the class
            TranscriptProcessor._last_transcript = transcript_list
            return " ".join([entry['text'] for entry in transcript_list])
        except Exception as e:
            TranscriptProcessor._last_transcript = []
            return "" if not raw else []  # Return empty string/list for videos without transcripts

    @staticmethod
    def format_transcript(transcript: str) -> str:
        """Format transcript text for better readability."""
        # Remove multiple spaces and normalize line endings
        formatted = " ".join(transcript.split())
        return formatted

    _last_transcript = []  # Class variable to store the last processed transcript
    
    @staticmethod
    def get_sentences_with_timestamps(transcript: str) -> List[tuple[str, float]]:
        """Extract sentences with their timestamps from a transcript."""
        try:
            if not TranscriptProcessor._last_transcript:
                return []
                
            results = []
            current_sentence = []
            current_start_time = None
            
            for entry in TranscriptProcessor._last_transcript:
                text = entry['text'].strip()
                if not text:
                    continue
                    
                # If this is the start of a new sentence
                if current_start_time is None:
                    current_start_time = entry['start']
                    
                current_sentence.append(text)
                
                # Check if the text ends with sentence-ending punctuation
                if text.endswith(('.', '!', '?')):
                    full_sentence = ' '.join(current_sentence)
                    results.append((full_sentence, current_start_time))
                    current_sentence = []
                    current_start_time = None
            
            # Add any remaining text as a sentence
            if current_sentence:
                full_sentence = ' '.join(current_sentence)
                results.append((full_sentence, current_start_time or 0))
            
            return results
        except Exception as e:
            print(f"Error processing sentences: {str(e)}")
            return []

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
