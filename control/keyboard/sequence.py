"""
Keyboard sequence builder for Control component.
Handles building sequences of keyboard actions.
"""

import logging
import time
import random
from typing import Dict, List, Optional, Any, Union, Tuple

from ..config import Config

class KeyboardSequence:
    """
    Builds sequences of keyboard actions.
    """
    
    def __init__(self):
        # Get configuration
        self.config = Config()
        
        # Initialize logging
        self.logger = logging.getLogger("KeyboardSequence")
        
        # Typing parameters
        self.typing_delay_range = (0.05, 0.15)  # Default typing delay range
    
    def build_typing_sequence(self, text: str, delay_range: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
        """
        Build typing sequence for text
        
        Args:
            text: Text to type
            delay_range: Optional custom delay range
            
        Returns:
            List of action dictionaries
        """
        if delay_range is None:
            delay_range = self.typing_delay_range
            
        sequence = []
        
        # Add typing actions
        for char in text:
            # Calculate delay
            delay = random.uniform(delay_range[0], delay_range[1])
            
            # Add action
            sequence.append({
                "action": "type",
                "text": char,
                "delay_after": delay
            })
        
        return sequence
    
    def build_dictation_sequence(self, text: str) -> List[Dict[str, Any]]:
        """
        Build dictation-style typing sequence
        
        Args:
            text: Text to type
            
        Returns:
            List of action dictionaries
        """
        sequence = []
        
        # Split into words
        words = text.split()
        
        # Add typing actions with word-level delays
        for i, word in enumerate(words):
            # Type word
            sequence.append({
                "action": "type",
                "text": word,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Add space after word (except last word)
            if i < len(words) - 1:
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.1, 0.3)
                })
                
                # Occasionally add longer thinking pauses
                if random.random() < 0.1:  # 10% chance
                    sequence.append({
                        "action": "delay",
                        "duration": random.uniform(0.5, 1.5)
                    })
            
        return sequence
    
    def build_autofill_sequence(self, text: str) -> List[Dict[str, Any]]:
        """
        Build autofill-style typing sequence
        
        Args:
            text: Text to type
            
        Returns:
            List of action dictionaries
        """
        sequence = []
        
        # For autofill, we type a portion then select suggestion
        if " " in text:
            # For phrases, type first few words
            words = text.split()
            prefix = " ".join(words[:min(2, len(words))])
            
            # Type prefix
            sequence.append({
                "action": "type",
                "text": prefix,
                "delay_after": random.uniform(0.2, 0.4)
            })
            
            # Pause to view suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.5, 0.8)
            })
            
            # Select suggestion (replace with full text)
            sequence.append({
                "action": "select_all",
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        else:
            # For single words, just type it
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        
        return sequence
    
    def build_clipboard_sequence(self, text: str) -> List[Dict[str, Any]]:
        """
        Build clipboard paste sequence
        
        Args:
            text: Text to paste
            
        Returns:
            List of action dictionaries
        """
        sequence = []
        
        # Set clipboard
        sequence.append({
            "action": "clipboard_set",
            "text": text,
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Paste
        sequence.append({
            "action": "paste",
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        return sequence
