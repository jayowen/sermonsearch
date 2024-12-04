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
def init_database():
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            return Database()
        except Exception as e:
            retry_count += 1
            if retry_count == max_retries:
                st.error(f"Failed to connect to the database after {max_retries} attempts. Please try again later.")
                st.stop()
            time.sleep(2)  # Wait before retrying

db = init_database()
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
    if st.button("📊 Basic Analysis", use_container_width=True):
        st.session_state.current_command = "analyze"
    if st.button("📈 Word Frequency", use_container_width=True):
        st.session_state.current_command = "word_frequency"
    if st.button("🔑 Key Phrases", use_container_width=True):
        st.session_state.current_command = "key_phrases"
    if st.button("⏱️ Time Segments", use_container_width=True):
        st.session_state.current_command = "time_segments"
    if st.button("🔄 Compare Transcripts", use_container_width=True):
        st.session_state.current_command = "compare"
    if st.button("💾 Export Data", use_container_width=True):
        st.session_state.current_command = "export"
    
    st.markdown("---")
    with st.expander("ℹ️ Command Help"):
        st.markdown(parser.get_help().replace("\n", "<br>"), unsafe_allow_html=True)

# Configure page and add custom styles
st.set_page_config(
    page_title="YouTube Transcript Processor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom styles and header
st.markdown("""
    <div class="header-bar">
        <h1>YouTube Transcript Processor</h1>
    </div>
    <div class="main-content">
""", unsafe_allow_html=True)

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
                    st.rerun()

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

elif st.session_state.current_command == "export":
    st.subheader("Export Transcripts")
    export_format = st.selectbox(
        "Select export format",
        ["json", "csv", "txt"],
        help="Choose the format for exporting your transcripts"
    )
    
    if st.button("Export", key="export_btn"):
        try:
            data = db.export_transcripts(format=export_format)
            if data:
                st.download_button(
                    label=f"Download {export_format.upper()} File",
                    data=data,
                    file_name=f"transcripts.{export_format}",
                    mime={
                        'json': 'application/json',
                        'csv': 'text/csv',
                        'txt': 'text/plain'
                    }[export_format]
                )
            else:
                st.info("No transcripts available to export")
        except Exception as e:
            st.error(f"Error exporting data: {str(e)}")

elif st.session_state.current_command == "analyze":
    st.subheader("Analyze Transcript")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts available for analysis")
    else:
        selected = st.selectbox(
            "Select a transcript to analyze",
            options=[(t['id'], t['title']) for t in transcripts],
            format_func=lambda x: x[1]
        )
        
        if selected:
            transcript = next((t for t in transcripts if t['id'] == selected[0]), None)
            if transcript:
                # Show text statistics
                stats = parser.get_word_stats(transcript['transcript'])
                st.write("### Text Statistics")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Word Count", stats['word_count'])
                    st.metric("Sentence Count", stats['sentence_count'])
                with col2:
                    st.metric("Unique Words", stats['unique_words'])
                    st.metric("Avg Words/Sentence", f"{stats['avg_words_per_sentence']:.1f}")
                
                # Show keywords
                st.write("### Top Keywords")
                keywords = parser.extract_keywords(transcript['transcript'])
                st.bar_chart(
                    {word: count for word, count in keywords}
                )
                
                # Show AI-powered summary
                st.write("### AI-Generated Summary")
                max_words = st.slider("Maximum summary length (words)", 50, 500, 200)
                with st.spinner("Generating AI summary..."):
                    summary = parser.summarize_text(transcript['transcript'], max_words)
                    if summary.startswith("Error"):
                        st.error(summary)
                    else:
                        st.markdown(f"""<div class="transcript-viewer">{summary}</div>""", 
                                  unsafe_allow_html=True)

elif st.session_state.current_command == "compare":
    st.subheader("Compare Transcripts")
    transcripts = db.get_all_transcripts()
    
    if len(transcripts) < 2:
        st.info("Need at least 2 transcripts for comparison")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            selected1 = st.selectbox(
                "Select first transcript",
                options=[(t['id'], t['title']) for t in transcripts],
                format_func=lambda x: x[1],
                key="compare1"
            )
        
        with col2:
            selected2 = st.selectbox(
                "Select second transcript",
                options=[(t['id'], t['title']) for t in transcripts],
                format_func=lambda x: x[1],
                key="compare2"
            )
        
        if selected1 and selected2 and selected1 != selected2:
            transcript1 = next((t for t in transcripts if t['id'] == selected1[0]), None)
            transcript2 = next((t for t in transcripts if t['id'] == selected2[0]), None)
            
            if transcript1 and transcript2:
                # Compare statistics
                stats1 = parser.get_word_stats(transcript1['transcript'])
                stats2 = parser.get_word_stats(transcript2['transcript'])
                
                st.write("### Statistical Comparison")
                metrics = {
                    "Word Count": (stats1['word_count'], stats2['word_count']),
                    "Sentence Count": (stats1['sentence_count'], stats2['sentence_count']),
                    "Unique Words": (stats1['unique_words'], stats2['unique_words']),
                    "Avg Words/Sentence": (
                        round(stats1['avg_words_per_sentence'], 1),
                        round(stats2['avg_words_per_sentence'], 1)
                    )
                }
                
                for metric, (val1, val2) in metrics.items():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(f"{metric} (1)", val1)
                    with col2:
                        st.metric(f"{metric} (2)", val2)
                
                # Compare keywords
                st.write("### Keyword Comparison")
                kw1 = dict(parser.extract_keywords(transcript1['transcript']))
                kw2 = dict(parser.extract_keywords(transcript2['transcript']))
                common_words = set(kw1.keys()) & set(kw2.keys())
                
                if common_words:
                    st.write("Common keywords:")
                    for word in common_words:
                        st.write(f"- {word} ({kw1[word]} vs {kw2[word]} occurrences)")
            
    if st.button("← Back to List"):
        st.session_state.current_command = "list"
        st.rerun()
elif st.session_state.current_command == "word_frequency":
    st.subheader("Word Frequency Analysis")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts available for analysis")
    else:
        selected = st.selectbox(
            "Select a transcript to analyze",
            options=[(t['id'], t['title']) for t in transcripts],
            format_func=lambda x: x[1],
            key="word_freq"
        )
        
        min_count = st.slider("Minimum word occurrence", 2, 20, 5)
        
        if selected:
            transcript = next((t for t in transcripts if t['id'] == selected[0]), None)
            if transcript:
                word_freq = parser.get_word_frequency(transcript['transcript'], min_count)
                
                if word_freq:
                    st.write("### Word Frequency Distribution")
                    freq_data = {word: count for word, count in word_freq}
                    st.bar_chart(freq_data)
                else:
                    st.info("No words meet the minimum frequency threshold")

elif st.session_state.current_command == "key_phrases":
    st.subheader("Key Phrases Analysis")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts available for analysis")
    else:
        selected = st.selectbox(
            "Select a transcript to analyze",
            options=[(t['id'], t['title']) for t in transcripts],
            format_func=lambda x: x[1],
            key="phrases"
        )
        
        if selected:
            transcript = next((t for t in transcripts if t['id'] == selected[0]), None)
            if transcript:
                col1, col2 = st.columns(2)
                with col1:
                    min_words = st.slider("Min words in phrase", 2, 5, 3)
                with col2:
                    max_words = st.slider("Max words in phrase", 3, 8, 6)
                
                phrases = parser.find_key_phrases(transcript['transcript'], min_words, max_words)
                if phrases:
                    st.write("### Most Common Phrases")
                    for phrase, count in phrases:
                        st.markdown(f"- **{phrase}** ({count} occurrences)")
                else:
                    st.info("No key phrases found with current settings")

elif st.session_state.current_command == "time_segments":
    st.subheader("Time-based Segments")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts available for segmentation")
    else:
        selected = st.selectbox(
            "Select a transcript to segment",
            options=[(t['id'], t['title']) for t in transcripts],
            format_func=lambda x: x[1],
            key="segments"
        )
        
        if selected:
            transcript = next((t for t in transcripts if t['id'] == selected[0]), None)
            if transcript:
                words_per_segment = st.slider("Words per segment", 100, 500, 300)
                segments = parser.extract_time_segments(transcript['transcript'], words_per_segment)
                
                st.write(f"### Transcript Segments ({len(segments)} total)")
                for i, segment in enumerate(segments, 1):
                    with st.expander(f"Segment {i}"):
                        st.write(segment)
# Close main-content div
st.markdown("</div>", unsafe_allow_html=True)

else:
    if not st.session_state.current_command:
        st.info("👈 Select a command from the sidebar to get started")
