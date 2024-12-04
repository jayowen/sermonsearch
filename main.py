import streamlit as st
# Configure Streamlit page settings first
st.set_page_config(
    page_title="Sermon Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

import os
from dotenv import load_dotenv
from utils.database import Database
from utils.youtube_helper import YouTubeHelper
from utils.transcript_processor import TranscriptProcessor
from utils.command_parser import CommandParser
from utils.ai_helper import AIHelper  # Import AIHelper
from typing import Dict, Any
import json

def process_single_video(video_id: str, title: str = None, no_redirect: bool = False) -> None:
    """Process a single video: download transcript and store in database."""
    try:
        transcript = processor.extract_transcript(video_id)
        if not transcript:
            st.error("No transcript available for this video.")
            st.stop()
        
        # If no title provided, get it from YouTube
        if not title:
            video_info = youtube.get_video_info(video_id)
            title = video_info['title']

        # Generate AI summary with progress indicator
        with st.spinner("Generating AI summary..."):
            try:
                summary = ai_helper.generate_summary(transcript)
                st.write("✓ AI summary generated successfully")
            except Exception as e:
                st.error(f"Error generating AI summary: {str(e)}")
                summary = None
        
        # Generate categories with progress indicator
        with st.spinner("Analyzing transcript and generating categories..."):
            try:
                categories = ai_helper.categorize_transcript(transcript)
                st.write("✓ Categories generated successfully")
            except Exception as e:
                st.error(f"Error generating categories: {str(e)}")
                categories = None
            
        # Insert transcript with summary and get the ID
        transcript_id = db.insert_transcript(video_id, title, transcript)
        if transcript_id:
            # Update categories and summary
            db.update_categories(video_id, categories)
            db.update_transcript_summary(video_id, summary)
            st.success("Transcript processed, categorized, and summarized successfully!")
            
            # Only update state and redirect if not processing a playlist
            if not no_redirect:
                st.session_state.show_transcript_id = transcript_id
                st.session_state.current_command = "view_video"
                st.rerun()
        else:
            st.error("Failed to store transcript in database.")
            st.stop()
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        st.stop()

# Initialize category lists
CHRISTIAN_LIFE_CATEGORIES = [
    "Abortion", "Abuse", "Adoption", "Anger", "Anxiety", "Community", "Current Events", 
    "Dating", "Death", "Discipline", "Divorce", "Education", "Fatherhood", "Fear", 
    "Finances", "Forgiveness", "Gender", "Holiness", "Hypocrisy", "Identity", "Idolatry", 
    "Joy", "Marriage", "Motherhood", "Peace", "Politics", "Pride", "Purity", "Race", 
    "Relationships", "Rest", "Sexuality", "Singleness", "Suffering", "Suicide", 
    "Technology", "Wisdom", "Work"
]

CHURCH_MINISTRY_CATEGORIES = [
    "Adults", "Baptism", "Care", "Church", "Church Planting", "Church-Planting", 
    "Connections", "Disciple Groups", "Discipleship", "Faith", "Family Discipleship", 
    "Fasting", "Giving", "Global Missions", "Grace", "Kids", "Leadership", 
    "Local Missions", "Men", "Missional Living", "Missions", "Multisite", "Persecution", 
    "Prayer", "School of Ministry", "Serving", "Students", "The Church of Eleven22", 
    "Women", "World Religions", "Worship"
]

THEOLOGY_CATEGORIES = [
    "Creation", "End Times", "False Teaching", "Heaven and Hell", "Revelation", 
    "Salvation", "Sanctification", "Sin", "Sound Doctrine", "Spiritual Gifts", 
    "Spiritual Warfare", "The Bible", "The Birth of Christ", "The Character of God", 
    "The Death of Christ", "The Fall", "The Gathering", "The Gospel", "The Holy Spirit", 
    "The Kingdom of God", "The Law", "The Lord's Supper", "The Ministry of Christ", 
    "The Resurrection of Christ", "The Return of Christ", "The Sovereignty of God", 
    "Theology", "Trinitarianism", "Union with Christ"
]

# Load environment variables from .env file
load_dotenv()

# Set Supabase environment variables
os.environ["NEXT_PUBLIC_SUPABASE_URL"] = "https://cnfqqutobbpgrfqxqnxt.supabase.co"
os.environ["NEXT_PUBLIC_SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNuZnFxdXRvYmJwZ3JmcXhxbnh0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzMzMjEzNzYsImV4cCI6MjA0ODg5NzM3Nn0.IXKF8ZRhgR5eVdmcxWfw7r33T3DzHZMgr6c-Wsqj4Nc"

# Page is already configured at the top of the file

# Initialize database connection
db = Database()
youtube = YouTubeHelper()
processor = TranscriptProcessor()
parser = CommandParser()
ai_helper = AIHelper()  # Create an AIHelper instance

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
    st.title("Sermon Search")
    st.markdown("---")
    
    if st.button("➕ Add Video(s)", use_container_width=True):
        st.session_state.current_command = "add_videos"
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
    if st.button("💾 Export Data", use_container_width=True):
        st.session_state.current_command = "export"
    st.markdown("---")
    with st.expander("ℹ️ Command Help"):
        st.markdown(parser.get_help().replace("\n", "<br>"), unsafe_allow_html=True)

# Main content area
if st.session_state.current_command == "add_videos":
    st.subheader("Add Video(s)")
    
    # Radio button to select input type
    input_type = st.radio("Select input type:", ["Single Video", "Playlist"])
    url = st.text_input("Enter YouTube URL", help="Enter a video URL or playlist URL")
    
    if input_type == "Playlist":
        batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=5, 
                             help="Number of videos to process in each batch")
    
    if st.button("Process", key="process_videos_btn"):
        if url:
            try:
                if input_type == "Single Video":
                    # Process single video
                    video_id = processor.extract_video_id(url)
                    
                    # Check if video already exists
                    existing_video = db.video_exists(video_id)
                    if existing_video:
                        st.info(f"This video '{existing_video['title']}' is already in the system.")
                        
                        # Initialize session state for action selection
                        if 'video_action' not in st.session_state:
                            st.session_state.video_action = None
                            
                        # Create a form for action selection
                        with st.form(key=f'video_action_form_{video_id}'):
                            action = st.radio(
                                "Choose an action:",
                                ["View Existing", "Re-process"],
                                key=f'action_radio_{video_id}'
                            )
                            
                            submitted = st.form_submit_button("Confirm Action")
                            if submitted:
                                if action == "View Existing":
                                    st.session_state.show_transcript_id = video_id
                                    st.session_state.current_command = "view_video"
                                    st.rerun()
                                else:  # Re-process
                                    process_single_video(video_id, existing_video['title'])
                    else:
                        process_single_video(video_id)
                
                else:  # Playlist processing
                    st.markdown("""
                    ### Processing Playlist
                    The videos will be processed in batches to handle large playlists efficiently.
                    You can monitor the progress below:
                    """)
                    
                    # Get videos from playlist using the youtube helper instance
                    try:
                        videos = youtube.get_playlist_videos(url)
                        st.info(f"Found {len(videos)} videos in playlist")
                        
                        # Check for existing videos
                        existing_videos = []
                        new_videos = []
                        for video in videos:
                            if db.video_exists(video['video_id']):
                                existing_videos.append(video)
                            else:
                                new_videos.append(video)
                        
                        if existing_videos:
                            st.info(f"Found {len(existing_videos)} videos that are already in the system.")
                            if st.button("Re-process existing videos", key="reprocess_playlist"):
                                new_videos.extend(existing_videos)
                            else:
                                st.write("Will only process new videos.")
                        
                        if new_videos:
                            progress_bar = st.progress(0)
                            processed_count = 0
                            errors = []
                            
                            for i, video in enumerate(new_videos):
                                try:
                                    with st.spinner(f"Processing video {i+1} of {len(new_videos)}: {video['title']}"):
                                        process_single_video(video['video_id'], video['title'], no_redirect=True)
                                        processed_count += 1
                                except Exception as e:
                                    errors.append(f"Error processing {video['title']}: {str(e)}")
                                progress_bar.progress((i + 1) / len(new_videos))
                            
                            # Show summary
                            if processed_count > 0:
                                st.success(f"Successfully processed {processed_count} videos!")
                            if errors:
                                st.error("Some videos failed to process:")
                                for error in errors:
                                    st.error(error)
                            
                            # Add a button to view all videos
                            if st.button("View All Videos", key="view_all_videos"):
                                st.session_state.current_command = "list"
                                st.rerun()
                        else:
                            st.info("No new videos to process.")
                    except Exception as e:
                        st.error(f"Error processing playlist: {str(e)}")
            except Exception as e:
                st.error(f"Error processing videos: {str(e)}")
        else:
            st.warning("Please enter a valid YouTube URL")

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
                            <p>Added: {t['created_at'][:19] if isinstance(t['created_at'], str) else t['created_at'].strftime('%Y-%m-%d %H:%M:%S')}</p>
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
        result = db.get_transcript(st.session_state.show_transcript_id)
        
        if result:
            # Display video title
            st.title(result['title'])
            
            # Embed YouTube video
            st.video(f"https://www.youtube.com/watch?v={result['video_id']}")
            
            # Create tabs for different sections
            transcript_tab, categories_tab, stories_tab, edit_tab = st.tabs([
                "📝 Transcript", 
                "🏷️ Categories",
                "📖 Personal Stories",
                "✏️ Edit"
            ])
            
            # Get categories
            categories = db.get_categories(st.session_state.show_transcript_id)
            
            with transcript_tab:
                st.markdown("### Full Transcript")
                st.markdown(result['transcript'])
                
                if result.get('ai_summary'):
                    with st.expander("View AI Summary"):
                        st.markdown(result['ai_summary'])
                else:
                    if st.button("Generate AI Summary", key="transcript_summary_btn"):
                        with st.spinner("Generating summary..."):
                            summary = ai_helper.generate_summary(result['transcript'])
                            if summary:
                                # Update transcript with summary
                                db.update_transcript_summary(st.session_state.show_transcript_id, summary)
                                st.success("Summary generated successfully!")
                                st.rerun()
            
            with categories_tab:
                st.markdown("### Categories")
                
                # Add debug expander at the top
                with st.expander("🔍 Categories Debug Information"):
                    st.markdown("### Current Categories in Database")
                    st.json(categories)
                    
                    st.markdown("### Category Lists")
                    st.markdown("**Christian Life Categories:**")
                    st.write(CHRISTIAN_LIFE_CATEGORIES)
                    st.markdown("**Church & Ministry Categories:**")
                    st.write(CHURCH_MINISTRY_CATEGORIES)
                    st.markdown("**Theology Categories:**")
                    st.write(THEOLOGY_CATEGORIES)
                    
                    if hasattr(st.session_state, 'categories_debug'):
                        debug = st.session_state.categories_debug
                        
                        st.markdown("### AI Processing Information")
                        st.markdown("#### Input")
                        st.write(f"Transcript Length: {len(debug.get('input_transcript', ''))} characters")
                        
                        st.markdown("#### AI Response")
                        st.json(debug.get('ai_response', {}))
                        
                        st.markdown("#### Parsed Categories")
                        st.json(debug.get('parsed_categories', {}))
                        
                        if debug.get('errors'):
                            st.markdown("#### Errors")
                            for error in debug['errors']:
                                st.error(error)
                
                # Get current categories
                current_categories = categories if categories else {
                    'christian_life': [],
                    'church_ministry': [],
                    'theology': []
                }
                
                # Create columns for each category type
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**The Christian Life**")
                    selected_christian = st.multiselect(
                        "Select Christian Life categories",
                        options=CHRISTIAN_LIFE_CATEGORIES,
                        default=current_categories.get('christian_life', [])
                    )
                
                with col2:
                    st.markdown("**Church & Ministry**")
                    selected_ministry = st.multiselect(
                        "Select Church & Ministry categories",
                        options=CHURCH_MINISTRY_CATEGORIES,
                        default=current_categories.get('church_ministry', [])
                    )
                
                with col3:
                    st.markdown("**Theology**")
                    selected_theology = st.multiselect(
                        "Select Theology categories",
                        options=THEOLOGY_CATEGORIES,
                        default=current_categories.get('theology', [])
                    )
                
                # Create a callback to handle category changes
                def on_category_change():
                    new_categories = {
                        'christian_life': selected_christian,
                        'church_ministry': selected_ministry,
                        'theology': selected_theology
                    }
                    if db.update_categories(st.session_state.show_transcript_id, new_categories):
                        st.success("Categories updated automatically!")
                        st.rerun()
                    else:
                        st.error("Failed to update categories")

                # Check if any category has changed
                if ('prev_christian' not in st.session_state or st.session_state.prev_christian != selected_christian or
                    'prev_ministry' not in st.session_state or st.session_state.prev_ministry != selected_ministry or
                    'prev_theology' not in st.session_state or st.session_state.prev_theology != selected_theology):
                    
                    st.session_state.prev_christian = selected_christian
                    st.session_state.prev_ministry = selected_ministry
                    st.session_state.prev_theology = selected_theology
                    on_category_change()
                
                # Add button to regenerate categories
                col1, col2 = st.columns(2)
                with col1:
                    if categories:
                        if st.button("Regenerate Categories"):
                            with st.spinner("Analyzing transcript and generating categories..."):
                                try:
                                    ai_response = ai_helper.categorize_transcript(result['transcript'])
                                    new_categories = ai_response['categories']
                                    
                                    # Store debug info in session state
                                    st.session_state.categories_debug = {
                                        'input_transcript': ai_response['debug']['input_transcript'],
                                        'ai_response': ai_response['debug']['ai_response'],
                                        'parsed_categories': ai_response['debug']['parsed_categories'],
                                        'errors': ai_response['debug'].get('errors', [])
                                    }
                                    
                                    # Update categories in database
                                    if db.update_categories(st.session_state.show_transcript_id, new_categories):
                                        # Fetch the updated categories
                                        categories = db.get_categories(st.session_state.show_transcript_id)
                                        st.success("Categories regenerated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to update categories in database")
                                except Exception as e:
                                    st.error(f"Error processing categories: {str(e)}")
                                    st.session_state.categories_debug = {
                                        'errors': [str(e)]
                                    }
                    else:
                        if st.button("Generate Categories"):
                            with st.spinner("Analyzing transcript and generating categories..."):
                                try:
                                    ai_response = ai_helper.categorize_transcript(result['transcript'])
                                    new_categories = ai_response['categories']
                                    
                                    # Store debug info in session state
                                    st.session_state.categories_debug = {
                                        'input_transcript': ai_response['debug']['input_transcript'],
                                        'ai_response': ai_response['debug']['ai_response'],
                                        'parsed_categories': ai_response['debug']['parsed_categories'],
                                        'errors': ai_response['debug'].get('errors', [])
                                    }
                                    
                                    # Update categories in database
                                    if db.update_categories(st.session_state.show_transcript_id, new_categories):
                                        st.success("Categories generated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to save categories to database")
                                except Exception as e:
                                    st.error(f"Error generating categories: {str(e)}")
                                    st.session_state.categories_debug = {
                                        'errors': [str(e)]
                                    }
            
            with stories_tab:
                st.markdown("### Personal Stories")
                stories_col1, stories_col2 = st.columns([3, 1])
                
                with stories_col2:
                    if st.button("Extract Stories"):
                        with st.spinner("Analyzing transcript for personal stories..."):
                            extraction_result = ai_helper.extract_personal_stories(result['transcript'])
                            
                            if extraction_result.get("rate_limited"):
                                st.error("⚠️ API rate limit reached. Please wait about an hour before trying again.")
                            else:
                                stories = extraction_result["stories"]
                                st.session_state.debug_info = extraction_result["debug"]  # Store debug info
                                db.update_personal_stories(st.session_state.show_transcript_id, stories)
                                st.success("Stories extracted successfully!")
                                st.rerun()

                # Get stories from database
                stories = db.get_personal_stories(st.session_state.show_transcript_id)
                
                if not stories:
                    st.info("No personal stories have been extracted from this sermon yet. Click 'Extract Stories' to analyze the transcript for personal stories and anecdotes.")
                else:
                    st.write(f"Found {len(stories)} stories in the database")
                    for idx, story in enumerate(stories, 1):
                        with st.expander(f"📖 {story.get('title', 'Untitled Story')}", expanded=idx==1):
                            st.markdown(f"**Summary:** {story.get('summary', 'No summary available')}")
                            st.markdown(f"**Key Message:** {story.get('message', 'No message available')}")

                # Add debug expander
                with st.expander("🔍 Debug Information"):
                    st.markdown("### Current Database Stories")
                    st.json(stories)
                    
                    st.markdown("### Latest AI Extraction")
                    if hasattr(st.session_state, 'debug_info'):
                        debug = st.session_state.debug_info
                        
                        st.markdown("#### Process Information")
                        st.write(f"- Input Length: {debug['input_length']} characters")
                        st.write(f"- Number of Story Sections: {debug.get('num_sections', 0)}")
                        st.write(f"- Stories Found: {debug.get('final_story_count', 0)}")
                        
                        if debug.get('errors'):
                            st.markdown("#### Errors")
                            for error in debug['errors']:
                                st.error(error)
                        
                        st.markdown("#### Raw AI Response")
                        st.text(debug.get('ai_response', 'No response available'))
                        
                        st.markdown("#### Parsed Stories")
                        st.json(debug.get('parsed_stories', []))
                    else:
                        st.info("No AI extraction data available yet. Click 'Extract Stories' to see the AI response.")

                # Display AI Summary if available
                st.markdown("### AI Summary")
                if result.get('ai_summary'):
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
                else:
                    st.warning("AI summarization not available.")
                    if st.button("Generate AI Summary", key="categories_summary_btn"):
                        with st.spinner("Generating AI summary..."):
                            summary = ai_helper.generate_summary(result['transcript'])
                            # Update the database with the new summary
                            if db.update_transcript_summary(st.session_state.show_transcript_id, summary):
                                st.success("Summary generated successfully!")
                            else:
                                st.error("Failed to update summary")
                            st.rerun()

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