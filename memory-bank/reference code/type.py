#!/usr/bin/env python3
"""
Utility for typing text on a device with realistic input behavior.
Automatically selects between typing, dictation, and autofill based on content.
"""

import random
import time
import re
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any

# Add the project root to the path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.device_id_converter import get_ip_from_device_id
import keyboard_client

# Constants for typing simulation
TYPING_DELAY_RANGE = (0.032, 0.125)  # Base delay range between keypresses in seconds (based on tap duration analysis)
DICTATION_WORD_DELAY_RANGE = (0.2, 0.5)  # Delay between words in dictation
AUTOFILL_PROBABILITY = 0.2  # Probability of using autofill for eligible content
DICTATION_PROBABILITY = 0.15  # Probability of using dictation for eligible content
TYPO_PROBABILITY = 0.2  # Probability of making a typo for a word
AUTOCORRECT_PROBABILITY = 0.9  # Probability that autocorrect will fix a typo
BURST_TYPING_PROBABILITY = 0.7  # Probability of typing common words faster
BURST_TYPING_MODIFIER = 0.6  # Speed modifier for burst typing (lower = faster)
CAPITAL_LETTER_MODIFIER = 2.15  # Delay modifier for capital letters (except at start of sentence)
SPECIAL_CHAR_MODIFIER = (2.0, 3.0)  # Range of delay modifiers for special characters

# Tap movement parameters from statistical analysis
TAP_MOVEMENT_DISTANCE_MEAN = 12.01  # pixels
TAP_MOVEMENT_DISTANCE_STD = 9.16
TAP_MOVEMENT_DX_MEAN = -1.51  # pixels
TAP_MOVEMENT_DX_STD = 13.57
TAP_MOVEMENT_DY_MEAN = 0.87  # pixels
TAP_MOVEMENT_DY_STD = 6.40

# Quadrant distribution for movement direction
TAP_QUADRANT_PROBS = {
    'Q1 (right-down)': 0.3006,  # +x, +y
    'Q2 (left-down)': 0.3121,   # -x, +y
    'Q3 (left-up)': 0.2197,     # -x, -y
    'Q4 (right-up)': 0.1676     # +x, -y
}

# Common words that might be typed faster
COMMON_WORDS = {
    "the", "and", "a", "to", "of", "in", "is", "it", "you", "that", "he", "was", "for", 
    "on", "are", "with", "as", "I", "his", "they", "be", "at", "one", "have", "this", 
    "from", "or", "had", "by", "not", "word", "but", "what", "some", "we", "can", "out", 
    "other", "were", "all", "there", "when", "up", "use", "your", "how", "said", "an", 
    "each", "she", "which", "do", "their", "time", "if", "will", "way", "about", "many", 
    "then", "them", "write", "would", "like", "so", "these", "her", "long", "make", 
    "thing", "see", "him", "two", "has", "look", "more", "day", "could", "go", "come", 
    "did", "number", "sound", "no", "most", "people", "my", "over", "know", "water", 
    "than", "call", "first", "who", "may", "down", "side", "been", "now", "find", "any", 
    "new", "work", "part", "take", "get", "place", "made", "live", "where", "after", 
    "back", "little", "only", "round", "man", "year", "came", "show", "every", "good", 
    "me", "give", "our", "under", "name", "very", "through", "just", "form", "sentence", 
    "great", "think", "say", "help", "low", "line", "differ", "turn", "cause", "much", 
    "mean", "before", "move", "right", "boy", "old", "too", "same", "tell", "does", 
    "set", "three", "want", "air", "well", "also", "play", "small", "end", "put", "home", 
    "read", "hand", "port", "large", "spell", "add", "even", "land", "here", "must", 
    "big", "high", "such", "follow", "act", "why", "ask", "men", "change", "went", 
    "light", "kind", "off", "need", "house", "picture", "try", "us", "again", "animal", 
    "point", "mother", "world", "near", "build", "self", "earth", "father", "head", 
    "stand", "own", "page", "should", "country", "found", "answer", "school", "grow", 
    "study", "still", "learn", "plant", "cover", "food", "sun", "four", "between", 
    "state", "keep", "eye", "never", "last", "let", "thought", "city", "tree", "cross", 
    "farm", "hard", "start", "might", "story", "saw", "far", "sea", "draw", "left", 
    "late", "run", "don't", "while", "press", "close", "night", "real", "life", "few", 
    "north", "open", "seem", "together", "next", "white", "children", "begin", "got", 
    "walk", "example", "ease", "paper", "group", "always", "music", "those", "both", 
    "mark", "often", "letter", "until", "mile", "river", "car", "feet", "care", "second", 
    "book", "carry", "took", "science", "eat", "room", "friend", "began", "idea", "fish", 
    "mountain", "stop", "once", "base", "hear", "horse", "cut", "sure", "watch", "color", 
    "face", "wood", "main", "enough", "plain", "girl", "usual", "young", "ready", "above", 
    "ever", "red", "list", "though", "feel", "talk", "bird", "soon", "body", "dog", 
    "family", "direct", "pose", "leave", "song", "measure", "door", "product", "black", 
    "short", "numeral", "class", "wind", "question", "happen", "complete", "ship", "area", 
    "half", "rock", "order", "fire", "south", "problem", "piece", "told", "knew", "pass", 
    "since", "top", "whole", "king", "space", "heard", "best", "hour", "better", "true", 
    "during", "hundred", "five", "remember", "step", "early", "hold", "west", "ground", 
    "interest", "reach", "fast", "verb", "sing", "listen", "six", "table", "travel", 
    "less", "morning", "ten", "simple", "several", "vowel", "toward", "war", "lay", 
    "against", "pattern", "slow", "center", "love", "person", "money", "serve", "appear", 
    "road", "map", "rain", "rule", "govern", "pull", "cold", "notice", "voice", "unit", 
    "power", "town", "fine", "certain", "fly", "fall", "lead", "cry", "dark", "machine", 
    "note", "wait", "plan", "figure", "star", "box", "noun", "field", "rest", "correct", 
    "able", "pound", "done", "beauty", "drive", "stood", "contain", "front", "teach", 
    "week", "final", "gave", "green", "oh", "quick", "develop", "ocean", "warm", "free", 
    "minute", "strong", "special", "mind", "behind", "clear", "tail", "produce", "fact", 
    "street", "inch", "multiply", "nothing", "course", "stay", "wheel", "full", "force", 
    "blue", "object", "decide", "surface", "deep", "moon", "island", "foot", "system", 
    "busy", "test", "record", "boat", "common", "gold", "possible", "plane", "stead", 
    "dry", "wonder", "laugh", "thousand", "ago", "ran", "check", "game", "shape", 
    "equate", "hot", "miss", "brought", "heat", "snow", "tire", "bring", "yes", "distant", 
    "fill", "east", "paint", "language", "among", "grand", "ball", "yet", "wave", "drop", 
    "heart", "am", "present", "heavy", "dance", "engine", "position", "arm", "wide", 
    "sail", "material", "size", "vary", "settle", "speak", "weight", "general", "ice", 
    "matter", "circle", "pair", "include", "divide", "syllable", "felt", "perhaps", 
    "pick", "sudden", "count", "square", "reason", "length", "represent", "art", "subject", 
    "region", "energy", "hunt", "probable", "bed", "brother", "egg", "ride", "cell", 
    "believe", "fraction", "forest", "sit", "race", "window", "store", "summer", "train", 
    "sleep", "prove", "lone", "leg", "exercise", "wall", "catch", "mount", "wish", 
    "sky", "board", "joy", "winter", "sat", "written", "wild", "instrument", "kept", 
    "glass", "grass", "cow", "job", "edge", "sign", "visit", "past", "soft", "fun", 
    "bright", "gas", "weather", "month", "million", "bear", "finish", "happy", "hope", 
    "flower", "clothe", "strange", "gone", "jump", "baby", "eight", "village", "meet", 
    "root", "buy", "raise", "solve", "metal", "whether", "push", "seven", "paragraph", 
    "third", "shall", "held", "hair", "describe", "cook", "floor", "either", "result", 
    "burn", "hill", "safe", "cat", "century", "consider", "type", "law", "bit", "coast", 
    "copy", "phrase", "silent", "tall", "sand", "soil", "roll", "temperature", "finger", 
    "industry", "value", "fight", "lie", "beat", "excite", "natural", "view", "sense", 
    "ear", "else", "quite", "broke", "case", "middle", "kill", "son", "lake", "moment", 
    "scale", "loud", "spring", "observe", "child", "straight", "consonant", "nation", 
    "dictionary", "milk", "speed", "method", "organ", "pay", "age", "section", "dress", 
    "cloud", "surprise", "quiet", "stone", "tiny", "climb", "cool", "design", "poor", 
    "lot", "experiment", "bottom", "key", "iron", "single", "stick", "flat", "twenty", 
    "skin", "smile", "crease", "hole", "trade", "melody", "trip", "office", "receive", 
    "row", "mouth", "exact", "symbol", "die", "least", "trouble", "shout", "except", 
    "wrote", "seed", "tone", "join", "suggest", "clean", "break", "lady", "yard", "rise", 
    "bad", "blow", "oil", "blood", "touch", "grew", "cent", "mix", "team", "wire", "cost", 
    "lost", "brown", "wear", "garden", "equal", "sent", "choose", "fell", "fit", "flow", 
    "fair", "bank", "collect", "save", "control", "decimal", "gentle", "woman", "captain", 
    "practice", "separate", "difficult", "doctor", "please", "protect", "noon", "whose", 
    "locate", "ring", "character", "insect", "caught", "period", "indicate", "radio", 
    "spoke", "atom", "human", "history", "effect", "electric", "expect", "crop", "modern", 
    "element", "hit", "student", "corner", "party", "supply", "bone", "rail", "imagine", 
    "provide", "agree", "thus", "capital", "won't", "chair", "danger", "fruit", "rich", 
    "thick", "soldier", "process", "operate", "guess", "necessary", "sharp", "wing", 
    "create", "neighbor", "wash", "bat", "rather", "crowd", "corn", "compare", "poem", 
    "string", "bell", "depend", "meat", "rub", "tube", "famous", "dollar", "stream", 
    "fear", "sight", "thin", "triangle", "planet", "hurry", "chief", "colony", "clock", 
    "mine", "tie", "enter", "major", "fresh", "search", "send", "yellow", "gun", "allow", 
    "print", "dead", "spot", "desert", "suit", "current", "lift", "rose", "continue", 
    "block", "chart", "hat", "sell", "success", "company", "subtract", "event", 
    "particular", "deal", "swim", "term", "opposite", "wife", "shoe", "shoulder", "spread", 
    "arrange", "camp", "invent", "cotton", "born", "determine", "quart", "nine", "truck", 
    "noise", "level", "chance", "gather", "shop", "stretch", "throw", "shine", "property", 
    "column", "molecule", "select", "wrong", "gray", "repeat", "require", "broad", "prepare", 
    "salt", "nose", "plural", "anger", "claim", "continent", "oxygen", "sugar", "death", 
    "pretty", "skill", "women", "season", "solution", "magnet", "silver", "thank", "branch", 
    "match", "suffix", "especially", "fig", "afraid", "huge", "sister", "steel", "discuss", 
    "forward", "similar", "guide", "experience", "score", "apple", "bought", "led", "pitch", 
    "coat", "mass", "card", "band", "rope", "slip", "win", "dream", "evening", "condition", 
    "feed", "tool", "total", "basic", "smell", "valley", "nor", "double", "seat", "arrive", 
    "master", "track", "parent", "shore", "division", "sheet", "substance", "favor", 
    "connect", "post", "spend", "chord", "fat", "glad", "original", "share", "station", 
    "dad", "bread", "charge", "proper", "bar", "offer", "segment", "slave", "duck", 
    "instant", "market", "degree", "populate", "chick", "dear", "enemy", "reply", "drink", 
    "occur", "support", "speech", "nature", "range", "steam", "motion", "path", "liquid", 
    "log", "meant", "quotient", "teeth", "shell", "neck"
}

# Common homophones for dictation errors
COMMON_HOMOPHONES = {
    "there": ["their", "they're"],
    "their": ["there", "they're"],
    "they're": ["their", "there"],
    "your": ["you're", "you've"],
    "you're": ["your", "you've"],
    "its": ["it's"],
    "it's": ["its"],
    "were": ["we're", "where"],
    "we're": ["were", "where"],
    "where": ["were", "we're"],
    "than": ["then"],
    "then": ["than"],
    "affect": ["effect"],
    "effect": ["affect"],
    "to": ["too", "two"],
    "too": ["to", "two"],
    "two": ["to", "too"],
    "accept": ["except"],
    "except": ["accept"],
    "weather": ["whether"],
    "whether": ["weather"],
    "hear": ["here"],
    "here": ["hear"],
    "break": ["brake"],
    "brake": ["break"],
    "piece": ["peace"],
    "peace": ["piece"],
    "principal": ["principle"],
    "principle": ["principal"],
    "complement": ["compliment"],
    "compliment": ["complement"],
    "desert": ["dessert"],
    "dessert": ["desert"],
    "capital": ["capitol"],
    "capitol": ["capital"],
    "stair": ["stare"],
    "stare": ["stair"],
    "sight": ["site", "cite"],
    "site": ["sight", "cite"],
    "cite": ["site", "sight"],
    "coarse": ["course"],
    "course": ["coarse"],
    "aloud": ["allowed"],
    "allowed": ["aloud"],
    "bear": ["bare"],
    "bare": ["bear"],
    "board": ["bored"],
    "bored": ["board"],
    "cereal": ["serial"],
    "serial": ["cereal"],
    "fair": ["fare"],
    "fare": ["fair"],
    "great": ["grate"],
    "grate": ["great"],
    "grown": ["groan"],
    "groan": ["grown"],
    "heal": ["heel"],
    "heel": ["heal"],
    "heard": ["herd"],
    "herd": ["heard"],
    "hour": ["our"],
    "our": ["hour"],
    "knight": ["night"],
    "night": ["knight"],
    "knot": ["not"],
    "not": ["knot"],
    "know": ["no"],
    "no": ["know"],
    "made": ["maid"],
    "maid": ["made"],
    "mail": ["male"],
    "male": ["mail"],
    "meat": ["meet"],
    "meet": ["meat"],
    "morning": ["mourning"],
    "mourning": ["morning"],
    "pair": ["pear", "pare"],
    "pear": ["pair", "pare"],
    "pare": ["pair", "pear"],
    "plain": ["plane"],
    "plane": ["plain"],
    "rain": ["reign", "rein"],
    "reign": ["rain", "rein"],
    "rein": ["rain", "reign"],
    "role": ["roll"],
    "roll": ["role"],
    "sail": ["sale"],
    "sale": ["sail"],
    "scene": ["seen"],
    "seen": ["scene"],
    "some": ["sum"],
    "sum": ["some"],
    "son": ["sun"],
    "sun": ["son"],
    "steal": ["steel"],
    "steel": ["steal"],
    "tail": ["tale"],
    "tale": ["tail"],
    "wait": ["weight"],
    "weight": ["wait"],
    "way": ["weigh"],
    "weigh": ["way"],
    "weak": ["week"],
    "week": ["weak"],
    "wear": ["where"],
    "where": ["wear"],
    "which": ["witch"],
    "witch": ["which"],
    "wood": ["would"],
    "would": ["wood"]
}

# Common typos for realistic typing errors
COMMON_TYPOS = {
    # Transposition errors (swapped letters)
    "the": ["teh"],
    "and": ["adn"],
    "for": ["fro"],
    "with": ["wiht"],
    "this": ["tihs"],
    "that": ["taht"],
    "what": ["waht"],
    "when": ["wehn"],
    "where": ["wehre"],
    "would": ["woudl"],
    "could": ["cuold"],
    "should": ["shuold"],
    "because": ["becuase"],
    "people": ["peopel"],
    "about": ["abuot"],
    
    # Common misspellings
    "definitely": ["definately", "definatly", "defenitely"],
    "separate": ["seperate", "seperete"],
    "necessary": ["neccessary", "necessery"],
    "receive": ["recieve"],
    "believe": ["beleive"],
    "accommodate": ["accomodate", "acommodate"],
    "occurrence": ["occurence", "occurrance"],
    "restaurant": ["restaraunt", "resteraunt"],
    "immediately": ["immediatly", "immedietly"],
    "government": ["goverment", "govenment"],
    "beginning": ["begining", "beggining"],
    "weird": ["wierd"],
    "successful": ["succesful", "successfull"],
    "tomorrow": ["tommorow", "tommorrow"],
    "surprise": ["suprise", "surprize"],
    "familiar": ["familar", "familliar"],
    "different": ["diffrent", "diferent"],
    "probably": ["probly", "probaly"],
    "thought": ["thougt", "thougth"],
    "business": ["busness", "bussiness"],
    "beautiful": ["beutiful", "beautifull"],
    "exercise": ["excercise", "exercize"],
    "address": ["adress", "adres"],
    "calendar": ["calender", "calander"],
    "friend": ["freind", "frend"],
    "embarrass": ["embarass", "embaras"],
    "grammar": ["grammer", "gramar"],
    "privilege": ["priviledge", "privilage"],
    "recommend": ["reccomend", "recomend"],
    "relevant": ["relevent", "revelant"],
    "schedule": ["schedual", "shedule"],
    "argument": ["arguement", "arguemnet"],
    "environment": ["enviroment", "enviornment"],
    "experience": ["experiance", "expereince"],
    "library": ["libary", "liberry"],
    "maintenance": ["maintainance", "maintnance"],
    "occasion": ["ocassion", "occassion"],
    "occurred": ["occured", "ocurred"],
    "particular": ["particuler", "partikular"],
    "rhythm": ["rythm", "rythem"],
    "surprise": ["suprise", "surprize"],
    "until": ["untill", "untl"],
    "vacuum": ["vacume", "vaccuum"],
    "vehicle": ["vehical", "vehicel"],
    "weather": ["wether", "wheather"],
    "writing": ["writting", "writeing"],
}

# Common autocorrect failures (wrong word suggestions)
AUTOCORRECT_FAILS = {
    "were": "we're",
    "well": "we'll",
    "cant": "can't",
    "wont": "won't",
    "its": "it's",
    "your": "you're",
    "their": "there",
    "there": "their",
    "then": "than",
    "than": "then",
    "affect": "effect",
    "effect": "affect",
    "accept": "except",
    "except": "accept",
    "to": "too",
    "too": "to",
    "hear": "here",
    "here": "hear",
    "break": "brake",
    "brake": "break",
    "principal": "principle",
    "principle": "principal",
    "desert": "dessert",
    "dessert": "desert",
    "stationary": "stationery",
    "stationery": "stationary",
    "complement": "compliment",
    "compliment": "complement",
    "capital": "capitol",
    "capitol": "capital",
    "cite": "site",
    "site": "cite",
    "council": "counsel",
    "counsel": "council",
    "coarse": "course",
    "course": "coarse",
}

def type_text(
    device_id: str,
    region: List[int],
    text: str,
    mode: Optional[str] = None,
) -> bool:
    """
    Type text on a device using the most appropriate method based on content.
    
    Args:
        device_id: ADB device ID
        region: Region to type in [x1, y1, x2, y2]
        text: Text to type
        mode: Optional override for input mode ('typing', 'dictation', 'autofill')
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Get IP address for keyboard communication
        ip_port = get_ip_from_device_id(device_id)
        if not ip_port or ":" not in ip_port:
            print(f"Failed to get valid IP:PORT from device ID: {device_id}")
            return False
            
        ip, port_str = ip_port.split(":")
        port = int(port_str)
        
        # Tap in the provided region
        from utils.tap import generate_tap_events
        tap_result = generate_tap_events(device_id, region)
        if not tap_result:
            print(f"Failed to tap in region {region}")
            return False
                
        time.sleep(0.5)  # Wait for keyboard to appear
        
        # If mode is explicitly specified, use that
        if mode:
            if mode == "typing":
                return _handle_typing(ip, port, text)
            elif mode == "dictation":
                return _handle_dictation(ip, port, text)
            elif mode == "autofill":
                return _handle_autofill(ip, port, text)
            else:
                print(f"Invalid mode: {mode}")
                return False
        
        # Otherwise, automatically select the best mode based on content
        
        # Check if text is suitable for autofill (short phrases, common expressions)
        autofill_patterns = [
            r"^(Yes|No|Maybe|Sure|Okay|OK|Thanks|Thank you|Hello|Hi|Hey|Bye|Goodbye|See you|Later)$",
            r"^(I agree|I disagree|I understand|I don't know|I'm not sure|I think so|I don't think so)$",
            r"^(Good morning|Good afternoon|Good evening|Good night)$",
            r"^(How are you|What's up|What are you doing|Where are you|When will you|Why did you)$",
            r"^(Can you|Could you|Would you|Will you|Should I|Can I|May I)$",
            r"^(That's great|That's awesome|That's cool|That's nice|That's interesting|That's funny)$",
            r"^(I'll call you|I'll text you|I'll be there|I'll do it|I'll try|I'll see)$",
            r"^(On my way|Be right there|Just a minute|Give me a second|Hold on|Wait)$",
            r"^(Let me know|Keep me posted|Tell me more|Sounds good|Works for me)$",
            r"^(See you soon|Talk to you later|Catch you later|Until next time)$"
        ]
        
        is_autofill_candidate = any(re.match(pattern, text) for pattern in autofill_patterns)
        
        # Check for @ symbol in a single word (email addresses, usernames)
        is_at_symbol_word = len(text.split()) == 1 and '@' in text
        if is_at_symbol_word:
            is_autofill_candidate = True
        
        # Decide if this is a good candidate for dictation
        # Longer text, complete sentences, proper punctuation
        is_dictation_candidate = (
            len(text) > 50 and  # Longer text
            len(text.split()) > 10 and  # Multiple words
            any(p in text for p in ['.', '!', '?']) and  # Contains sentence endings
            text[0].isupper()  # Starts with capital letter
        )
        
        # Make probabilistic decision based on text characteristics
        if is_dictation_candidate and random.random() < 0.8:  # 80% chance for dictation if candidate
            return _handle_dictation(ip, port, text)
        elif is_autofill_candidate and random.random() < 0.7:  # 70% chance for autofill if candidate
            return _handle_autofill(ip, port, text)
        else:
            # Default to typing
            return _handle_typing(ip, port, text)
            
    except Exception as e:
        print(f"Error in type_text: {e}")
        return False

def type_text_sequence(
    device_id: str,
    region: List[int],
    text: str,
    mode: Optional[str] = None,
) -> bool:
    """
    Type text on a device using a sequence-based approach for improved accuracy.
    
    Args:
        device_id: Device ID to type on
        region: Region to tap in [x1, y1, x2, y2]
        text: Text to type
        mode: Force a specific typing mode (typing, dictation, autofill)
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Convert device ID to IP:PORT format for keyboard client
        ip_port = get_ip_from_device_id(device_id)
        ip, port = ip_port.split(':')
        port = int(port)
        
        # First tap in the region to ensure focus
        from utils.tap import generate_tap_events
        tap_result = generate_tap_events(device_id, region)
        if not tap_result:
            print(f"Failed to tap in region {region}")
            return False
        
        # Wait for tap to register
        time.sleep(0.5)
        
        # Build the sequence based on the selected mode
        if mode == "typing" or mode is None:
            sequence = _build_typing_sequence(text)
        elif mode == "dictation":
            sequence = _build_dictation_sequence(text)
        elif mode == "autofill":
            sequence = _build_autofill_sequence(text)
        else:
            # Default to typing
            sequence = _build_typing_sequence(text)
        
        # Execute the sequence
        response = keyboard_client.execute_sequence(ip, port, sequence)
        
        # Check if the sequence executed successfully
        if response.get("status") == "success":
            return True
        else:
            print(f"Error executing sequence: {response.get('message', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"Error in type_text_sequence: {e}")
        return False

def _handle_typing(ip: str, port: int, text: str) -> bool:
    """
    Simulate realistic typing with human-like patterns.
    
    Args:
        ip: Device IP address
        port: Device port
        text: Text to type
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Split text into words and spaces
        words = re.findall(r'\S+|\s+', text)
        
        # Track state for autocorrect failures
        wrong_autocorrect_word = None
        wrong_autocorrect_index = -1
        
        # Track if we're at the start of a sentence (for auto-capitalization)
        start_of_sentence = True
        
        for i, word in enumerate(words):
            # Handle spaces
            if word.isspace():
                keyboard_client.type_text(ip, port, " ")
                time.sleep(random.uniform(0.05, 0.15))
                continue
            
            # Check if we need to fix a previous wrong autocorrect
            if wrong_autocorrect_word is not None and i - wrong_autocorrect_index >= 2 and random.random() < 0.9:
                # Calculate how many characters to delete (including spaces)
                chars_to_delete = sum(len(words[j]) for j in range(wrong_autocorrect_index + 1, i + 1))
                
                # Add spaces between words
                chars_to_delete += (i - wrong_autocorrect_index)
                
                # Delete back to the error
                keyboard_client.delete_text(ip, port, chars_to_delete)
                time.sleep(random.uniform(0.2, 0.4))
                
                # Type the correct word
                keyboard_client.type_text(ip, port, wrong_autocorrect_word)
                
                # Add a space
                keyboard_client.type_text(ip, port, " ")
                
                # Now retype the deleted words
                for j in range(wrong_autocorrect_index + 1, i + 1):
                    keyboard_client.type_text(ip, port, words[j])
                    
                    # Add space if not the last word
                    if j < i:
                        keyboard_client.type_text(ip, port, " ")
                
                # Reset wrong autocorrect tracking
                wrong_autocorrect_word = None
                wrong_autocorrect_index = -1
                
                # Continue with the next word
                continue
            
            # Decide if we'll make a typo for this word
            make_typo = random.random() < TYPO_PROBABILITY and len(word) > 1 and not any(c in word for c in "@#$%^&*()_+-=[]{}|;:'\",.<>/?\\")
            
            # Check if this is a common word that might be typed quickly
            is_common_word = word.lower() in COMMON_WORDS and random.random() < BURST_TYPING_PROBABILITY
            
            if make_typo:
                # Generate a typo
                typo = _generate_typo(word)
                
                # Type the typo character by character with realistic timing
                for j, char in enumerate(typo):
                    # Determine typing speed based on character type
                    if is_common_word:
                        # Burst typing for common words
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                    elif char.isalpha() and char.islower():
                        # Common lowercase letters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isalpha() and char.isupper() and not start_of_sentence:
                        # Capital letters (except at start of sentence)
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                    elif char.isalpha() and char.isupper() and start_of_sentence:
                        # First letter of sentence is auto-capitalized, no extra delay
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isdigit():
                        # Numbers
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in ".,":
                        # Common punctuation
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                        # Special characters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                                  TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                    else:
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    
                    # Add variation based on tap movement statistics
                    movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                    adjusted_delay = base_delay * movement_factor
                    
                    # Type the character
                    keyboard_client.type_text(ip, port, char)
                    time.sleep(adjusted_delay)
                
                # Decide if autocorrect will fix the typo
                if random.random() < AUTOCORRECT_PROBABILITY:
                    # Simulate autocorrect behavior
                    time.sleep(random.uniform(0.2, 0.4))  # Brief pause for autocorrect
                    
                    # Delete the typo
                    keyboard_client.delete_text(ip, port, len(typo))
                    time.sleep(random.uniform(0.1, 0.2))
                    
                    # Get a replacement (sometimes wrong)
                    replacement = _get_autocorrect_replacement(word, typo)
                    
                    # Type the replacement
                    keyboard_client.type_text(ip, port, replacement)
                    
                    # If the replacement is wrong, track it for potential later correction
                    if replacement != word:
                        wrong_autocorrect_word = word
                        wrong_autocorrect_index = i
                else:
                    # No autocorrect, the typo remains
                    pass
            else:
                # No typo, type the word normally
                for j, char in enumerate(word):
                    # Determine typing speed based on character type
                    if is_common_word:
                        # Burst typing for common words
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                    elif char.isalpha() and char.islower():
                        # Common lowercase letters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isalpha() and char.isupper() and not start_of_sentence:
                        # Capital letters (except at start of sentence)
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                    elif char.isalpha() and char.isupper() and start_of_sentence:
                        # First letter of sentence is auto-capitalized, no extra delay
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char.isdigit():
                        # Numbers
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in ".,":
                        # Common punctuation
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                        # Special characters
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                                  TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                    else:
                        base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                    
                    # Add variation based on tap movement statistics
                    movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                    adjusted_delay = base_delay * movement_factor
                    
                    # Type the character
                    keyboard_client.type_text(ip, port, char)
                    time.sleep(adjusted_delay)
            
            # Add a space after the word (unless it's the last word)
            if i < len(words) - 1 and not words[i+1].isspace():
                keyboard_client.type_text(ip, port, " ")
                time.sleep(random.uniform(0.05, 0.15))
            
            # Update sentence tracking
            if word.endswith(('.', '!', '?')):
                start_of_sentence = True
            else:
                start_of_sentence = False
            
            # Add occasional thinking pauses between words with more realistic distribution
            pause_chance = random.random()
            if pause_chance < 0.15:  # 15% chance of a pause
                if pause_chance < 0.03:  # 3% chance of a longer thinking pause
                    time.sleep(random.uniform(0.8, 2.0))
                else:  # 12% chance of a shorter pause
                    time.sleep(random.uniform(0.2, 0.5))
        
        return True
        
    except Exception as e:
        print(f"Error in _handle_typing: {e}")
        return False

def _handle_dictation(ip: str, port: int, text: str) -> bool:
    """
    Simulate dictation with realistic word timing, errors, and corrections.
    
    Args:
        ip: Device IP address
        port: Device port
        text: Text to dictate
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence_idx, sentence in enumerate(sentences):
            # Simulate thinking before dictating
            if sentence_idx > 0:
                time.sleep(random.uniform(1.0, 2.0))
            
            # Split sentence into words
            words = sentence.split()
            
            # Track dictation errors for potential correction
            error_index = -1
            original_word = None
            
            for i, word in enumerate(words):
                # Decide if we'll make a dictation error
                make_error = random.random() < 0.15 and len(word) > 2
                
                if make_error and word.lower() in COMMON_HOMOPHONES:
                    # Use a homophone instead
                    original_word = word
                    error_index = i
                    error_word = random.choice(COMMON_HOMOPHONES[word.lower()])
                    
                    # Maintain capitalization
                    if word[0].isupper():
                        error_word = error_word[0].upper() + error_word[1:]
                    
                    # Type the error word
                    keyboard_client.type_text(ip, port, error_word)
                elif make_error and len(word) > 4:
                    # Make up a plausible dictation error
                    original_word = word
                    
                    # Different types of errors
                    error_type = random.choice(["similar", "compound_split", "join"])
                    
                    if error_type == "similar":
                        # Replace with a similar-sounding word
                        similar_words = {
                            "their": "there", "there": "their", "they're": "their",
                            "your": "you're", "you're": "your", "its": "it's", "it's": "its",
                            "affect": "effect", "effect": "affect", "then": "than", "than": "then",
                            "accept": "except", "except": "accept", "lose": "loose", "loose": "lose",
                            "weather": "whether", "whether": "weather", "to": "too", "too": "to",
                            "hear": "here", "here": "hear", "right": "write", "write": "right"
                        }
                        
                        if word.lower() in similar_words:
                            error_word = similar_words[word.lower()]
                            # Preserve capitalization
                            if word[0].isupper():
                                error_word = error_word[0].upper() + error_word[1:]
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    elif error_type == "compound_split" and len(word) > 5:
                        # Only split at realistic compound word boundaries
                        compound_splits = {
                            "keyboard": "key board",
                            "notebook": "note book",
                            "background": "back ground",
                            "sometimes": "some times",
                            "everything": "every thing",
                            "something": "some thing",
                            "anything": "any thing",
                            "nothing": "no thing",
                            "downtown": "down town",
                            "bedroom": "bed room",
                            "bathroom": "bath room",
                            "classroom": "class room",
                            "football": "foot ball",
                            "baseball": "base ball",
                            "basketball": "basket ball",
                            "weekend": "week end",
                            "birthday": "birth day",
                            "sunlight": "sun light",
                            "moonlight": "moon light",
                            "daylight": "day light",
                            "software": "soft ware",
                            "hardware": "hard ware",
                            "firewall": "fire wall",
                            "network": "net work",
                            "website": "web site",
                            "homepage": "home page",
                            "username": "user name",
                            "password": "pass word",
                            "database": "data base",
                            "filename": "file name",
                            "keyboard": "key board",
                            "smartphone": "smart phone",
                            "headphone": "head phone",
                            "microphone": "micro phone",
                            "loudspeaker": "loud speaker",
                            "toothbrush": "tooth brush",
                            "toothpaste": "tooth paste",
                            "hairbrush": "hair brush",
                            "hairdryer": "hair dryer",
                            "sunglasses": "sun glasses",
                            "raincoat": "rain coat",
                            "snowflake": "snow flake",
                            "fireplace": "fire place",
                            "waterfall": "water fall",
                            "earthquake": "earth quake",
                            "thunderstorm": "thunder storm",
                            "rainbow": "rain bow",
                            "sunshine": "sun shine",
                            "moonshine": "moon shine",
                            "starlight": "star light",
                            "candlelight": "candle light",
                            "flashlight": "flash light",
                            "nightlight": "night light",
                            "daybreak": "day break",
                            "nightfall": "night fall",
                            "rainfall": "rain fall",
                            "snowfall": "snow fall",
                            "downpour": "down pour",
                            "upstairs": "up stairs",
                            "downstairs": "down stairs",
                            "inside": "in side",
                            "outside": "out side",
                            "alongside": "along side",
                            "underside": "under side",
                            "backside": "back side",
                            "frontside": "front side",
                            "leftside": "left side",
                            "rightside": "right side",
                            "topside": "top side",
                            "bottomside": "bottom side",
                            "bedtime": "bed time",
                            "lunchtime": "lunch time",
                            "dinnertime": "dinner time",
                            "breakfast": "break fast",
                            "afternoon": "after noon",
                            "midnight": "mid night",
                            "midday": "mid day",
                            "daytime": "day time",
                            "nighttime": "night time",
                            "lifetime": "life time",
                            "halftime": "half time",
                            "fulltime": "full time",
                            "parttime": "part time",
                            "overtime": "over time",
                            "anytime": "any time",
                            "sometime": "some time",
                            "everytime": "every time",
                            "nobody": "no body",
                            "somebody": "some body",
                            "anybody": "any body",
                            "everybody": "every body",
                            "yourself": "your self",
                            "myself": "my self",
                            "himself": "him self",
                            "herself": "her self",
                            "themselves": "them selves",
                            "ourselves": "our selves",
                            "itself": "it self",
                            "oneself": "one self",
                            "cannot": "can not"
                        }
                        
                        if word.lower() in compound_splits:
                            error_word = compound_splits[word.lower()]
                            # Preserve capitalization
                            if word[0].isupper():
                                parts = error_word.split()
                                parts[0] = parts[0][0].upper() + parts[0][1:]
                                error_word = " ".join(parts)
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    elif error_type == "join" and i < len(words) - 1:
                        # Join this word with the next word (only if they make sense together)
                        next_word = words[i + 1]
                        combined = word + next_word
                        
                        # Only join if the combined word is not too long
                        if len(combined) <= 12:
                            error_word = word
                            # We'll handle the join when we get to the next word
                            # by skipping it
                        else:
                            # Just use the original word
                            error_word = word
                            error_index = -1  # Reset since we didn't make an error
                    else:
                        # Just use the original word
                        error_word = word
                        error_index = -1  # Reset since we didn't make an error
                    
                    # Type the error word
                    keyboard_client.type_text(ip, port, error_word)
                else:
                    # Type the word correctly
                    keyboard_client.type_text(ip, port, word)
                
                # Add space between words
                if i < len(words) - 1:
                    keyboard_client.type_text(ip, port, " ")
                
                # Pause between words with natural variation
                time.sleep(random.uniform(DICTATION_WORD_DELAY_RANGE[0], DICTATION_WORD_DELAY_RANGE[1]))
                
                # Decide if we'll correct a previous error
                if error_index >= 0 and i > error_index and random.random() < 0.8:
                    # Calculate how many characters to delete
                    chars_to_delete = len(words[error_index])
                    
                    # Add spaces and following words if needed
                    for j in range(error_index + 1, i + 1):
                        chars_to_delete += len(words[j]) + 1  # +1 for space
                    
                    # Pause before correction
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # Delete back to the error
                    keyboard_client.delete_text(ip, port, chars_to_delete)
                    time.sleep(random.uniform(0.2, 0.4))
                    
                    # Type the correct word
                    keyboard_client.type_text(ip, port, original_word)
                    
                    # Add a space
                    keyboard_client.type_text(ip, port, " ")
                    
                    # Now retype the deleted words
                    for j in range(error_index + 1, i + 1):
                        keyboard_client.type_text(ip, port, words[j])
                        
                        # Add space if not the last word
                        if j < i:
                            keyboard_client.type_text(ip, port, " ")
                    
                    # Reset error tracking
                    error_index = -1
                    original_word = None
            
            # Add period at end of sentence if it doesn't already have punctuation
            if not sentence.rstrip().endswith(('.', '!', '?')):
                keyboard_client.type_text(ip, port, ".")
            
            # Add space between sentences
            if sentence_idx < len(sentences) - 1:
                keyboard_client.type_text(ip, port, " ")
        
        return True
        
    except Exception as e:
        print(f"Error in _handle_dictation: {e}")
        return False

def _build_typing_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for realistic typing with human-like patterns.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Split text into words and spaces
    words = re.findall(r'\S+|\s+', text)
    
    # Track state for autocorrect failures
    wrong_autocorrect_word = None
    wrong_autocorrect_index = -1
    
    # Track if we're at the start of a sentence (for auto-capitalization)
    start_of_sentence = True
    
    for i, word in enumerate(words):
        # Handle spaces
        if word.isspace():
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
            continue
        
        # Check if we need to fix a previous wrong autocorrect
        if wrong_autocorrect_word is not None and i - wrong_autocorrect_index >= 2 and random.random() < 0.9:
            # Calculate how many characters to delete (including spaces)
            chars_to_delete = sum(len(words[j]) for j in range(wrong_autocorrect_index + 1, i + 1))
            
            # Add spaces between words
            chars_to_delete += (i - wrong_autocorrect_index)
            
            # Delete back to the error
            sequence.append({
                "action": "delete",
                "count": chars_to_delete,
                "delay_after": random.uniform(0.2, 0.4)
            })
            
            # Type the correct word
            sequence.append({
                "action": "type",
                "text": wrong_autocorrect_word,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Add a space
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
            
            # Now retype the deleted words
            for j in range(wrong_autocorrect_index + 1, i + 1):
                sequence.append({
                    "action": "type",
                    "text": words[j],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add space if not the last word
                if j < i:
                    sequence.append({
                        "action": "type",
                        "text": " ",
                        "delay_after": random.uniform(0.05, 0.15)
                    })
            
            # Reset wrong autocorrect tracking
            wrong_autocorrect_word = None
            wrong_autocorrect_index = -1
            
            # Continue with the next word
            continue
        
        # Decide if we'll make a typo for this word
        make_typo = random.random() < TYPO_PROBABILITY and len(word) > 1 and not any(c in word for c in "@#$%^&*()_+-=[]{}|;:'\",.<>/?\\")
        
        # Check if this is a common word that might be typed quickly
        is_common_word = word.lower() in COMMON_WORDS and len(word) <= 5
        
        if make_typo and not is_common_word:
            # Generate a typo
            typo = _generate_typo(word)
            
            # Type the typo character by character
            for j, char in enumerate(typo):
                # Determine typing speed based on character type
                if char.isalpha() and char.islower():
                    # Common lowercase letters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isalpha() and char.isupper() and not start_of_sentence:
                    # Capital letters (except at start of sentence)
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                elif char.isalpha() and char.isupper() and start_of_sentence:
                    # First letter of sentence is auto-capitalized, no extra delay
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isdigit():
                    # Numbers
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in ".,":
                    # Common punctuation
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                    # Special characters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                              TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                else:
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                
                # Add variation based on tap movement statistics
                movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                adjusted_delay = base_delay * movement_factor
                
                # Add to sequence
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": adjusted_delay
                })
            
            # Decide if autocorrect will fix the typo
            if random.random() < AUTOCORRECT_PROBABILITY:
                # Simulate autocorrect behavior
                sequence.append({
                    "action": "delay",
                    "duration": random.uniform(0.2, 0.4)  # Brief pause for autocorrect
                })
                
                # Delete the typo
                sequence.append({
                    "action": "delete",
                    "count": len(typo),
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Get a replacement (sometimes wrong)
                replacement = _get_autocorrect_replacement(word, typo)
                
                # Type the replacement
                sequence.append({
                    "action": "type",
                    "text": replacement,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # If the replacement is wrong, track it for potential later correction
                if replacement != word:
                    wrong_autocorrect_word = word
                    wrong_autocorrect_index = i
        else:
            # No typo, type the word normally
            for j, char in enumerate(word):
                # Determine typing speed based on character type
                if is_common_word:
                    # Burst typing for common words
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * BURST_TYPING_MODIFIER
                elif char.isalpha() and char.islower():
                    # Common lowercase letters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isalpha() and char.isupper() and not start_of_sentence:
                    # Capital letters (except at start of sentence)
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1]) * CAPITAL_LETTER_MODIFIER
                elif char.isalpha() and char.isupper() and start_of_sentence:
                    # First letter of sentence is auto-capitalized, no extra delay
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char.isdigit():
                    # Numbers
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in ".,":
                    # Common punctuation
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                elif char in "!@#$%^&*()_+-=[]{}|;:'\",<>/?\\":
                    # Special characters
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0] * SPECIAL_CHAR_MODIFIER[0], 
                                              TYPING_DELAY_RANGE[1] * SPECIAL_CHAR_MODIFIER[1])
                else:
                    base_delay = random.uniform(TYPING_DELAY_RANGE[0], TYPING_DELAY_RANGE[1])
                
                # Add variation based on tap movement statistics
                movement_factor = random.normalvariate(1.0, 0.15)  # 15% variation based on movement
                adjusted_delay = base_delay * movement_factor
                
                # Add to sequence
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": adjusted_delay
                })
        
        # Add a space after the word (unless it's the last word)
        if i < len(words) - 1 and not words[i+1].isspace():
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
        
        # Reset start_of_sentence flag
        start_of_sentence = word.endswith(('.', '!', '?'))
    
    # Ensure we fix any remaining wrong autocorrect at the end
    if wrong_autocorrect_word is not None:
        # Pause as if noticing the error
        sequence.append({
            "action": "delay",
            "duration": random.uniform(0.5, 1.0)
        })
        
        # Calculate how many characters to delete to get back to the error
        words_after_error = len(words) - wrong_autocorrect_index - 1
        chars_to_delete = 0
        
        # Count characters in words after the error
        for j in range(wrong_autocorrect_index + 1, len(words)):
            if not words[j].isspace():  # Skip spaces in the word list
                chars_to_delete += len(words[j])
        
        # Add spaces between words
        chars_to_delete += words_after_error - 1  # -1 because we're not counting the last space
        
        # If we have characters to delete
        if chars_to_delete > 0:
            # Delete back to the error word
            sequence.append({
                "action": "delete",
                "count": chars_to_delete,
                "delay_after": random.uniform(0.2, 0.4)
            })
        
        # Delete the wrong autocorrect word
        sequence.append({
            "action": "delete",
            "count": len(words[wrong_autocorrect_index]),
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Type the correct word
        sequence.append({
            "action": "type",
            "text": wrong_autocorrect_word,
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Add a space
        if words_after_error > 0:
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.05, 0.15)
            })
        
        # Retype the remaining words
        for j in range(wrong_autocorrect_index + 1, len(words)):
            if not words[j].isspace():  # Skip spaces in the word list
                sequence.append({
                    "action": "type",
                    "text": words[j],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add space if not the last word
                if j < len(words) - 1:
                    sequence.append({
                        "action": "type",
                        "text": " ",
                        "delay_after": random.uniform(0.05, 0.15)
                    })
    
    return sequence

def _build_dictation_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for dictation-style typing.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Track error state
    error_index = -1
    original_word = None
    
    for sentence_idx, sentence in enumerate(sentences):
        # Split sentence into words
        words = sentence.split()
        
        # Process each word
        for i, word in enumerate(words):
            # Check if we need to fix a previous error
            if error_index != -1 and i - error_index >= 2 and random.random() < 0.7:
                # Calculate how many characters to delete (including spaces)
                chars_to_delete = sum(len(words[j]) for j in range(error_index + 1, i + 1))
                
                # Add spaces between words
                chars_to_delete += (i - error_index)
                
                # Delete back to the error
                sequence.append({
                    "action": "delete",
                    "count": chars_to_delete,
                    "delay_after": random.uniform(0.2, 0.4)
                })
                
                # Type the correct word
                sequence.append({
                    "action": "type",
                    "text": original_word,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Add a space
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
                
                # Now retype the deleted words
                for j in range(error_index + 1, i + 1):
                    sequence.append({
                        "action": "type",
                        "text": words[j],
                        "delay_after": random.uniform(0.1, 0.2)
                    })
                    
                    # Add space if not the last word
                    if j < i:
                        sequence.append({
                            "action": "type",
                            "text": " ",
                            "delay_after": random.uniform(0.05, 0.15)
                        })
                
                # Reset error tracking
                error_index = -1
                original_word = None
                
                # Continue with the next word
                continue
            
            # Decide if we'll make an error
            make_error = random.random() < 0.15 and len(word) > 2
            
            if make_error and word.lower() in COMMON_HOMOPHONES:
                # Use a homophone error
                error_word = random.choice(COMMON_HOMOPHONES[word.lower()])
                
                # Preserve capitalization
                if word[0].isupper():
                    error_word = error_word[0].upper() + error_word[1:]
                
                sequence.append({
                    "action": "type",
                    "text": error_word,
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                # Track the error for potential correction
                error_index = i
                original_word = word
            elif make_error and len(word) > 4:
                # Make a plausible dictation error
                error_type = random.choice(["similar", "compound_split", "join"])
                
                if error_type == "similar":
                    # Similar sounding word
                    similar_words = {
                        "their": "there", "there": "their", "they're": "their",
                        "your": "you're", "you're": "your", "its": "it's", "it's": "its",
                        "affect": "effect", "effect": "affect", "then": "than", "than": "then",
                        "accept": "except", "except": "accept", "lose": "loose", "loose": "lose",
                        "weather": "whether", "whether": "weather", "to": "too", "too": "to",
                        "hear": "here", "here": "hear", "right": "write", "write": "right"
                    }
                    
                    if word.lower() in similar_words:
                        error_word = similar_words[word.lower()]
                        # Preserve capitalization
                        if word[0].isupper():
                            error_word = error_word[0].upper() + error_word[1:]
                            
                        sequence.append({
                            "action": "type",
                            "text": error_word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                        
                        # Track the error for potential correction
                        error_index = i
                        original_word = word
                    else:
                        # Just type the word correctly
                        sequence.append({
                            "action": "type",
                            "text": word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                elif error_type == "compound_split" and len(word) > 5:
                    # Only split at realistic compound word boundaries
                    compound_splits = {
                        "keyboard": "key board",
                        "notebook": "note book",
                        "background": "back ground",
                        "sometimes": "some times",
                        "everything": "every thing",
                        "something": "some thing",
                        "anything": "any thing",
                        "nothing": "no thing",
                        "downtown": "down town",
                        "bedroom": "bed room",
                        "bathroom": "bath room",
                        "classroom": "class room",
                        "football": "foot ball",
                        "baseball": "base ball",
                        "basketball": "basket ball",
                        "weekend": "week end",
                        "birthday": "birth day",
                        "sunlight": "sun light",
                        "moonlight": "moon light",
                        "daylight": "day light",
                        "software": "soft ware",
                        "hardware": "hard ware",
                        "firewall": "fire wall",
                        "network": "net work",
                        "website": "web site",
                        "homepage": "home page",
                        "username": "user name",
                        "password": "pass word",
                        "database": "data base",
                        "filename": "file name",
                        "keyboard": "key board",
                        "smartphone": "smart phone",
                        "headphone": "head phone",
                        "microphone": "micro phone",
                        "loudspeaker": "loud speaker",
                        "toothbrush": "tooth brush",
                        "toothpaste": "tooth paste",
                        "hairbrush": "hair brush",
                        "hairdryer": "hair dryer",
                        "sunglasses": "sun glasses",
                        "raincoat": "rain coat",
                        "snowflake": "snow flake",
                        "fireplace": "fire place",
                        "waterfall": "water fall",
                        "earthquake": "earth quake",
                        "thunderstorm": "thunder storm",
                        "rainbow": "rain bow",
                        "sunshine": "sun shine",
                        "moonshine": "moon shine",
                        "starlight": "star light",
                        "candlelight": "candle light",
                        "flashlight": "flash light",
                        "nightlight": "night light",
                        "daybreak": "day break",
                        "nightfall": "night fall",
                        "rainfall": "rain fall",
                        "snowfall": "snow fall",
                        "downpour": "down pour",
                        "upstairs": "up stairs",
                        "downstairs": "down stairs",
                        "inside": "in side",
                        "outside": "out side",
                        "alongside": "along side",
                        "underside": "under side",
                        "backside": "back side",
                        "frontside": "front side",
                        "leftside": "left side",
                        "rightside": "right side",
                        "topside": "top side",
                        "bottomside": "bottom side",
                        "bedtime": "bed time",
                        "lunchtime": "lunch time",
                        "dinnertime": "dinner time",
                        "breakfast": "break fast",
                        "afternoon": "after noon",
                        "midnight": "mid night",
                        "midday": "mid day",
                        "daytime": "day time",
                        "nighttime": "night time",
                        "lifetime": "life time",
                        "halftime": "half time",
                        "fulltime": "full time",
                        "parttime": "part time",
                        "overtime": "over time",
                        "anytime": "any time",
                        "sometime": "some time",
                        "everytime": "every time",
                        "nobody": "no body",
                        "somebody": "some body",
                        "anybody": "any body",
                        "everybody": "every body",
                        "yourself": "your self",
                        "myself": "my self",
                        "himself": "him self",
                        "herself": "her self",
                        "themselves": "them selves",
                        "ourselves": "our selves",
                        "itself": "it self",
                        "oneself": "one self",
                        "cannot": "can not"
                    }
                    
                    if word.lower() in compound_splits:
                        error_word = compound_splits[word.lower()]
                        # Preserve capitalization
                        if word[0].isupper():
                            parts = error_word.split()
                            parts[0] = parts[0][0].upper() + parts[0][1:]
                            error_word = " ".join(parts)
                            
                        sequence.append({
                            "action": "type",
                            "text": error_word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                        
                        # Track the error for potential correction
                        error_index = i
                        original_word = word
                    else:
                        # Just type the word correctly
                        sequence.append({
                            "action": "type",
                            "text": word,
                            "delay_after": random.uniform(0.1, 0.2)
                        })
                else:
                    # Just type the word correctly
                    sequence.append({
                        "action": "type",
                        "text": word,
                        "delay_after": random.uniform(0.1, 0.2)
                    })
            
            # Add space between words
            if i < len(words) - 1:
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
        
        # Add period at end of sentence if it doesn't already have punctuation
        if not sentence.rstrip().endswith(('.', '!', '?')):
            sequence.append({
                "action": "type",
                "text": ".",
                "delay_after": random.uniform(0.1, 0.2)
            })
        
        # Add space between sentences
        if sentence_idx < len(sentences) - 1:
            sequence.append({
                "action": "type",
                "text": " ",
                "delay_after": random.uniform(0.5, 1.0)
            })
    
    # Ensure we fix any remaining errors at the end
    if error_index != -1:
        # Go back to the error and fix it
        words_after_error = len(words) - error_index - 1
        chars_to_delete = sum(len(words[j]) for j in range(error_index, len(words)))
        chars_to_delete += words_after_error  # Add spaces
        
        sequence.append({
            "action": "delete",
            "count": chars_to_delete,
            "delay_after": random.uniform(0.2, 0.4)
        })
        
        # Type the correct word
        sequence.append({
            "action": "type",
            "text": original_word,
            "delay_after": random.uniform(0.1, 0.2)
        })
        
        # Add a space
        sequence.append({
            "action": "type",
            "text": " ",
            "delay_after": random.uniform(0.05, 0.15)
        })
        
        # Retype the remaining words
        for j in range(error_index + 1, len(words)):
            sequence.append({
                "action": "type",
                "text": words[j],
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Add space if not the last word
            if j < len(words) - 1:
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
    
    return sequence

def _build_autofill_sequence(text: str) -> List[Dict]:
    """
    Build a sequence for autofill-style typing.
    
    Args:
        text: Text to type
        
    Returns:
        List of action dictionaries
    """
    sequence = []
    
    # Check if it's an email or URL
    if '@' in text or text.startswith(('http://', 'https://', 'www.')):
        # For emails and URLs, type a prefix and then use suggestion
        if '@' in text:
            # For email, type the part before @ and select suggestion
            prefix = text.split('@')[0]
            
            # Type the prefix character by character
            for char in prefix:
                sequence.append({
                    "action": "type",
                    "text": char,
                    "delay_after": random.uniform(0.1, 0.2)
                })
            
            # Pause as if looking at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.5, 1.0)
            })
            
            # Simulate tapping on a suggestion (by typing the full text)
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            return sequence
        
        # For common phrases
        words = text.split()
        
        if len(words) <= 3:
            # Type the first word
            sequence.append({
                "action": "type",
                "text": words[0],
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Pause to look at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.3, 0.6)
            })
            
            # Delete what we typed (simulating selecting a suggestion)
            sequence.append({
                "action": "delete",
                "count": len(words[0]),
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Type the full phrase (as if selected from suggestions)
            sequence.append({
                "action": "type",
                "text": text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        else:
            # For longer phrases, type first few words then use suggestion
            words_to_type = min(2, len(words) - 1)
            
            # Type the first few words
            for i in range(words_to_type):
                sequence.append({
                    "action": "type",
                    "text": words[i],
                    "delay_after": random.uniform(0.1, 0.2)
                })
                
                sequence.append({
                    "action": "type",
                    "text": " ",
                    "delay_after": random.uniform(0.05, 0.15)
                })
            
            # Type part of the next word
            partial_word = words[words_to_type][:min(3, len(words[words_to_type]))]
            sequence.append({
                "action": "type",
                "text": partial_word,
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Pause as if looking at suggestions
            sequence.append({
                "action": "delay",
                "duration": random.uniform(0.5, 1.0)
            })
            
            # Delete the partial word
            sequence.append({
                "action": "delete",
                "count": len(partial_word),
                "delay_after": random.uniform(0.1, 0.2)
            })
            
            # Type the rest of the phrase (as if selected from suggestions)
            remaining_text = " ".join(words[words_to_type:])
            sequence.append({
                "action": "type",
                "text": remaining_text,
                "delay_after": random.uniform(0.1, 0.2)
            })
        
        return sequence
    
    # For other text, just use the typing sequence
    return _build_typing_sequence(text)

def _generate_typo(word: str) -> str:
    """
    Generate a realistic typo for a given word.
    
    Args:
        word: The original word
        
    Returns:
        A word with a typo
    """
    if len(word) <= 1:
        return word
    
    # Choose typo type
    typo_type = random.choices(
        ["swap", "double", "adjacent", "wrong_key", "missing", "extra"],
        weights=[0.25, 0.15, 0.25, 0.2, 0.1, 0.05],
        k=1
    )[0]
    
    # Create a copy of the word as a list for easier manipulation
    chars = list(word)
    
    if typo_type == "swap" and len(word) >= 3:
        # Swap two adjacent characters (common error)
        pos = random.randint(0, len(word) - 2)
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
    
    elif typo_type == "double" and len(word) >= 2:
        # Double a letter (common error)
        pos = random.randint(0, len(word) - 1)
        chars.insert(pos, chars[pos])
    
    elif typo_type == "adjacent" and len(word) >= 2:
        # Hit an adjacent key on the keyboard
        keyboard_adjacency = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wrsdf',
            'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujklo', 'j': 'huikmn',
            'k': 'jiolm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
            'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedxz', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tghu',
            'z': 'asx'
        }
        
        pos = random.randint(0, len(word) - 1)
        char = word[pos].lower()
        
        if char in keyboard_adjacency:
            adjacent_keys = keyboard_adjacency[char]
            replacement = random.choice(adjacent_keys)
            
            # Preserve capitalization
            if word[pos].isupper():
                replacement = replacement.upper()
                
            chars[pos] = replacement
    
    elif typo_type == "wrong_key":
        # Just hit a random wrong key
        pos = random.randint(0, len(word) - 1)
        replacement = random.choice("abcdefghijklmnopqrstuvwxyz")
        
        # Preserve capitalization
        if word[pos].isupper():
            replacement = replacement.upper()
            
        chars[pos] = replacement
    
    elif typo_type == "missing" and len(word) >= 3:
        # Missing letter
        pos = random.randint(0, len(word) - 1)
        chars.pop(pos)
    
    else:  # extra
        # Extra letter
        pos = random.randint(0, len(word))
        chars.insert(pos, random.choice("abcdefghijklmnopqrstuvwxyz"))
    
    return ''.join(chars)

def _get_autocorrect_replacement(original_word: str, typo: str) -> str:
    """
    Simulate realistic autocorrect behavior by providing a replacement for a typo.
    
    Args:
        original_word: The original intended word
        typo: The typo that was typed
        
    Returns:
        Either the correct word (95% chance) or a plausible but wrong correctly-spelled
        word (5% chance). Never returns a misspelled word.
    """
    # 95% chance of correct autocorrect
    if random.random() < 0.95:
        return original_word
    
    # 5% chance of wrong but correctly spelled word
    # Check if the original word has a common confusion pair
    if original_word.lower() in AUTOCORRECT_FAILS:
        wrong_word = AUTOCORRECT_FAILS[original_word.lower()]
        
        # Preserve capitalization
        if original_word[0].isupper():
            wrong_word = wrong_word[0].upper() + wrong_word[1:]
            
        return wrong_word
    
    # If no confusion pair exists, just return the correct word
    return original_word

# Import subprocess here to avoid circular imports
import subprocess

if __name__ == "__main__":
    # Test code
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python type.py <device_id> <text>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    text = " ".join(sys.argv[2:])
    
    # Default region for testing
    region = [100, 300, 400, 400]
    
    result = type_text(device_id, region, text)
    print(f"Typing result: {result}")
