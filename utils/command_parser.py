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
    def extract_keywords(text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """Extract the most frequent meaningful words as keywords."""
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        words = [w for w in words if w.isalnum() and w not in stop_words]
        
        return Counter(words).most_common(top_n)

    @staticmethod
    def summarize_text(text: str, sentences: int = 3) -> str:
        """Create a simple extractive summary of the text."""
        # Split into sentences and tokenize
        sents = sent_tokenize(text)
        words = word_tokenize(text.lower())
        
        # Remove stopwords and get word frequencies
        stop_words = set(stopwords.words('english'))
        word_freq = Counter(w for w in words if w.isalnum() and w not in stop_words)
        
        # Score sentences based on word frequencies
        sent_scores = []
        for sent in sents:
            score = sum(word_freq.get(word.lower(), 0) 
                       for word in word_tokenize(sent) 
                       if word.lower() not in stop_words)
            sent_scores.append((sent, score))
        
        # Get top sentences
        summary_sents = sorted(sent_scores, key=lambda x: x[1], reverse=True)[:sentences]
        summary_sents = sorted(summary_sents, key=lambda x: sents.index(x[0]))
        
        return ' '.join(sent for sent, score in summary_sents)
