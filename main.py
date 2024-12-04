import streamlit as st
import os
from utils.database import Database
from psycopg2.extras import RealDictCursor
from utils.youtube_helper import YouTubeHelper
from utils.transcript_processor import TranscriptProcessor
from utils.command_parser import CommandParser
from typing import Dict, Any
import json

# Configure Streamlit page at the very beginning
st.set_page_config(
    page_title="YouTube Transcript Processor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database connection
db = Database()
youtube = YouTubeHelper()
processor = TranscriptProcessor()
parser = CommandParser()

# Initialize session state
if 'current_command' not in st.session_state:
    st.session_state.current_command = None
if 'show_transcript_id' not in st.session_state:
    st.session_state.show_transcript_id = None

# Load and apply custom CSS
try:
    with open('styles/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading styles: {str(e)}")

# Main content wrapper
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.title("YouTube Transcript Processor")
    st.markdown("---")
    
    if st.button("🎥 Process Single Video", use_container_width=True):
        st.session_state.current_command = "process"
    if st.button("📑 Process Playlist", use_container_width=True):
        st.session_state.current_command = "playlist"
    if st.button("🔍 Search Transcripts", use_container_width=True):
        st.session_state.current_command = "search"
    if st.button("📋 List All Transcripts", use_container_width=True):
        st.session_state.current_command = "list"
    if st.button("📊 Total Data Analysis", use_container_width=True):
        st.session_state.current_command = "total_analysis"
    if st.button("📊 Basic Analysis", use_container_width=True):
        st.session_state.current_command = "analyze"
    if st.button("📈 Word Frequency", use_container_width=True):
        st.session_state.current_command = "frequency"
    if st.button("🔑 Key Phrases", use_container_width=True):
        st.session_state.current_command = "phrases"
    if st.button("⏱️ Time Segments", use_container_width=True):
        st.session_state.current_command = "segments"
    if st.button("💾 Export Data", use_container_width=True):
        st.session_state.current_command = "export"
    st.markdown("---")
    with st.expander("ℹ️ Command Help"):
        st.markdown(parser.get_help().replace("\n", "<br>"), unsafe_allow_html=True)

# Main content area
if st.session_state.current_command == "process":
    st.subheader("Process Single Video")
    url = st.text_input("Enter YouTube Video URL")
    
    if st.button("Process Video"):
        if url:
            try:
                video_id = processor.extract_video_id(url)
                
                # Check if video already exists
                existing_video = db.video_exists(video_id)
                if existing_video:
                    st.info(f"This video '{existing_video['title']}' is already in the system.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("View Existing"):
                            st.session_state.show_transcript_id = video_id
                            st.session_state.current_command = "view_video"
                            st.experimental_rerun()
                    with col2:
                        if st.button("Re-process"):
                            try:
                                # Process existing video
                                transcript = processor.extract_transcript(video_id)
                                if not transcript:
                                    st.error("No transcript available for this video.")
                                    st.stop()
                                
                                # Generate AI summary
                                with st.spinner("Generating AI summary..."):
                                    ai_summary = parser.summarize_text(transcript, max_length=250)
                                
                                # Store in database with summary
                                db.store_transcript(video_id, existing_video['title'], transcript, ai_summary)
                                st.success("Transcript re-processed successfully!")
                                
                                # Redirect to video view
                                st.session_state.show_transcript_id = video_id
                                st.session_state.current_command = "view_video"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error re-processing video: {str(e)}")
                                st.stop()
                    st.stop()  # Stop here if video exists to prevent further processing
                
                # Process new video if it doesn't exist
                try:
                    transcript = processor.extract_transcript(video_id)
                    if not transcript:
                        st.error("No transcript available for this video.")
                        st.stop()
                    
                    # Generate AI summary
                    with st.spinner("Generating AI summary..."):
                        ai_summary = parser.summarize_text(transcript, max_length=250)
                    
                    # Get video title from YouTube API
                    try:
                        video_info = youtube.get_video_info(video_id)
                        video_title = video_info['title']
                    except Exception as e:
                        video_title = f"Video {video_id}"
                        st.warning(f"Could not fetch video title: {str(e)}")
                    
                    # Store in database with summary
                    db.store_transcript(video_id, video_title, transcript, ai_summary)
                    st.success("Transcript processed successfully!")
                    
                    # Redirect to video view
                    st.session_state.show_transcript_id = video_id
                    st.session_state.current_command = "view_video"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
            except Exception as e:
                st.error(f"Error extracting video ID: {str(e)}")
        else:
            st.warning("Please enter a valid YouTube URL")

elif st.session_state.current_command == "playlist":
    st.subheader("Process Playlist")
    url = st.text_input("Enter YouTube Playlist URL")
    batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=5, 
                          help="Number of videos to process in each batch")
    
    if st.button("Process", key="process_playlist_btn"):
        if url:
            st.markdown("""
            ### Processing Playlist
            The videos will be processed in batches to handle large playlists efficiently.
            You can monitor the progress below:
            """)
            try:
                videos = youtube.get_playlist_videos(url)
                
                # Check for existing videos first
                existing_videos = []
                new_videos = []
                for video in videos:
                    if db.video_exists(video['video_id']):
                        existing_videos.append(video)
                    else:
                        new_videos.append(video)
                
                if existing_videos:
                    st.info(f"Found {len(existing_videos)} videos that are already in the system.")
                    if st.button("Re-process all"):
                        new_videos.extend(existing_videos)
                    else:
                        st.write("Will only process new videos.")
                
                if new_videos:
                    progress_bar = st.progress(0)
                    processed_count = 0
                    
                    for i, video in enumerate(new_videos):
                        transcript = processor.extract_transcript(video['video_id'])
                        if transcript:
                            # Generate AI summary for each video
                            ai_summary = parser.summarize_text(transcript, max_length=250)
                            db.store_transcript(video['video_id'], video['title'], transcript, ai_summary)
                            processed_count += 1
                        progress_bar.progress((i + 1) / len(new_videos))
                    
                    st.success(f"Processed {processed_count} videos from playlist!")
                else:
                    st.info("No new videos to process.")
            except Exception as e:
                st.error(f"Error processing playlist: {str(e)}")
        else:
            st.warning("Please enter a valid playlist URL")

elif st.session_state.current_command == "search":
    st.subheader("Search Transcripts")
    query = st.text_input("Enter search query")
    
    if query:
        results = db.search_transcripts(query)
        if results:
            st.write(f"Found {len(results)} results:")
            for result in results:
                with st.expander(result['title']):
                    st.markdown(f"""<div class="search-result">{result['highlight']}</div>""", 
                              unsafe_allow_html=True)
        else:
            st.info("No matching transcripts found")

elif st.session_state.current_command == "list":
    st.subheader("All Transcripts")
    transcripts = db.get_all_transcripts()
    
    if transcripts:
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
    else:
        st.info("No transcripts found in database")

elif st.session_state.current_command == "view_video" and st.session_state.show_transcript_id:
    with st.spinner("Loading video and transcript..."):
        # Get video details
        with db.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT title, transcript, ai_summary FROM transcripts WHERE video_id = %s", 
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
                
                # Display AI Summary if available
                if result.get('ai_summary'):
                    st.markdown("### AI Summary")
                    # Remove any prefix text about word count or summary
                    summary = result['ai_summary']
                    summary = summary.replace("Here is a concise summary of the transcript:", "")
                    summary = summary.replace("Here is a summary of the key points from the transcript:", "")
                    summary = summary.strip()
                    st.markdown(
                        f"""<div class="transcript-viewer">
                            {summary}
                        </div>""",
                        unsafe_allow_html=True
                    )

                # Display key statistics
                st.markdown("### Key Statistics")
                stats = parser.get_word_stats(result['transcript'])
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Word Count", stats['word_count'])
                    st.metric("Sentence Count", stats['sentence_count'])
                with col2:
                    st.metric("Unique Words", stats['unique_words'])
                    st.metric("Avg Words/Sentence", f"{stats['avg_words_per_sentence']:.1f}")

                # Display keywords
                st.markdown("### Top Keywords")
                keywords = parser.extract_keywords(result['transcript'])
                st.bar_chart({word: count for word, count in keywords})

                # Display transcript in an expander
                with st.expander("Full Transcript"):
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

elif st.session_state.current_command == "analyze":
    st.subheader("Basic Analysis")
    transcripts = db.get_all_transcripts()
    
    if transcripts:
        # Select transcript
        titles = [t['title'] for t in transcripts]
        selected_title = st.selectbox("Select transcript to analyze", titles)
        
        selected_transcript = next(t for t in transcripts if t['title'] == selected_title)
        
        # Show statistics
        stats = parser.get_word_stats(selected_transcript['transcript'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Word Count", stats['word_count'])
            st.metric("Sentence Count", stats['sentence_count'])
        with col2:
            st.metric("Unique Words", stats['unique_words'])
            st.metric("Avg Words/Sentence", f"{stats['avg_words_per_sentence']:.1f}")
            
        # Show keywords
        st.write("### Top Keywords")
        keywords = parser.extract_keywords(selected_transcript['transcript'])
        st.bar_chart(
            {word: count for word, count in keywords}
        )
    else:
        st.info("No transcripts available for analysis")

elif st.session_state.current_command == "frequency":
    st.subheader("Word Frequency Analysis")
    transcripts = db.get_all_transcripts()
    
    if transcripts:
        titles = [t['title'] for t in transcripts]
        selected_title = st.selectbox("Select transcript", titles)
        
        selected_transcript = next(t for t in transcripts if t['title'] == selected_title)
        min_count = st.slider("Minimum word frequency", 2, 20, 5)
        
        frequencies = parser.get_word_frequency(selected_transcript['transcript'], min_count)
        if frequencies:
            st.bar_chart(
                {word: count for word, count in frequencies}
            )
        else:
            st.info(f"No words found with frequency >= {min_count}")
    else:
        st.info("No transcripts available for analysis")

elif st.session_state.current_command == "phrases":
    st.subheader("Key Phrases Analysis")
    transcripts = db.get_all_transcripts()
    
    if transcripts:
        titles = [t['title'] for t in transcripts]
        selected_title = st.selectbox("Select transcript", titles)
        
        selected_transcript = next(t for t in transcripts if t['title'] == selected_title)
        
        phrases = parser.find_key_phrases(selected_transcript['transcript'])
        if phrases:
            st.bar_chart(
                {phrase: count for phrase, count in phrases}
            )
        else:
            st.info("No key phrases found")
    else:
        st.info("No transcripts available for analysis")

elif st.session_state.current_command == "export":
    st.subheader("Export Data")
    format = st.selectbox("Select export format", ["json", "csv", "txt"])
    
    if st.button("Export"):
        try:
            data = db.export_transcripts(format)
            if data:
                st.download_button(
                    label=f"Download {format.upper()} file",
                    data=data,
                    file_name=f"transcripts.{format}",
                    mime=f"text/{format}"
                )
            else:
                st.info("No data available to export")
        except Exception as e:
            st.error(f"Error exporting data: {str(e)}")

elif st.session_state.current_command == "segments":
    st.subheader("Time-based Segmentation")
    transcripts = db.get_all_transcripts()
    
    if transcripts:
        titles = [t['title'] for t in transcripts]
        selected_title = st.selectbox("Select transcript", titles)
        
        selected_transcript = next(t for t in transcripts if t['title'] == selected_title)
        segment_length = st.slider("Words per segment", 100, 500, 300)
        
        segments = parser.extract_time_segments(selected_transcript['transcript'], segment_length)
        if segments:
            st.write(f"### Transcript Segments ({len(segments)} total)")
            for i, segment in enumerate(segments, 1):
                with st.expander(f"Segment {i}"):
                    st.write(segment)
        else:
            st.info("No segments available")
    else:
        st.info("No transcripts available for segmentation")

elif st.session_state.current_command == "total_analysis":
    st.subheader("Total Data Analysis")
    transcripts = db.get_all_transcripts()
    
    if not transcripts:
        st.info("No transcripts available for analysis")
    else:
        # Combine all transcripts
        combined_text = " ".join([t['transcript'] for t in transcripts])
        
        # Show total statistics
        stats = parser.get_word_stats(combined_text)
        st.write("### Combined Text Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Word Count", stats['word_count'])
            st.metric("Total Sentence Count", stats['sentence_count'])
        with col2:
            st.metric("Total Unique Words", stats['unique_words'])
            st.metric("Overall Avg Words/Sentence", f"{stats['avg_words_per_sentence']:.1f}")
        
        # Show keywords from all transcripts
        st.write("### Top Keywords Across All Transcripts")
        keywords = parser.extract_keywords(combined_text, top_n=20)
        st.bar_chart(
            {word: count for word, count in keywords}
        )
        
        # Show AI-powered summary of all content
        st.write("### AI-Generated Summary of All Content")
        max_words = st.slider("Maximum summary length (words)", 100, 1000, 300)
        with st.spinner("Generating AI summary of all content..."):
            # Split text into chunks of roughly 100k characters to stay within token limits
            chunk_size = 100000
            chunks = [combined_text[i:i + chunk_size] for i in range(0, len(combined_text), chunk_size)]
            
            summaries = []
            for i, chunk in enumerate(chunks, 1):
                st.write(f"Processing chunk {i} of {len(chunks)}...")
                chunk_summary = parser.summarize_text(chunk, max_words // len(chunks))
                if not chunk_summary.startswith("Error"):
                    summaries.append(chunk_summary)
            
            if summaries:
                final_summary = " ".join(summaries)
                st.markdown(f"""<div class="transcript-viewer">{final_summary}</div>""", 
                          unsafe_allow_html=True)
            else:
                st.error("Unable to generate summary. Text might be too long or an error occurred.")
        
        # Display transcript count
        st.metric("Total Number of Transcripts", len(transcripts))

# Close main-content div
st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.current_command:
    st.info("👈 Select a command from the sidebar to get started")