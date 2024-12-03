import os
from googleapiclient.discovery import build
import streamlit as st
import time
from utils.command_parser import CommandParser
from utils.database import Database
from utils.transcript_processor import TranscriptProcessor
from utils.youtube_helper import YouTubeHelper

# Initialize components
db = Database()
parser = CommandParser()

def process_video(url: str) -> str:
    """Process a single YouTube video."""
    try:
        video_id = TranscriptProcessor.extract_video_id(url)
        transcript = TranscriptProcessor.extract_transcript(video_id)
        
        if not transcript:
            return "Error: No subtitles available for this video"
            
        # Get video title using YouTube API
        youtube = build('youtube', 'v3', developerKey=os.environ.get('YOUTUBE_API_KEY'))
        response = youtube.videos().list(part='snippet', id=video_id).execute()
        
        if not response['items']:
            return "Error: Video not found"
            
        title = response['items'][0]['snippet']['title']
        formatted_transcript = TranscriptProcessor.format_transcript(transcript)
        db.store_transcript(video_id, title, formatted_transcript)
        
        return f"Successfully processed video:\n- Title: {title}\n- Video ID: {video_id}"
    except Exception as e:
        return f"Error: {str(e)}"

def process_playlist(url: str) -> str:
    """Process all videos in a playlist."""
    try:
        videos = YouTubeHelper.get_playlist_videos(url)
        processed = 0
        skipped = 0
        
        for video in videos:
            transcript = TranscriptProcessor.extract_transcript(video['video_id'])
            if transcript:
                formatted_transcript = TranscriptProcessor.format_transcript(transcript)
                db.store_transcript(video['video_id'], video['title'], formatted_transcript)
                processed += 1
            else:
                skipped += 1
                
        return f"Processing complete:\n- Successfully processed: {processed} videos\n- Skipped (no subtitles): {skipped} videos"
    except Exception as e:
        return f"Error: {str(e)}"

def search_transcripts(query: str) -> str:
    """Search through stored transcripts."""
    results = db.search_transcripts(query)
    if not results:
        return "No matches found"
    
    output = []
    for result in results:
        video_url = f"https://youtube.com/watch?v={result['video_id']}"
        output.append(f"Video: <a href='{video_url}' target='_blank'>{result['title']}</a>")
        output.append(f"Highlight: {result['highlight']}\n")
    return "\n".join(output)

def get_transcript(video_id: str) -> str:
    """Get transcript content for a specific video."""
    with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT title, transcript FROM transcripts WHERE video_id = %s", (video_id,))
        result = cur.fetchone()
        if result:
            return f"## {result['title']}\n\n{result['transcript']}"
        return "Transcript not found"

def list_transcripts() -> str:
    """List all stored transcripts."""
    transcripts = db.get_all_transcripts()
    if not transcripts:
        return "No transcripts stored"
    
    formatted_list = []
    for t in transcripts:
        formatted_list.append(
            f"• <a href='javascript:void(0)' onclick='show_transcript(\"{t['video_id']}\")'>{t['title']}</a>\n"
            f"  Video ID: {t['video_id']}\n"
            f"  Added: {t['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
        )
    return "\n".join(formatted_list)

# Register commands
parser.register("process-video", lambda args: process_video(args[0]),
               "process-video <video_url> - Process a single YouTube video")
parser.register("process-playlist", lambda args: process_playlist(args[0]),
               "process-playlist <playlist_url> - Process all videos in a YouTube playlist")
parser.register("search", lambda args: search_transcripts(" ".join(args)),
               "search <query> - Search through stored transcripts")
parser.register("list", lambda args: list_transcripts(),
               "list - Show all stored transcripts")
parser.register("transcript", lambda args: get_transcript(args[0]),
               "transcript <video_id> - Show transcript for a specific video")
parser.register("help", lambda args: parser.get_help(),
               "help - Show available commands")

# Streamlit UI
st.set_page_config(page_title="YouTube Transcript Processor", layout="wide")

# Load custom CSS and add JavaScript
with open("styles/custom.css") as f:
    st.markdown(f"""
        <style>{f.read()}</style>
        <script>
        function show_transcript(video_id) {{
            document.getElementById('command_input').value = 'transcript ' + video_id;
            document.getElementById('command_input').dispatchEvent(new Event('input'));
            document.querySelector('button[kind="primaryFormSubmit"]').click();
        }}
        </script>
    """, unsafe_allow_html=True)

st.title("YouTube Transcript Processor")

# Command input
command = st.text_input("Enter command:", key="command_input",
                       help="Type 'help' to see available commands")

if command:
    try:
        # Parse and execute command
        handler, args = parser.parse(command)
        with st.spinner("Processing..."):
            result = handler(args)
        
        # Display result in terminal-style container
        st.markdown(
            f"""
            <div class="terminal-container">
                <div class="command-input">> {command}</div>
                <pre>{result}</pre>
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Help section
with st.expander("Available Commands"):
    st.markdown(parser.get_help().replace("\n", "<br>"), unsafe_allow_html=True)
