from googleapiclient.discovery import build
from typing import List, Dict
import os
import isodate

class YouTubeHelper:
    @staticmethod
    def get_playlist_videos(playlist_url: str) -> List[Dict[str, str]]:
        """Get all video IDs and titles from a playlist."""
        playlist_id = YouTubeHelper._extract_playlist_id(playlist_url)
        
        youtube = build('youtube', 'v3', developerKey=os.environ.get('YOUTUBE_API_KEY'))
        
        videos = []
        next_page_token = None
        
        while True:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            
            response = request.execute()
            
            for item in response['items']:
                videos.append({
                    'video_id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title']
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return videos

    @staticmethod
    def _extract_playlist_id(url: str) -> str:
        """Extract playlist ID from URL."""
        import re
        patterns = [
            r'(?:list=)([0-9A-Za-z_-]+)',
            r'(?:playlist\/)([0-9A-Za-z_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError("Invalid playlist URL")

    @staticmethod
    def get_video_info(video_id: str) -> Dict[str, str]:
        """Get video information from YouTube API."""
        youtube = build('youtube', 'v3', developerKey=os.environ.get('YOUTUBE_API_KEY'))
        
        try:
            request = youtube.videos().list(
                part="snippet",
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return {
                    'title': response['items'][0]['snippet']['title'],
                    'description': response['items'][0]['snippet']['description']
                }
            else:
                raise ValueError("Video not found")
                
        except Exception as e:
            raise Exception(f"Error fetching video info: {str(e)}")
