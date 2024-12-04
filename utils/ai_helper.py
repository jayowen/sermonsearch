import os
import anthropic
from typing import Optional

class AIHelper:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get('ANTHROPIC_API_KEY')
        )

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
