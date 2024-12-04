import os
from googleapiclient.discovery import build
import streamlit as st
import time
from psycopg2.extras import RealDictCursor
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

def process_playlist(url: str, batch_size: int = 5) -> None:
    """Process all videos in a playlist with batch processing and progress updates."""
    try:
        videos = YouTubeHelper.get_playlist_videos(url)
        total_videos = len(videos)
        
        if not videos:
            st.error("No videos found in the playlist")
            return
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        stats = st.empty()
        processed = 0
        skipped = 0
        errors = 0
        
        # Process videos in batches
        for i in range(0, total_videos, batch_size):
            batch = videos[i:i + batch_size]
            batch_processed = 0
            batch_skipped = 0
            
            status_text.text(f"Processing batch {i//batch_size + 1} of {(total_videos + batch_size - 1)//batch_size}")
            
            for video in batch:
                try:
                    transcript = TranscriptProcessor.extract_transcript(video['video_id'])
                    if transcript:
                        formatted_transcript = TranscriptProcessor.format_transcript(transcript)
                        db.store_transcript(video['video_id'], video['title'], formatted_transcript)
                        batch_processed += 1
                        processed += 1
                    else:
                        batch_skipped += 1
                        skipped += 1
                except Exception as e:
                    st.warning(f"Error processing video '{video['title']}': {str(e)}")
                    errors += 1
                    time.sleep(1)  # Add delay on error to avoid rate limiting
                
                # Update progress
                progress = (i + len(batch)) / total_videos
                progress_bar.progress(min(1.0, progress))
                
                # Update stats
                stats.markdown(f"""
                    **Progress:**
                    - Processed: {processed} videos
                    - Skipped (no subtitles): {skipped} videos
                    - Errors: {errors} videos
                    - Remaining: {total_videos - (processed + skipped + errors)} videos
                """)
                
            # Add a small delay between batches to avoid rate limiting
            if i + batch_size < total_videos:
                time.sleep(2)
        
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

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

def list_transcripts() -> None:
    """List all stored transcripts."""
    transcripts = db.get_all_transcripts()
    if not transcripts:
        st.write("No transcripts stored")
        return
    
    for t in transcripts:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"• {t['title']}")
            st.text(f"  Video ID: {t['video_id']}")
            st.text(f"  Added: {t['created_at'].strftime('%Y-%m-%d %H:%M')}")
        with col2:
            if st.button("View Transcript", key=f"btn_{t['video_id']}"):
                st.session_state.show_transcript_id = t['video_id']

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
st.set_page_config(
    page_title="YouTube Transcript Processor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("styles/custom.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session states
if 'show_transcript_id' not in st.session_state:
    st.session_state.show_transcript_id = None
if 'current_command' not in st.session_state:
    st.session_state.current_command = None

# Sidebar
with st.sidebar:
    st.title("Commands")
    
    # Command buttons
    if st.button("📺 Process Video", use_container_width=True):
        st.session_state.current_command = "process-video"
    if st.button("📑 Process Playlist", use_container_width=True):
        st.session_state.current_command = "process-playlist"
    if st.button("🔍 Search Transcripts", use_container_width=True):
        st.session_state.current_command = "search"
    if st.button("📋 List All Transcripts", use_container_width=True):
        st.session_state.current_command = "list"
    
    st.markdown("---")
    with st.expander("ℹ️ Command Help"):
        st.markdown(parser.get_help().replace("\n", "<br>"), unsafe_allow_html=True)

# Main content
st.title("YouTube Transcript Processor")

# Command interface
if st.session_state.current_command == "process-video":
    st.subheader("Process Single Video")
    url = st.text_input("Enter YouTube video URL:")
    if st.button("Process", key="process_video_btn"):
        if url:
            with st.spinner("Processing video..."):
                result = process_video(url)
                st.markdown(
                    f"""<div class="terminal-container">
                        <pre>{result}</pre>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.warning("Please enter a video URL")

elif st.session_state.current_command == "process-playlist":
    st.subheader("Process Playlist")
    url = st.text_input("Enter YouTube playlist URL:")
    batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=5, 
                          help="Number of videos to process in each batch")
    
    if st.button("Process", key="process_playlist_btn"):
        if url:
            st.markdown("""
            ### Processing Playlist
            The videos will be processed in batches to handle large playlists efficiently.
            You can monitor the progress below:
            """)
            process_playlist(url, batch_size)
        else:
            st.warning("Please enter a playlist URL")

elif st.session_state.current_command == "search":
    st.subheader("Search Transcripts")
    query = st.text_input("Enter search query:")
    if st.button("Search", key="search_btn"):
        if query:
            with st.spinner("Searching..."):
                results = db.search_transcripts(query)
                if results:
                    for result in results:
                        video_url = f"https://youtube.com/watch?v={result['video_id']}"
                        st.markdown(
                            f"""<div class="search-result">
                                <a href="{video_url}" target="_blank" class="video-link">{result['title']}</a>
                                <p class="highlight-text">{result['highlight']}</p>
                            </div>""",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No results found")
        else:
            st.warning("Please enter a search query")

elif st.session_state.current_command == "list":
    st.subheader("All Transcripts")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts stored")
    else:
        # Create a grid layout
        cols = st.columns(3)
        for idx, t in enumerate(transcripts):
            with cols[idx % 3]:
                st.markdown(
                    f"""<div class="video-card">
                        <div class="video-thumbnail">
                            <img src="https://img.youtube.com/vi/{t['video_id']}/mqdefault.jpg" alt="Video thumbnail">
                        </div>
                        <div class="video-info">
                            <h3>{t['title']}</h3>
                            <p>Added: {t['created_at'].strftime('%Y-%m-%d %H:%M')}</p>
                        </div>
                        </div>""",
                    unsafe_allow_html=True
                )
                if st.button("View Details", key=f"btn_{t['video_id']}", use_container_width=True):
                    st.session_state.show_transcript_id = t['video_id']
                    st.session_state.current_command = "view_video"
                    st.experimental_rerun()

# Handle video viewing
if st.session_state.current_command == "view_video" and st.session_state.show_transcript_id:
    with st.spinner("Loading video and transcript..."):
        # Get video details
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT title, transcript FROM transcripts WHERE video_id = %s", 
                       (st.session_state.show_transcript_id,))
            result = cur.fetchone()
            
            if result:
                # Display video title
                st.title(result['title'])
                
                # Embed YouTube video
                video_url = f"https://www.youtube.com/embed/{st.session_state.show_transcript_id}"
                st.markdown(
                    f"""
                    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin-bottom: 20px;">
                        <iframe 
                            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
                            src="{video_url}"
                            frameborder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowfullscreen
                        ></iframe>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Display transcript
                st.markdown("### Transcript")
                st.markdown(
                    f"""<div class="transcript-viewer">
                        {result['transcript']}
                    </div>""",
                    unsafe_allow_html=True
                )
                
                # Back button
                if st.button("← Back to List"):
                    st.session_state.show_transcript_id = None
                    st.session_state.current_command = "list"
                    st.rerun()
else:
    if not st.session_state.current_command:
        st.info("👈 Select a command from the sidebar to get started")
