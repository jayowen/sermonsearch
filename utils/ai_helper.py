import os
import anthropic
from typing import Optional

class AIHelper:
    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ImportError("ANTHROPIC_API_KEY not found in environment")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_summary(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary of the given text using Claude AI."""
        try:
            if not text or len(text.strip()) < 10:
                return "Text is too short to summarize."

            # Limit text length to prevent token overflow
            max_chars = 50000  # Conservative limit to stay within token bounds
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            # Create a prompt that asks for a concise summary
            prompt = f"Please provide a clear and concise summary of the following transcript. Focus on the main points and key takeaways:\n\n{text}"
            
            if max_length:
                prompt += f"\n\nPlease keep the summary within approximately {max_length} words."

            # Generate summary using Claude
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0.7,
                system="You are an expert at summarizing video transcripts. Focus on extracting key points and main ideas. Be concise and highlight the most important information.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Error generating AI summary: {str(e)}")
            return f"Error generating summary: {str(e)}"
    def categorize_transcript(self, text: str) -> dict:
        """Categorize the transcript into predefined categories."""
        try:
            if not text or len(text.strip()) < 10:
                return {
                    'christian_life': [],
                    'church_ministry': [],
                    'theology': []
                }

            # Limit text length to prevent token overflow
            max_chars = 50000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            # Create a prompt that asks for categorization
            prompt = """Please analyze this sermon transcript and categorize it into the following three category types:

1. Christian Life (e.g., Abortion, Adoption, Anxiety, Community, Dating, Marriage, etc.)
2. Church & Ministry (e.g., Baptism, Church, Discipleship, Leadership, Missions, etc.)
3. Theology (e.g., Creation, Salvation, Sin, The Bible, The Gospel, etc.)

For each category type, return only the most relevant categories. Please format your response as a JSON object with three arrays.
Example format:
{
    "christian_life": ["Marriage", "Community"],
    "church_ministry": ["Discipleship"],
    "theology": ["The Gospel", "Salvation"]
}

Here's the transcript to analyze:

""" + text

            # Generate categories using Claude
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0.7,
                system="You are an expert at analyzing sermon transcripts and categorizing them accurately. Return only valid categories from the predefined lists in a JSON format.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response as JSON
            response_text = message.content[0].text
            # Extract JSON part if there's additional text
            import json
            import re
            
            # Find JSON-like structure in the response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                response_text = json_match.group(0)
            
            categories = json.loads(response_text)
            
            # Validate categories against predefined lists
            from main import CHRISTIAN_LIFE_CATEGORIES, CHURCH_MINISTRY_CATEGORIES, THEOLOGY_CATEGORIES
            
            validated_categories = {
                'christian_life': [cat for cat in categories.get('christian_life', []) if cat in CHRISTIAN_LIFE_CATEGORIES],
                'church_ministry': [cat for cat in categories.get('church_ministry', []) if cat in CHURCH_MINISTRY_CATEGORIES],
                'theology': [cat for cat in categories.get('theology', []) if cat in THEOLOGY_CATEGORIES]
            }
            
            return validated_categories
            
        except Exception as e:
            print(f"Error categorizing transcript: {str(e)}")
            return {
                'christian_life': [],
                'church_ministry': [],
                'theology': []
            }

