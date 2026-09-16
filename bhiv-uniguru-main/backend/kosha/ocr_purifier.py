import re
import unicodedata
from typing import Optional

class OCRPurifier:
    """
    Phase 2: OCR Purification Layer
    Removes broken Unicode, garbage text, random line breaks
    Ensures only clean, readable text passes forward
    """
    
    NOISE_PATTERNS = [
        r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]',  # Control chars
        r'[▪▫■□●○◆◇★☆]',  # Bullet noise
        r'https?://\S+',  # URLs
        r'www\.\S+',
        r'digitized\s+by',
        r'in\s+public\s+domain',
        r'©\s*\d{4}',
        r'\|\s*\|',  # Double pipes
        r'_{3,}',  # Multiple underscores
        r'-{3,}',  # Multiple dashes
    ]
    
    BROKEN_UNICODE_RANGES = [
        (0xFFFD, 0xFFFD),  # Replacement character
        (0xFFF0, 0xFFFF),  # Specials
    ]
    
    @staticmethod
    def clean(text: str) -> Optional[str]:
        """Main purification entry point"""
        if not text or not isinstance(text, str):
            return None
            
        text = text.strip()
        if len(text) < 10:
            return None
            
        # Remove noise patterns
        for pattern in OCRPurifier.NOISE_PATTERNS:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Remove broken Unicode
        text = OCRPurifier._remove_broken_unicode(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove lines with excessive special chars
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            if OCRPurifier._is_valid_line(line):
                clean_lines.append(line.strip())
        
        text = '\n'.join(clean_lines).strip()
        
        # Final validation
        if len(text) < 10:
            return None
        if OCRPurifier._is_garbage(text):
            return None
            
        return text
    
    @staticmethod
    def _remove_broken_unicode(text: str) -> str:
        """Remove broken Unicode characters"""
        result = []
        for char in text:
            code = ord(char)
            is_broken = any(start <= code <= end for start, end in OCRPurifier.BROKEN_UNICODE_RANGES)
            if not is_broken:
                result.append(char)
        return ''.join(result)
    
    @staticmethod
    def _is_valid_line(line: str) -> bool:
        """Check if line is valid (not garbage)"""
        if not line or len(line.strip()) < 3:
            return False
        
        # Count alphanumeric vs special chars
        alnum = sum(c.isalnum() or c.isspace() for c in line)
        total = len(line)
        
        if total == 0:
            return False
            
        ratio = alnum / total
        return ratio > 0.5
    
    @staticmethod
    def _is_garbage(text: str) -> bool:
        """Detect if entire text is garbage"""
        if not text:
            return True
        
        # Check for excessive special characters
        special_count = sum(not c.isalnum() and not c.isspace() for c in text)
        total = len(text)
        
        if total == 0:
            return True
            
        special_ratio = special_count / total
        if special_ratio > 0.3:
            return True
        
        # Check for random character sequences
        words = text.split()
        if len(words) < 3:
            return True
        
        # Check average word length (garbage tends to have very short or very long words)
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 2 or avg_word_len > 20:
            return True
        
        return False
    
    @staticmethod
    def extract_sanskrit_if_present(text: str) -> Optional[str]:
        """Extract clean Sanskrit text if present"""
        if not text:
            return None
        
        # Devanagari range: U+0900 to U+097F
        devanagari_pattern = r'[\u0900-\u097F।॥\s]+'
        matches = re.findall(devanagari_pattern, text)
        
        if not matches:
            return None
        
        sanskrit_text = ' '.join(matches).strip()
        
        # Validate Sanskrit quality
        if len(sanskrit_text) < 10:
            return None
        
        # Check for noise in Sanskrit
        devanagari_chars = sum(1 for c in sanskrit_text if '\u0900' <= c <= '\u097F')
        total_chars = len(sanskrit_text.replace(' ', ''))
        
        if total_chars == 0:
            return None
        
        purity_ratio = devanagari_chars / total_chars
        if purity_ratio < 0.7:
            return None
        
        return sanskrit_text
