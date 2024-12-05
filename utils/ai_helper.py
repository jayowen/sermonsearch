import os
import anthropic
from typing import Optional, Dict, Any, List
import json
import re

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
                system="You are an expert at summarizing video transcripts. Focus on extracting key points and main ideas. Be concise and highlight the most important information. Provide only the summary text without any prefixes or explanatory text.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = message.content[0].text
            # Remove any common prefixes that might appear
            prefixes_to_remove = [
                "Here is a concise summary of the transcript:",
                "Here is a summary of the key points from the transcript:",
                "Here's a summary of the transcript:",
                "Summary:",
                "Here is a summary:"
            ]
            for prefix in prefixes_to_remove:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            
            return summary
            
        except Exception as e:
            print(f"Error generating AI summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def categorize_transcript(self, text: str) -> Dict[str, Any]:
        """Categorize the transcript into predefined categories."""
        try:
            # Define category lists here to avoid circular imports
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
            
            if not text or len(text.strip()) < 10:
                return {
                    'categories': {
                        'christian_life': [],
                        'church_ministry': [],
                        'theology': []
                    },
                    'debug': {
                        'input_transcript': text,
                        'ai_response': None,
                        'parsed_categories': None,
                        'errors': ['Text too short to process']
                    }
                }

            # Limit text length to prevent token overflow
            max_chars = 50000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            # Create a prompt that asks for categorization with explicit category lists
            prompt = """Please analyze this sermon transcript and categorize it into the following three category types. Only use categories from these exact lists:

1. Christian Life - Choose from:
Abortion, Abuse, Adoption, Anger, Anxiety, Community, Current Events, Dating, Death, Discipline, Divorce, Education, Fatherhood, Fear, Finances, Forgiveness, Gender, Holiness, Hypocrisy, Identity, Idolatry, Joy, Marriage, Motherhood, Peace, Politics, Pride, Purity, Race, Relationships, Rest, Sexuality, Singleness, Suffering, Suicide, Technology, Wisdom, Work

2. Church & Ministry - Choose from:
Adults, Baptism, Care, Church, Church Planting, Church-Planting, Connections, Disciple Groups, Discipleship, Faith, Family Discipleship, Fasting, Giving, Global Missions, Grace, Kids, Leadership, Local Missions, Men, Missional Living, Missions, Multisite, Persecution, Prayer, School of Ministry, Serving, Students, The Church of Eleven22, Women, World Religions, Worship

3. Theology - Choose from:
Creation, End Times, False Teaching, Heaven and Hell, Revelation, Salvation, Sanctification, Sin, Sound Doctrine, Spiritual Gifts, Spiritual Warfare, The Bible, The Birth of Christ, The Character of God, The Death of Christ, The Fall, The Gathering, The Gospel, The Holy Spirit, The Kingdom of God, The Law, The Lord's Supper, The Ministry of Christ, The Resurrection of Christ, The Return of Christ, The Sovereignty of God, Theology, Trinitarianism, Union with Christ

Only select categories that are explicitly mentioned or strongly implied in the transcript. Format your response as a JSON object with three arrays containing ONLY categories from the above lists, like this:
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
                system="You are an expert at analyzing sermon transcripts and categorizing them accurately. Return only valid categories from the predefined lists in a strict JSON format.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Get the response text
            response_text = message.content[0].text.strip()
            
            # Initialize debug info
            debug_info = {
                'input_transcript': text[:1000] + '...' if len(text) > 1000 else text,
                'ai_response': response_text,
                'parsed_categories': None,
                'errors': []
            }
            
            # Try to extract JSON from the response
            try:
                # Find the first occurrence of '{'
                json_start = response_text.find('{')
                if json_start != -1:
                    # Find the matching closing brace
                    count = 1
                    json_end = json_start + 1
                    while count > 0 and json_end < len(response_text):
                        if response_text[json_end] == '{':
                            count += 1
                        elif response_text[json_end] == '}':
                            count -= 1
                        json_end += 1
                    
                    if count == 0:
                        json_str = response_text[json_start:json_end]
                        categories = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No valid JSON object found", response_text, 0)
                else:
                    raise json.JSONDecodeError("No JSON object found", response_text, 0)
            except json.JSONDecodeError as e:
                # If direct parsing fails, try to extract JSON structure
                json_match = re.search(r'\{[\s\S]*?\}(?=\s*$)', response_text)
                if json_match:
                    try:
                        categories = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        debug_info['errors'].append(f"Failed to parse JSON: {str(e)}")
                        categories = {"christian_life": [], "church_ministry": [], "theology": []}
                else:
                    debug_info['errors'].append("No valid JSON structure found in response")
                    categories = {"christian_life": [], "church_ministry": [], "theology": []}

            # Validate categories against predefined lists
            validated_categories = {
                'christian_life': [cat for cat in categories.get('christian_life', []) 
                                 if cat in CHRISTIAN_LIFE_CATEGORIES],
                'church_ministry': [cat for cat in categories.get('church_ministry', []) 
                                  if cat in CHURCH_MINISTRY_CATEGORIES],
                'theology': [cat for cat in categories.get('theology', []) 
                           if cat in THEOLOGY_CATEGORIES]
            }
            
            debug_info['parsed_categories'] = validated_categories
            
            return {
                'categories': validated_categories,
                'debug': debug_info
            }
            
        except Exception as e:
            print(f"Error categorizing transcript: {str(e)}")
            return {
                'categories': {
                    'christian_life': [],
                    'church_ministry': [],
                    'theology': []
                },
                'debug': {
                    'input_transcript': text[:1000] + '...' if text else '',
                    'ai_response': None,
                    'parsed_categories': None,
                    'errors': [str(e)]
                }
            }

    def extract_personal_stories(self, text: str) -> Dict[str, Any]:
        """Extract personal stories from the transcript."""
        try:
            if not text or len(text.strip()) < 100:
                return {
                    "stories": [],
                    "debug": {
                        "input_length": len(text) if text else 0,
                        "errors": ["Text too short to process"]
                    },
                    "rate_limited": False
                }

            # Limit text length to prevent token overflow
            max_chars = 50000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            # Create prompt for story extraction
            prompt = """Does this sermon include any personal stories, anecdotes, or examples shared by the speaker to illustrate the message? For each story or example found, please provide:

1. A brief title for the story/example
2. A concise summary of what happened
3. The key message or lesson the speaker was illustrating

Format your response strictly as a JSON object with a 'stories' array containing objects with 'title', 'summary', and 'message' fields. Example:
{
    "stories": [
        {
            "title": "The Lost Sheep",
            "summary": "A shepherd left his 99 sheep to find one that was lost in the mountains",
            "message": "God's love for each individual is personal and pursuing"
        }
    ]
}

Only include actual personal stories or specific examples, not general teachings or biblical passages unless they're part of a personal anecdote.

Here's the sermon transcript to analyze:

""" + text

            # Generate story analysis using Claude
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0.7,
                system="You are an expert at analyzing sermon transcripts and identifying personal stories and anecdotes. Extract meaningful stories that illustrate key points. Always respond with valid JSON containing a 'stories' array, even if no stories are found.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Get the response text
            response_text = message.content[0].text.strip()
            
            try:
                # First try direct JSON parsing
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If direct parsing fails, try to extract JSON structure
                json_match = re.search(r'\{[\s\S]*?\}(?=\s*$)', response_text)
                if json_match:
                    try:
                        parsed_data = json.loads(json_match.group(0))
                    except json.JSONDecodeError as nested_e:
                        debug_info["errors"].append({
                            "error_type": "JSON Parse Error",
                            "message": str(nested_e),
                            "context": response_text[:100] + "..." if len(response_text) > 100 else response_text,
                            "position": nested_e.pos,
                            "line_number": nested_e.lineno if hasattr(nested_e, 'lineno') else None
                        })
                        parsed_data = {"stories": []}
                else:
                    debug_info["errors"].append({
                        "error_type": "JSON Structure Error",
                        "message": str(e),
                        "context": response_text[:100] + "..." if len(response_text) > 100 else response_text,
                        "raw_response": response_text
                    })
                    parsed_data = {"stories": []}

            # Ensure we have a valid stories array
            if not isinstance(parsed_data, dict) or "stories" not in parsed_data:
                parsed_data = {"stories": []}

            # Add debug information
            debug_info = {
                "input_length": len(text),
                "ai_response": response_text,
                "parsed_stories": parsed_data.get("stories", []),
                "final_story_count": len(parsed_data.get("stories", [])),
                "errors": []
            }

            return {
                "stories": parsed_data.get("stories", []),
                "debug": debug_info,
                "rate_limited": False
            }

        except Exception as e:
            print(f"Error extracting stories: {str(e)}")
            return {
                "stories": [],
                "debug": {
                    "input_length": len(text) if text else 0,
                    "errors": [str(e)]
                },
                "rate_limited": "rate limit" in str(e).lower()
            }
