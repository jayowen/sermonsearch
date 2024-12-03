from typing import Dict, Callable, List, Tuple
import re

class CommandParser:
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self.help_text: Dict[str, str] = {}

    def register(self, command: str, handler: Callable, help_text: str):
        """Register a new command with its handler and help text."""
        self.commands[command] = handler
        self.help_text[command] = help_text

    def parse(self, input_text: str) -> Tuple[Callable, List[str]]:
        """Parse input text into command and arguments."""
        if not input_text:
            raise ValueError("Empty command")

        parts = input_text.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        if command not in self.commands:
            raise ValueError(f"Unknown command: {command}")

        return self.commands[command], args

    def get_help(self, command: str = None) -> str:
        """Get help text for a specific command or all commands."""
        if command:
            return self.help_text.get(command, "Command not found")
        
        return "\n".join([
            f"{cmd}: {help}" for cmd, help in self.help_text.items()
        ])
