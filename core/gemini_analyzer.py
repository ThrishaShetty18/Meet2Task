import json
import logging
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """
    Analyzes meeting transcripts using Google Gemini AI
    """
    
    def __init__(self, api_key: str):
        """
        Initialize GeminiAnalyzer
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.model_names = ["gemini-pro", "models/gemini-pro", "gemini-1.5-flash"]
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        logger.info("GeminiAnalyzer initialized")
    
    def configure_api(self):
        """Configure Gemini API"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            logger.info("Gemini API configured successfully")
            return genai
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
            raise
    
    def analyze_transcript(self, transcript: str) -> Optional[str]:
        """
        Analyze meeting transcript using Gemini
        
        Args:
            transcript: Meeting transcript text
        
        Returns:
            JSON string with analysis results or None if failed
        """
        genai = self.configure_api()
        
        prompt = self._create_analysis_prompt(transcript)
        
        # Try each model with retries
        for model_name in self.model_names:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Attempting analysis with model: {model_name} (attempt {attempt + 1}/{self.max_retries})")
                    
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    
                    logger.info(f"Analysis successful with model: {model_name}")
                    return response.text
                
                except Exception as e:
                    logger.warning(f"Analysis failed with {model_name} (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"All retries exhausted for model: {model_name}")
        
        logger.error("All models failed")
        return None
    
    def _create_analysis_prompt(self, transcript: str) -> str:
        """Create analysis prompt for Gemini"""
        return f"""
Analyze this meeting transcript and return a JSON response with the following structure:

{{
  "summary": "A concise 2-3 sentence summary of the meeting",
  "insights": "Key insights and important points from the meeting",
  "tasks": [
    {{
      "title": "Short task title (max 60 characters)",
      "description": "Detailed task description",
      "priority": "High/Medium/Low",
      "type": "Bug/Feature/Improvement/DevOps/Testing/Documentation/General"
    }}
  ]
}}

Meeting Transcript:
{transcript}

Return ONLY valid JSON, no additional text.
"""
    
    def parse_analysis(self, response_text: str) -> Tuple[str, List[Dict], str]:
        """
        Parse Gemini response into structured data
        
        Args:
            response_text: Raw response from Gemini
        
        Returns:
            Tuple of (summary, tasks_list, insights)
        """
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in response")
                return "", [], ""
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            summary = data.get("summary", "")
            insights = data.get("insights", "")
            
            # Parse tasks
            tasks = []
            for task in data.get("tasks", []):
                tasks.append({
                    "Task Title": task.get("title", "Untitled")[:60],
                    "Summary": task.get("description", ""),
                    "Priority": task.get("priority", "Medium"),
                    "Type": task.get("type", "General"),
                    "Full Task": task.get("description", "")
                })
            
            logger.info(f"Parsed {len(tasks)} tasks from analysis")
            return summary, tasks, insights
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return "", [], ""
        except Exception as e:
            logger.error(f"Analysis parsing failed: {e}")
            return "", [], ""

