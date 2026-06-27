"""
Audio Processing Module
Handles audio transcription using OpenAI Whisper
"""

import os
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Handles audio file processing and transcription using Whisper
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize AudioProcessor
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        logger.info(f"AudioProcessor initialized with model size: {model_size}")
    
    def load_model(self):
        """Load Whisper model"""
        try:
            import whisper
            if self.model is None:
                logger.info(f"Loading Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_audio(self, audio_file, file_suffix: str) -> Optional[str]:
        """
        Transcribe audio file to text
        
        Args:
            audio_file: Audio file object
            file_suffix: File extension (e.g., '.mp3', '.wav')
        
        Returns:
            Transcribed text or None if failed
        """
        temp_path = None
        try:
            # Load model if not already loaded
            self.load_model()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_audio:
                temp_audio.write(audio_file.read())
                temp_path = temp_audio.name
            
            logger.info(f"Transcribing audio file: {temp_path}")
            
            # Transcribe
            result = self.model.transcribe(temp_path)
            text = result["text"]
            
            logger.info(f"Transcription successful. Length: {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
        
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Temporary file removed: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")
    
    def validate_audio_format(self, filename: str) -> bool:
        """
        Validate audio file format
        
        Args:
            filename: Name of the audio file
        
        Returns:
            True if format is supported, False otherwise
        """
        supported_formats = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
        file_ext = os.path.splitext(filename)[1].lower()
        
        is_valid = file_ext in supported_formats
        if not is_valid:
            logger.warning(f"Unsupported audio format: {file_ext}")
        
        return is_valid