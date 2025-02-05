import os
from openai import OpenAI
import google.generativeai as genai
from google.generativeai.types import GenerationConfig 
import re
from dotenv import load_dotenv

load_dotenv()



class BaseLLMProvider:
    """Base class for LLM providers with common interface"""
    def __init__(self, model):
        self.model = model
    
    def summarize_text(self, text):
        """Summarize the given text"""
        raise NotImplementedError("Subclasses must implement summarize_text")
    
    def generate_answer(self, question, transcript):
        """Generate an answer based on the transcript"""
        raise NotImplementedError("Subclasses must implement generate_answer")
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file"""
        raise NotImplementedError("Subclasses must implement transcribe_audio")

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model='gpt-4o-mini'):
        super().__init__(model)
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def summarize_text(self, text):
        try:
            system_prompt = """You are a YouTube video summarizer. Follow these rules:
                1. Start with a 1-sentence overview.
                2. List 3-5 key points as bullet points.
                3. Highlight technical terms or tools mentioned, if significant.
                4. If multiple speakers, note their roles.
                5. Avoid speculation; only use transcript content."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the transcript to summarize: {text}. Keep your summary concise and to the point."}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Summarization Error: {str(e)}")
            return f"Error in summarization: {str(e)}"
    
    def generate_answer(self, question, transcript):
        try:
            system_prompt = f"""Answer the user's question using this transcript.
                Rules:
                1. If the answer isn't in the transcript, say "I don't know."
                2. Be concise (1-2 sentences).
                3. Format technical terms in **bold**.
                Transcript:\n{transcript[:3000]}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Answer Generation Error: {str(e)}")
            return f"Error generating answer: {str(e)}"
    
    def transcribe_audio(self, audio_file_path):
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                # Clean the response text (remove non-printable characters and escape HTML)
            clean_text = transcript.text.strip()  # Remove leading/trailing whitespace
            clean_text = re.sub(r'\n+', '\n', clean_text)  # R
            return clean_text
        except Exception as e:
            print(f"OpenAI Transcription Error: {str(e)}")
            return None

class GoogleProvider(BaseLLMProvider):
    def __init__(self, model='gemini-1.5-flash'):
        super().__init__(model)
        # Configure Generative AI client
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    
        self.genai_client = genai.GenerativeModel(model)
        
    
    def summarize_text(self, text):
        try:
            system_prompt = """You are a YouTube video summarizer. Follow these rules:
                1. Start with a 1-sentence overview.
                2. List 3-5 key points as bullet points.
                3. Highlight technical terms or tools mentioned, if significant.
                4. If multiple speakers, note their roles.
                5. Avoid speculation; only use transcript content."""
            
            prompt = f"{system_prompt}\n\nHere is the transcript to summarize: {text}. Keep your summary concise and to the point."
            response = self.genai_client.generate_content(prompt)
            print(f"Raw Gemini response: {response.text}")
            # Clean the response text (remove non-printable characters and escape HTML)
            clean_summary = response.text.strip()  # Remove leading/trailing whitespace
            clean_summary = re.sub(r'\n+', '\n', clean_summary)  # R
            
            return clean_summary
        except Exception as e:
            print(f"Google Summarization Error: {str(e)}")
            return f"Error in summarization: {str(e)}"
            
            
    
    def generate_answer(self, question, transcript):
        try:
            system_prompt = f"""Answer the user's question using this transcript.
                Rules:
                1. If the answer isn't in the transcript, say "I don't know."
                2. Be concise (1-2 sentences).
                3. Format technical terms in **bold**.
                Transcript:\n{transcript[:3000]}"""
            
            prompt = f"{system_prompt}\n\nQuestion: {question}"
            response = self.genai_client.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Google Answer Generation Error: {str(e)}")
            return f"Error generating answer: {str(e)}"
    
    def transcribe_audio(self, audio_file_path):
        try:
                
            # Generate transcript
            response = self.genai_client.generate_content([
                "Transcribe the contents of this audio file. Capture all spoken words accurately.",
                genai.upload_file(audio_file_path)
            ])
                
            return response.text
        except Exception as e:
            print(f"An error occurred: {e}")
            
           

class LLMProviderFactory:
    @staticmethod
    def get_provider():
        provider = os.getenv('LLM_PROVIDER').lower()
        model = os.getenv('LLM_MODEL')
        
        if provider == 'openai':
            return OpenAIProvider(model)
        elif provider in ["gemini", "google"]:
            return GoogleProvider(model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")