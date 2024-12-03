import streamlit as st
import time
from utils.command_parser import CommandParser
from utils.database import Database
from utils.transcript_processor import TranscriptProcessor
from utils.youtube_helper import YouTubeHelper

# Initialize components
db = Database()
parser = CommandParser()

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
        output.append(f"Video: {result['title']}")
        output.append(f"Highlight: {result['highlight']}\n")
    return "\n".join(output)

def list_transcripts() -> str:
    """List all stored transcripts."""
    transcripts = db.get_all_transcripts()
    if not transcripts:
        return "No transcripts stored"
    
    formatted_list = []
    for t in transcripts:
        formatted_list.append(f"• {t['title']}\n  Video ID: {t['video_id']}\n  Added: {t['created_at'].strftime('%Y-%m-%d %H:%M')}\n")
    return "\n".join(formatted_list)

# Register commands
parser.register("process", lambda args: process_playlist(args[0]),
               "process <playlist_url> - Process all videos in a YouTube playlist")
parser.register("search", lambda args: search_transcripts(" ".join(args)),
               "search <query> - Search through stored transcripts")
parser.register("list", lambda args: list_transcripts(),
               "list - Show all stored transcripts")
parser.register("help", lambda args: parser.get_help(),
               "help - Show available commands")

# Streamlit UI
st.set_page_config(page_title="YouTube Transcript Processor", layout="wide")

# Load custom CSS
with open("styles/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
