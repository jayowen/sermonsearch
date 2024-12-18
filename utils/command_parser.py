from typing import Dict, Callable, List, Tuple, Optional
import re
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

class TranscriptCommand:
    def __init__(self, name: str, description: str, handler: Callable):
        self.name = name
        self.description = description
        self.handler = handler

class CommandParser:
    def __init__(self):
        self.commands: Dict[str, TranscriptCommand] = {}
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        except Exception as e:
            print(f"Error downloading NLTK data: {str(e)}")
            pass

    def register(self, command: str, handler: Callable, help_text: str):
        """Register a new command with its handler and help text."""
        self.commands[command] = TranscriptCommand(command, help_text, handler)

    def parse(self, input_text: str) -> Tuple[Callable, List[str]]:
        """Parse input text into command and arguments."""
        if not input_text:
            raise ValueError("Empty command")

        parts = input_text.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        if command not in self.commands:
            raise ValueError(f"Unknown command: {command}")

        return self.commands[command].handler, args

    def get_help(self, command: str = None) -> str:
        """Get help text for a specific command or all commands."""
        if command:
            cmd = self.commands.get(command)
            return cmd.description if cmd else "Command not found"
        
        return "\n".join([
            f"{cmd.name}: {cmd.description}" for cmd in self.commands.values()
        ])

    @staticmethod
    def get_word_stats(text: str) -> Dict[str, any]:
        """Get basic statistics about the text."""
        words = word_tokenize(text.lower())
        sentences = sent_tokenize(text)
        stop_words = set(stopwords.words('english'))
        words_no_stop = [w for w in words if w.isalnum() and w not in stop_words]
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'unique_words': len(set(words_no_stop))
        }

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10, min_length: int = 3) -> List[Tuple[str, int]]:
        """Extract the most frequent meaningful words as keywords."""
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        # Filter words: must be alphanumeric, not in stop words, and longer than min_length
        words = [w for w in words if w.isalnum() and w not in stop_words and len(w) >= min_length]
        
        return Counter(words).most_common(top_n)

    @staticmethod
    def get_word_frequency(text: str, min_count: int = 2) -> List[Tuple[str, int]]:
        """Get word frequency analysis with minimum count filter."""
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        words = [w for w in words if w.isalnum() and w not in stop_words]
        freq = Counter(words)
        return [(word, count) for word, count in freq.items() if count >= min_count]

    @staticmethod
    def extract_time_segments(transcript_text: str, segment_length: int = 300) -> List[str]:
        """Split transcript into time-based segments."""
        words = transcript_text.split()
        segments = []
        current_segment = []
        word_count = 0
        
        for word in words:
            current_segment.append(word)
            word_count += 1
            
            if word_count >= segment_length:
                segments.append(" ".join(current_segment))
                current_segment = []
                word_count = 0
        
        if current_segment:
            segments.append(" ".join(current_segment))
            
        return segments

    @staticmethod
    def find_key_phrases(text: str, min_words: int = 3, max_words: int = 6) -> List[Tuple[str, int]]:
        """Extract key phrases from the transcript."""
        sentences = sent_tokenize(text)
        stop_words = set(stopwords.words('english'))
        phrases = []
        
        for sentence in sentences:
            words = word_tokenize(sentence)
            current_phrase = []
            
            for word in words:
                if word.isalnum() and word.lower() not in stop_words:
                    current_phrase.append(word)
                else:
                    if min_words <= len(current_phrase) <= max_words:
                        phrases.append(" ".join(current_phrase))
                    current_phrase = []
            
            if min_words <= len(current_phrase) <= max_words:
                phrases.append(" ".join(current_phrase))
                
        return Counter(phrases).most_common(10)

    @staticmethod
    def summarize_text(text: str, max_length: int = None) -> str:
        """Generate a summary of the text using Claude AI."""
        try:
            if not text or not isinstance(text, str):
                return "No text available for summarization."

            if len(text.strip()) < 100:  # Don't summarize very short texts
                return text

            from utils.ai_helper import AIHelper
            ai = AIHelper()
            summary = ai.generate_summary(text, max_length)
            return summary if summary else "Summary generation skipped."
            
        except ImportError:
            return "AI summarization not available."
        except Exception as e:
            print(f"Error in summarize_text: {str(e)}")
            return "Summary generation failed."
