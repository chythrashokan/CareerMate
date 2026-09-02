try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
    _GENAI_IMPORT_ERROR = None
except Exception as _e:
    genai = None
    _GENAI_AVAILABLE = False
    _GENAI_IMPORT_ERROR = _e

import os
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class GeminiQuestionService:
    def __init__(self):
        api_key = "AIzaSyCFKxFxqdE0YO1S057XaUAg2TVJ_0Wppiw"
        # If the Google generative AI library failed to import, don't attempt to configure it.
        if _GENAI_AVAILABLE and genai is not None:
            try:
                genai.configure(api_key=api_key)
                # Initialize model handle; errors here will be caught below in methods
                self.model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
            except Exception as e:
                logger.warning('Generative AI library present but failed to initialize: %s', e)
                self.model = None
        else:
            logger.warning('Generative AI library not available: %s', _GENAI_IMPORT_ERROR)
            self.model = None
    
    def generate_questions(self, role, level, count=5, context=None):
        """
        Generate interview questions based on role and level using Gemini API
        """
        # Ensure count is an integer and constrained to 1..10
        try:
            count = int(count)
        except Exception:
            count = 5
        count = max(1, min(count, 10))

        # If Gemini model is not available, return fallback questions immediately
        if self.model is None:
            logger.warning('Gemini model not available; using fallback questions')
            return self._get_fallback_questions(role, level, count)

        prompt = self._build_question_prompt(role, level, count, context)
        
        try:
            response = self.model.generate_content(prompt)
            questions = self._parse_response(response.text)
            return questions[:count]
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._get_fallback_questions(role, level, count)
    
    def _build_question_prompt(self, role, level, count, context):
        level_descriptions = {
            'beginner': "Beginner level (0-2 years experience). Focus on basic concepts, fundamentals, and entry-level knowledge.",
            'mid': "Mid-level (2-5 years experience). Focus on practical experience, problem-solving, and intermediate concepts.",
            'senior': "Senior level (5+ years experience). Focus on leadership, architecture, system design, and advanced concepts."
        }
        
        prompt = f"""
        Generate {count} interview questions for a {role} position at {level} level.
        
        Level: {level_descriptions.get(level, level)}
        
        Requirements:
        1. Each question should be relevant to the role
        2. Include a mix of question types (technical, behavioral, situational)
        3. Questions should be appropriate for the experience level
        4. Each question should have:
           - The question text
           - Question type (e.g., 'technical', 'behavioral', 'situational', 'problem-solving')
           - Category (e.g., 'Technical Skills', 'Teamwork', 'Leadership', 'Problem Solving')
        
        Format the response as a JSON array of objects, each with:
        - "text": the question
        - "type": question type
        - "category": question category
        
        Example:
        [
            {{
                "text": "Tell me about your experience with {role}.",
                "type": "intro",
                "category": "Introduction"
            }},
            {{
                "text": "How do you handle debugging complex issues?",
                "type": "technical",
                "category": "Problem Solving"
            }}
        ]
        
        Context: {context if context else 'No additional context provided.'}
        
        Generate questions now:
        """
        return prompt
    
    def _parse_response(self, response_text):
        """Parse Gemini response into structured questions"""
        try:
            # Try to extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                questions = json.loads(json_str)
                return questions
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse manually
        questions = []
        lines = response_text.split('\n')
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('"text"') or line.startswith('text:'):
                text = line.split(':', 1)[1].strip().strip('",')
                current_question['text'] = text
            elif line.startswith('"type"') or line.startswith('type:'):
                q_type = line.split(':', 1)[1].strip().strip('",')
                current_question['type'] = q_type
            elif line.startswith('"category"') or line.startswith('category:'):
                category = line.split(':', 1)[1].strip().strip('",')
                current_question['category'] = category
                if current_question.get('text'):
                    questions.append(current_question.copy())
                    current_question = {}
        
        return questions
    
    def _get_fallback_questions(self, role, level, count):
        """Fallback questions if API fails"""
        fallback_questions = {
            'developer': [
                {"text": f"Tell me about your experience as a {role}.", "type": "intro", "category": "Introduction"},
                {"text": "What programming languages are you most comfortable with?", "type": "technical", "category": "Technical Skills"},
                {"text": "Describe a challenging technical problem you solved.", "type": "problem-solving", "category": "Problem Solving"},
                {"text": "How do you stay updated with new technologies?", "type": "behavioral", "category": "Learning"},
                {"text": "What's your approach to code reviews?", "type": "process", "category": "Development Process"}
            ],
            'account': [
                {"text": f"Describe your account management experience.", "type": "intro", "category": "Introduction"},
                {"text": "How do you handle difficult clients?", "type": "situational", "category": "Client Management"},
                {"text": "What's your sales process?", "type": "process", "category": "Sales Process"},
            ]
        }
        
        questions = fallback_questions.get(role, fallback_questions['developer'])
        return questions[:count]
    
    def evaluate_answer(self, question, answer):
        """
        Evaluate an answer using Gemini API
        """
        # If Gemini model is not available, return fallback evaluation immediately
        if self.model is None:
            logger.warning('Gemini model not available; using fallback evaluation')
            return {
                "confidence": 75,
                "clarity": 70,
                "feedback": "Good attempt. Consider adding more specific examples."
            }
        
        prompt = f"""
        Evaluate this interview answer on a scale of 0-100 for confidence and clarity.
        
        Question: {question}
        Answer: {answer}
        
        Provide a JSON response with these exact fields:
        - "confidence": number between 0-100 (how confident the answer sounds)
        - "clarity": number between 0-100 (how clear and well-structured the answer is)
        - "feedback": brief constructive feedback (max 100 characters)
        
        Example response:
        {{
            "confidence": 85,
            "clarity": 90,
            "feedback": "Good structure but could provide more specific examples."
        }}
        
        Now evaluate:
        """
        
        try:
            response = self.model.generate_content(prompt)
            evaluation = self._parse_evaluation_response(response.text)
            return evaluation
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            return {
                "confidence": 75,
                "clarity": 70,
                "feedback": "Good attempt. Consider adding more specific examples."
            }
    
    def _parse_evaluation_response(self, response_text):
        """Parse evaluation response"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Default fallback
        return {
            "confidence": 75,
            "clarity": 70,
            "feedback": "Good attempt. Could be more detailed."
        }