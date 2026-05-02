"""
api_clients.py

This module centralizes all interactions with external APIs into dedicated classes.
It handles the construction of API requests, sending them, and processing the
responses, including robust error handling. This keeps the main pipeline logic
clean and focused on orchestration rather than API specifics.
"""
import requests
import time
import base64
import wave
import json
import logging
from functools import wraps
import re
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

# Safely import Google Cloud libraries for Vertex AI
try:
    from google.cloud import aiplatform
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from vertexai.preview.vision_models import ImageGenerationModel
except ImportError:
    logging.warning("Failed to import Google Cloud libraries. Vertex AI functionality will be disabled.")
    aiplatform = None
    vertexai = None
    ImageGenerationModel = None


# --- API Constants (As specified by user) ---
GEMINI_TEXT_MODEL = "gemini-3-flash-preview"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
WAVESPEED_POLL_URL = "https://api.wavespeed.ai/api/v3/predictions/{}/result"
WAVESPEED_BASE_ENDPOINT = "https://api.wavespeed.ai/api/v3/{}"
VEO_MODEL_ID = "veo-3.0-generate-preview" # For Vertex AI Video
NANO_BANANA_IMAGE_MODEL = "gemini-2.5-flash-image-preview" # For Vertex AI Image

# --- Style Profiles: Single source of truth for all content styles ---
STYLE_PROFILES = {
    "Podcast": {
        "script": "Craft a lively dual-host podcast conversation with natural back-and-forth dialogue, questions, reactions, and humor.",
        "tts": "(Speaking naturally in a warm, conversational podcast tone)",
        "video": "A cozy professional podcast studio, soft lighting, two microphones, soundproof foam walls, cinematic bokeh, warm amber and teal tones.",
        "image": "Photorealistic podcast studio aesthetic, professional warm atmosphere with microphones.",
        "research": "Focus on interesting angles, debatable points, surprising facts, and recent developments.",
    },
    "ASMR Video": {
        "script": "Write a slow, meditative, deeply relaxing narration. Use sensory language — textures, sounds, gentle actions. Sentences must be short, calming, and hypnotic. No excitement or urgency.",
        "tts": "(Whispering very softly and gently, as if speaking directly into the listener's ear, extremely slowly and soothingly)",
        "video": "Extreme close-up macro shots of soft textures — velvet, sand, water droplets, leaves, candlelight. Slow motion. Soft natural light. Pastel and earth tones.",
        "image": "Extreme macro photography, soft focus, calming textures, muted earth tones, candlelight, very peaceful.",
        "research": "Focus on sensory, calming, and mindful aspects. Find peaceful, gentle angles of the story.",
    },
    "Documentary": {
        "script": "Write like a serious authoritative documentary narrator (David Attenborough style). Use dramatic pauses, powerful statements, and a building narrative arc. Ground every claim in facts.",
        "tts": "(Speaking with a deep, authoritative documentary narrator voice — measured, serious, and compelling)",
        "video": "Cinematic documentary footage. Sweeping aerial shots, dramatic landscapes, slow zooms. Film grain, desaturated color grading, epic atmosphere.",
        "image": "Documentary-style photography. High contrast, dramatic lighting, journalistic realism. Cinematic color grading.",
        "research": "Find historical context, expert quotes, compelling statistics, and the human story behind the facts.",
    },
    "Story": {
        "script": "Write a compelling narrative story with a clear beginning, rising action, climax, and resolution. Use vivid descriptions, character voices, and emotional beats.",
        "tts": "(Speaking as an engaging storyteller — varied pace, dramatic at tense moments, warm and inviting)",
        "video": "Cinematic storybook visuals. Rich painterly colors, dramatic lighting that follows the story mood.",
        "image": "Cinematic narrative illustration. Dramatic composition, rich colors, a sense of story and character like a movie poster.",
        "research": "Find the most compelling narrative — human stories, dramatic turning points, heroes and villains.",
    },
    "Kids Story": {
        "script": "Write a fun, simple, cheerful story for young children. Use bright positive language, repetition, simple vocabulary, and a clear moral. Characters should be lovable.",
        "tts": "(Speaking in a bright, enthusiastic, fun children's storyteller voice — animated, clear, and very expressive)",
        "video": "Colorful cartoonish animated world. Bright primary colors, bouncy movements, whimsical characters, sunny skies. Pixar aesthetic.",
        "image": "Bright colorful children's book illustration. Simple shapes, bold outlines, primary colors, happy characters.",
        "research": "Find the most fun, age-appropriate, educational angles. Focus on wonder, discovery, and positive messages.",
    },
    "Horror Story": {
        "script": "Write a chilling, suspenseful horror story. Build dread slowly. Use dark imagery, unsettling details, and moments of genuine fear. Leave the listener unsettled.",
        "tts": "(Speaking in a slow, tense, unsettling voice — hushed but intense, with dramatic pauses before reveals)",
        "video": "Dark shadowy high-contrast visuals. Abandoned locations, flickering lights, fog, deep shadows. Desaturated palette with blood-red accents.",
        "image": "Dark horror photography. Deep shadows, unsettling compositions, muted colors with red accents, a sense of dread.",
        "research": "Find the most disturbing, unexplained, or frightening real-world angles — unsolved mysteries, dark history.",
    },
    "Viral Video": {
        "script": "Write punchy, high-energy, hook-driven content. Open with a jaw-dropping hook in the first 5 seconds. Use short punchy sentences. Include surprising facts and a strong call-to-action.",
        "tts": "(Speaking fast and energetically, with high enthusiasm — punchy delivery like a viral social media creator)",
        "video": "Fast-paced dynamic eye-catching visuals. Bold colors, rapid cuts, motion graphics, trending hyper-saturated aesthetic.",
        "image": "Viral social media aesthetic. Bold high-contrast, eye-catching. Bright saturated colors, dynamic angles, designed to stop the scroll.",
        "research": "Find the most shocking, surprising, counterintuitive or debated angles. What makes people share and react?",
    },
    "Product Ad": {
        "script": "Write a persuasive benefit-focused advertisement. Lead with the problem, introduce the solution, highlight 3 key benefits, include social proof, and close with a compelling call to action.",
        "tts": "(Speaking in a warm, confident, trustworthy sales voice — enthusiastic but professional and persuasive)",
        "video": "Sleek premium product advertisement. Clean backgrounds, product hero shots, smooth slow-motion, aspirational lifestyle imagery. Apple or Nike aesthetic.",
        "image": "Premium commercial photography. Clean backgrounds, perfect product lighting, aspirational lifestyle context. Sleek modern high-end brand aesthetic.",
        "research": "Find the strongest selling points, target audience pain points, and competitive advantages.",
    },
}

def get_style_profile(content_style: str) -> dict:
    """Returns the style profile for the given content style, falling back to Podcast."""
    return STYLE_PROFILES.get(content_style, STYLE_PROFILES["Podcast"])





def handle_api_errors(func):
    """A decorator to catch and handle common API errors, with automatic rate-limit retries."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except google_exceptions.ResourceExhausted as e:
                error_str = str(e.message) if hasattr(e, "message") else str(e)
                match = re.search(r"Please retry in ([0-9.]+)s", error_str)
                if match and attempt < max_retries - 1:
                    wait_time = float(match.group(1)) + 1.5
                    logging.warning(f"⏳ Rate limited by Google API. Auto-waiting {wait_time:.1f}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                elif "aiplatform.googleapis.com" in error_str:
                    error_message = f"Vertex AI Quota Exceeded: {error_str}. Ensure your project region is set correctly in settings."
                else:
                    error_message = f"Gemini API Quota Exceeded: {error_str}. Please check your usage or billing plan."
                logging.error(error_message, exc_info=True)
                raise RuntimeError(error_message) from e
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    logging.warning(f"⏳ HTTP 429 Rate Limit. Auto-waiting {wait_time}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                elif e.response.status_code == 429:
                    error_message = "API rate limit heavily exceeded. Please wait manually and try again."
                    logging.error(error_message, exc_info=True)
                    raise RuntimeError(error_message) from e
                raise
    return wrapper

class NewsApiClient:
    """Client for interacting with the NewsAPI."""
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"

    def get_news(self, topic: str) -> str:
        if not self.api_key:
            logging.warning("News API key is not configured. Skipping news gathering.")
            return ""
        try:
            params = {'q': topic, 'apiKey': self.api_key}
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            articles = response.json().get('articles', [])
            if articles:
                formatted_news = "\n\n--- Recent News Articles ---\n"
                for i, article in enumerate(articles[:3]):
                    formatted_news += f"Article {i+1}: {article.get('title', '')}\n"
                    formatted_news += f"   - {article.get('description', '')}\n"
                return formatted_news
            return ""
        except Exception as e:
            logging.error(f"Could not retrieve news from NewsAPI: {e}")
            return ""

class GoogleClient:
    """Client for all Google Generative AI interactions, now acting as a Unified Text Orchestrator."""
    def __init__(self, config):
        self.config = config
        self.api_key = config.get("GEMINI_API_KEY")
        if not self.api_key:
            logging.warning("Google API key is missing. Ensure Ollama or WaveSpeed is selected for text generation.")
        else:
            genai.configure(api_key=self.api_key)
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            self.text_model = genai.GenerativeModel(GEMINI_TEXT_MODEL, safety_settings=self.safety_settings)

    def _generate_text(self, prompt: str, as_json=False) -> str:
        """Dynamically routes text generation to Gemini, WaveSpeed, or Ollama."""
        engine = self.config.get("TEXT_ENGINE", "Gemini API")
        
        if engine == "Ollama":
            base_url = self.config.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip('/')
            model = self.config.get("OLLAMA_MODEL", "llama3")
            payload = {"model": model, "prompt": prompt, "stream": False}
            if as_json: payload["format"] = "json"
            logging.info(f"Sending prompt to local Ollama ({model})...")
            try:
                resp = requests.post(f"{base_url}/api/generate", json=payload, timeout=300)
                resp.raise_for_status()
                return resp.json().get("response", "")
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Ollama local generation failed: {e}")
                
        elif engine == "WaveSpeed AI":
            api_key = self.config.get("WAVESPEED_AI_KEY")
            if not api_key: raise ValueError("WaveSpeed AI key is missing for Text Engine.")
            # WaveSpeed LLM uses their 'any-llm' router model via the standard async task API.
            # The model_id is passed as the 'model' parameter to route to the underlying LLM.
            model_id = self.config.get("WAVESPEED_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            # Submit task to the WaveSpeed any-llm model endpoint
            submit_url = "https://api.wavespeed.ai/api/v3/wavespeed-ai/any-llm"
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
            }
            if as_json:
                payload["messages"][0]["content"] = prompt + "\n\nRespond ONLY with valid JSON."
            logging.info(f"Submitting text task to WaveSpeed LLM ({model_id})...")
            try:
                submit_resp = requests.post(submit_url, headers=headers, json=payload, timeout=60)
                submit_resp.raise_for_status()
                task_id = submit_resp.json().get("data", {}).get("id")
                if not task_id:
                    raise RuntimeError(f"WaveSpeed LLM did not return a task ID. Response: {submit_resp.text}")
                # Poll for result
                poll_url = WAVESPEED_POLL_URL.format(task_id)
                logging.info(f"WaveSpeed LLM task submitted (ID: {task_id}). Polling for result...")
                for _ in range(60):  # Poll up to 60 times (~120 seconds)
                    time.sleep(2)
                    poll_resp = requests.get(poll_url, headers=headers, timeout=30)
                    poll_resp.raise_for_status()
                    result = poll_resp.json().get("data", {})
                    status = result.get("status", "")
                    if status == "completed":
                        outputs = result.get("outputs", {})
                        text = outputs.get("text") or outputs.get("content") or str(outputs)
                        return text
                    elif status in ("failed", "cancelled"):
                        raise RuntimeError(f"WaveSpeed LLM task failed. Status: {status}. Details: {result}")
                raise RuntimeError("WaveSpeed LLM task timed out after 120 seconds.")
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 'N/A'
                body = e.response.text if e.response is not None else str(e)
                raise RuntimeError(f"WaveSpeed LLM request failed (HTTP {status_code}). Check your API key and model name '{model_id}'. Details: {body}")
            except Exception as e:
                raise RuntimeError(f"WaveSpeed text generation failed: {e}")
                    
        else: # Gemini API
            if not hasattr(self, 'text_model'): raise RuntimeError("Gemini API key not configured properly.")
            kwargs = {}
            if as_json: kwargs["generation_config"] = {"response_mime_type": "application/json"}
            response = self.text_model.generate_content(prompt, **kwargs)
            return response.text

    @handle_api_errors
    def deep_research(self, topic: str, language: str, news_client: NewsApiClient) -> str:
        logging.info(f"Conducting advanced deep research for '{topic}'...")
        external_data = news_client.get_news(topic)
        
        language_instruction = ""
        if language and language.lower() == 'urdu':
            language_instruction = "All output text must be written in Roman Urdu."
        elif language:
            language_instruction = f"All output text must be written in {language}."

        logging.info("Research Step 1: Identifying key facets and sub-topics...")
        facet_prompt = (
            f"Using Google Search, perform a deep analysis of the topic '{topic}'. "
            "Identify: "
            "1. Key sub-topics and foundational concepts. "
            "2. The main individuals, companies, or entities involved. "
            "3. The primary points of controversy, debate, or public questions. "
            f"Format this analysis as a structured brief. {language_instruction}"
        )
        
        engine = self.config.get("TEXT_ENGINE", "Gemini API")
        
        if engine == "Gemini API":
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": facet_prompt}]}], "tools": [{"google_search": {}}]}
            try:
                response = requests.post(api_url, json=payload, timeout=120)
                response.raise_for_status()
                response_json = response.json()
                facet_analysis = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if not facet_analysis: raise ValueError("No text content found in Gemini research (Facet Analysis).")
            except requests.exceptions.HTTPError:
                raise # Let the @handle_api_errors wrapper manage retries
            except Exception as e:
                logging.error(f"Failed during Research Step 1 (Facet Analysis): {e}")
                raise RuntimeError(f"Failed research step 1: {e}")
        else:
            logging.info("Using non-Gemini engine for research. Skipping native Google Search Tool and relying on NewsAPI context.")
            facet_analysis = self._generate_text(facet_prompt)

        logging.info("Research Step 2: Synthesizing final summary...")
        synthesis_prompt = (
            f"You are a research analyst. Your goal is to create a single, comprehensive, and well-structured summary on the topic '{topic}'. "
            "You must synthesize the following two sources of information: "
            f"\nSOURCE 1: A preliminary analysis of the topic's key facets:\n---START SOURCE 1---\n{facet_analysis}\n---END SOURCE 1---"
            f"\nSOURCE 2: A feed of recent news headlines:\n---START SOURCE 2---\n{external_data}\n---END SOURCE 2---"
            "\nYOUR TASK: "
            "Using ONLY the information provided in the sources above, write a detailed, synthesized summary. This summary must cover the topic's background, why it is trending, key facts, primary controversies/debates, and the future outlook. "
            "Ensure the summary is well-organized, factually dense, and coherent. "
            f"{language_instruction}"
        )
        
        return self._generate_text(synthesis_prompt)

    @handle_api_errors
    def generate_seo_metadata(self, topic: str, script: str) -> dict:
        logging.info("Generating expert SEO metadata from final script...")
        prompt = f"""
        Act as a world-class YouTube SEO strategist. Your task is to generate a complete, optimized metadata package for a video based on its final script.
        CRITICAL INSTRUCTIONS:
        1.  **Title:** Create a title that is keyword-rich at the beginning, creates intrigue, uses power words/numbers, and is under 70 characters.
        2.  **Description:** Write a 3-paragraph description. The first sentence must be a captivating hook with the main keywords. The rest should summarize the key points discussed in the script.
        3.  **Tags:** Generate 10-15 comma-separated tags, mixing broad and specific (long-tail) keywords. The first tag must be the main keyword.
        4.  **Output Format:** Your response MUST be a single, valid JSON object and nothing else. Do not include intros, explanations, or code blocks.
            -   JSON must have keys: "title", "description", "tags".
            -   **DO NOT** include timestamps in this output.
        **VIDEO TOPIC:** {topic}
        **FULL SCRIPT (for context):**
        ```
        {script}
        ```
        Generate the complete JSON metadata package now.
        """
        response_text = self._generate_text(prompt, as_json=True)
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            logging.warning("Initial JSON parsing failed for SEO. Attempting to extract and clean.")
            try:
                text = response_text
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    raise ValueError("No JSON object found in the SEO response.")
            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"Failed to decode JSON for SEO after fallback: {e}")
                return {"title": topic, "description": "Failed to generate description.", "tags": topic.replace(" ", ",")}

    @handle_api_errors
    def generate_podcast_script(self, topic: str, research: str, config: dict) -> str:
        logging.info("Generating script with style-aware TTS vocal instructions...")

        content_style = config.get("CONTENT_STYLE", "Podcast")
        is_podcast_mode = (content_style == "Podcast")
        podcast_sub_style = config.get("PODCAST_STYLE", "Informative News")
        script_length = config.get("SCRIPT_LENGTH", "Medium (~5 minutes)")
        story_arc = config.get("STORY_ARC", "None")

        # Pull style profile — single source of truth
        profile = get_style_profile(content_style)
        tts_instruction = profile["tts"]
        script_instruction = profile["script"]

        # For Podcast mode, allow podcast sub-style to further refine the tone
        podcast_sub_style_map = {
            "Informative News": "Adopt a balanced journalistic tone. Focus on clarity and factual accuracy.",
            "Comedy / Entertaining": "Inject humor, witty banter, and playful disagreements.",
            "Educational / Explainer": "Break down complex topics simply. Use analogies and examples.",
            "Motivational / Inspiring": "Use powerful uplifting language. Build towards an inspiring conclusion.",
            "Casual Conversational": "Create a relaxed, friends-chatting vibe with natural dialogue.",
            "Serious Debate": "Construct a structured argument with clear points and counterpoints.",
        }
        if is_podcast_mode:
            sub_instruction = podcast_sub_style_map.get(podcast_sub_style, script_instruction)
            script_instruction = f"{script_instruction} Sub-style: {sub_instruction}"

        language_instruction = "The entire script must be in English."
        if config.get("LANGUAGE_ENABLED", False):
            language = config.get("PODCAST_LANGUAGE", "English")
            if language.lower() == 'urdu': language_instruction = "The entire script must be in Roman Urdu."
            else: language_instruction = f"The entire script must be in {language}."

        length_instruction = f"The total word count must be appropriate for a '{script_length}' spoken video."
        story_arc_prompt = f"Structure the script to follow the '{story_arc}' narrative arc." if story_arc != "None" else ""

        if is_podcast_mode:
            logging.info("Generating DUAL-SPEAKER script for Podcast mode.")
            host, guest = config.get("HOST_NAME", "Alex"), config.get("GUEST_NAME", "Maya")
            host_persona = config.get("HOST_PERSONA", "")
            guest_persona = config.get("GUEST_PERSONA", "")
            sub_count = config.get("SUBSCRIBE_COUNT", 3)
            sub_message = config.get("SUBSCRIBE_MESSAGE", "").replace("{channel}", config.get("CHANNEL_NAME", "My AI Channel"))
            placement_instruction = (f"Insert about {sub_count} reminders randomly in the host's dialogue." if config.get("SUBSCRIBE_RANDOM") else f"Insert exactly {sub_count} reminders evenly spaced.")

            prompt = f"""
You are an expert scriptwriter. Create an engaging dual-host podcast script.

**CONTENT STYLE:** {content_style}
**STYLE INSTRUCTION:** {script_instruction}
**TOPIC:** {topic}

**HOSTS:**
- Host ({host}): {host_persona}
- Guest ({guest}): {guest_persona}

**DIALOGUE RULES (CRITICAL):**
- Simulate a real unscripted conversation. Use natural fillers ("Right," "Wow," "So...").
- Keep speaking turns short (2-3 sentences). The host must REACT to the guest.
- VOCAL DIRECTIONS (MANDATORY): Prepend EVERY line for both {host} and {guest} with a parenthetical direction. Base vocal style: {tts_instruction}.

**STRUCTURE:** Cold Open/Hook → Introduction → Main Discussion → Conclusion → Outro

**ENGAGEMENT:** Insert this message {sub_count} times: "{sub_message}". {placement_instruction}

**FORMATTING:** EVERY line must start with `{host}:` or `{guest}:`.
- {language_instruction}
- {length_instruction}
- {story_arc_prompt}

**RESEARCH:**
```
{research}
```
Generate the complete script now.
"""
        else:
            logging.info(f"Generating SINGLE-SPEAKER script for '{content_style}' mode.")
            narrator_persona = config.get("HOST_PERSONA", "")

            prompt = f"""
You are an expert scriptwriter specializing in '{content_style}' content. Create an immersive, authentic script.

**CONTENT STYLE:** {content_style}
**STYLE INSTRUCTION:** {script_instruction}
**TOPIC:** {topic}
**NARRATOR PERSONA:** {narrator_persona}

**SCRIPT REQUIREMENTS:**
- This is a single-voice narration. Write ONLY the narration — no speaker labels.
- VOCAL DIRECTIONS (MANDATORY): Add parenthetical vocal directions throughout. Overall style: {tts_instruction}.
- Example: {tts_instruction} The story begins...
- {language_instruction}
- {length_instruction}
- {story_arc_prompt}

**STRUCTURE:** Hook → Introduction → Main Body → Conclusion

**RESEARCH:**
```
{research}
```
Generate the complete script now, ensuring all vocal directions match the '{content_style}' style.
"""

        return self._generate_text(prompt)


    @handle_api_errors
    def generate_image_prompt_for_segment(self, content_style: str, topic: str, script_segment: str, style_guide: str = "") -> str:
        logging.info(f"Generating image prompt for segment based on style: '{content_style}'...")
        profile = get_style_profile(content_style)
        image_style = profile["image"]
        extra = f" Additional style notes: {style_guide}" if style_guide and style_guide.strip() else ""
        refinement_prompt = (
            f"You are an expert prompt engineer for an AI image generator. "
            f"Generate a single concise visual prompt (under 60 words) for this scene:\n"
            f"Topic: {topic}\n"
            f"Script segment: '{script_segment}'\n"
            f"Visual style MUST match this aesthetic: {image_style}{extra}\n"
            "Output ONLY the final image prompt, nothing else."
        )
        return self._generate_text(refinement_prompt).strip().replace('"', '')


    @handle_api_errors
    def generate_thumbnail_prompts(self, topic: str, title_text: str) -> dict:
        logging.info("Generating dynamic prompts for split-screen thumbnail...")
        prompt = f"""
        Act as a viral YouTube thumbnail designer. Generate two separate image prompts for a split-screen thumbnail.
        The left side is a photorealistic, emotional character relevant to the topic. The right side is a graphic design with the video title.
        VIDEO TOPIC: {topic}
        VIDEO TITLE: {title_text}
        Your entire response MUST be a single, valid JSON object with two keys: "character_prompt" and "text_prompt".
        """
        response_text = self._generate_text(prompt, as_json=True)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON for thumbnail prompts. Raw response: {response_text}")
            return {
                "character_prompt": f"A photorealistic, cinematic close-up of a person looking shocked and amazed, reacting to the topic of '{topic}'.",
                "text_prompt": f"A graphic design for a YouTube thumbnail title card. A dark blue background with the text '{title_text}' in large, bold, yellow and white font."
            }
    
    @handle_api_errors
    def generate_chapter_titles(self, script: str) -> list:
        logging.info("Identifying logical chapter titles from script...")
        prompt = f"""
        You are a video editor. Read the following podcast script. Your task is to identify 5-10 main logical chapters or topic shifts in the conversation.
        The first chapter MUST be "Intro".
        Return ONLY a valid JSON list of strings and nothing else. Do not add explanations.
        Example: ["Intro", "The Early Days", "A Surprising Discovery", "Conclusion"]
        --- SCRIPT ---
        {script}
        --- END SCRIPT ---
        Generate the JSON list of chapter titles now.
        """
        response = self.text_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        try:
            text = response.text.strip().replace("```json", "").replace("```", "")
            return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            logging.error(f"Failed to parse chapter titles JSON. Raw: {getattr(response, 'text', 'NO TEXT')}")
            return ["Intro"]

    @handle_api_errors
    def gemini_nanobanana_image(self, prompt: str, output_path: str):
        logging.info(f"Generating image with Gemini API (gemini-2.5-flash-image-preview): '{prompt}'")
        model = genai.GenerativeModel(NANO_BANANA_IMAGE_MODEL, safety_settings=self.safety_settings)
        response = model.generate_content(prompt)
        
        image_part = response.candidates[0].content.parts[0]
        if "image" not in image_part.mime_type:
            raise RuntimeError(f"API did not return an image. It may have returned text instead: {response.text}")
        
        image_data = image_part.inline_data.data
        with open(output_path, "wb") as f: 
            f.write(base64.b64decode(image_data))
        logging.info(f"Image successfully saved to {output_path}")

    @handle_api_errors
    def vertex_nanobanana_image(self, prompt: str, output_path: str):
        if not vertexai or not ImageGenerationModel:
            raise RuntimeError("Vertex AI libraries not installed correctly.")
        
        logging.info(f"Generating image with Vertex AI (Imagen 3): '{prompt}'")
        vertexai.init()
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        response = model.generate_images(prompt=prompt, number_of_images=1, aspect_ratio="16:9")
        response[0].save(location=output_path, include_generation_parameters=True)
        logging.info(f"Vertex AI image successfully saved to {output_path}")

    @handle_api_errors
    def fact_check_script(self, script: str, language: str) -> str:
        logging.info("Fact-checking script...")
        language_instruction = "Your entire response must be in English."
        if language and language.lower() == 'urdu': language_instruction = "Your entire response must be in Roman Urdu."
        elif language: language_instruction = f"Your entire response must be in {language}."
        prompt = f"Review the script for factual accuracy. List issues and suggest corrections.\n{language_instruction}\n\nScript:\n{script}"
        return self._generate_text(prompt)

    @handle_api_errors
    def revise_script(self, script: str, fact_check_results: str) -> str:
        logging.info("Revising script based on fact-check...")
        prompt = f"Revise the script based on the fact-check. Output only the revised script.\n\nFact-Check:\n{fact_check_results}\n\nOriginal Script:\n{script}"
        return self._generate_text(prompt)

    @handle_api_errors
    def generate_tts(self, script: str, output_path: str, tts_config: dict):
        logging.info("Generating audio with real Gemini TTS...")
        
        script_for_api = script.split('Text :')[-1].strip() if 'Text :' in script else script
        
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent?key={self.api_key}"
        
        is_podcast_mode = tts_config.get("CONTENT_STYLE") == "Podcast"
        host_name = tts_config.get("HOST_NAME", "Alex")
        guest_name = tts_config.get("GUEST_NAME", "Maya")
        
        is_multi_speaker_script = is_podcast_mode and f"{host_name}:" in script_for_api and f"{guest_name}:" in script_for_api
        if is_multi_speaker_script:
            logging.info("Multi-speaker script detected. Forcing multi-speaker TTS mode.")
        else:
            logging.info("Single-speaker script detected. Using single voice.")

        CHUNK_SIZE_LIMIT = 4500
        script_lines = script_for_api.split('\n')
        script_chunks = []
        current_chunk = ""

        for line in script_lines:
            if len(current_chunk) + len(line) + 1 > CHUNK_SIZE_LIMIT:
                if current_chunk: script_chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = f"{current_chunk}\n{line}" if current_chunk else line
        if current_chunk: script_chunks.append(current_chunk)

        if len(script_chunks) > 1:
            logging.info(f"Script is long, splitting into {len(script_chunks)} chunks to ensure quality.")

        all_audio_data = []

        for i, chunk in enumerate(script_chunks):
            logging.info(f"Generating audio for chunk {i+1}/{len(script_chunks)}...")
            payload = {
                "contents": [{"parts": [{"text": chunk}]}],
                "generationConfig": {"responseModalities": ["AUDIO"]},
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }
            
            if is_multi_speaker_script:
                 payload["generationConfig"]["speechConfig"] = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
                    {"speaker": host_name, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": tts_config["SPEAKER1"]}}},
                    {"speaker": guest_name, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": tts_config["SPEAKER2"]}}}
                ]}}
            else:
                 payload["generationConfig"]["speechConfig"] = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": tts_config.get("SPEAKER1", "Kore")}}}

            
            response = requests.post(api_url, json=payload, timeout=300)
            response.raise_for_status()
            resp_json = response.json()
            candidates = resp_json.get("candidates", [])
            if not candidates: raise RuntimeError(f"TTS failed: No candidates in response. {resp_json}")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts: raise RuntimeError(f"TTS failed: No content parts. Finish Reason: '{candidates[0].get('finishReason', 'UNKNOWN')}'.")

            audio_data = parts[0].get("inlineData", {}).get("data")
            if not audio_data: raise RuntimeError(f"TTS failed: No audio data. API may have returned text: '{parts[0].get('text', '')}'")
            
            all_audio_data.append(base64.b64decode(audio_data))

        logging.info("All audio chunks generated. Combining into a single file...")
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
            for audio_data in all_audio_data:
                wf.writeframes(audio_data)

    @handle_api_errors
    def generate_video_prompt(self, topic: str, script_segment: str, style_guide: str, content_style: str = "Podcast") -> str:
        logging.info(f"Generating dynamic video prompt for style '{content_style}' and segment...")
        profile = get_style_profile(content_style)
        video_style = profile["video"]
        # Allow user's custom style guide to augment the profile
        extra = f" Additional style notes: {style_guide}" if style_guide and style_guide.strip() else ""
        prompt = f"""
You are an expert prompt engineer for a text-to-video AI model.
Create ONE highly descriptive video prompt (under 100 words) for this specific scene.
Rules:
1. Visually describe the scene happening in the script segment.
2. The visual style MUST match: {video_style}{extra}
3. Output ONLY the final video prompt, nothing else.
TOPIC: {topic}
SCENE DIALOGUE/NARRATION: '{script_segment}'
Generate the final video prompt now.
"""
        return self._generate_text(prompt).strip().replace('"', '')


    @handle_api_errors
    def vertex_ai_text_to_video(self, prompt: str, output_path: str, aspect_ratio: str):
        if not vertexai: 
            raise RuntimeError("Vertex AI libraries not installed correctly.")
        
        logging.info(f"Generating video with Vertex AI: '{prompt}'")
        vertexai.init()
        model = GenerativeModel(VEO_MODEL_ID)
        final_prompt = f"{prompt} The video must be in a {aspect_ratio} aspect ratio."
        
        logging.info("Sending video generation request to Vertex AI...")
        response = model.generate_content(
            [final_prompt],
            generation_config={"response_mime_type": "video/mp4"}
        )

        video_part = response.candidates[0].content.parts[0]
        if "video" not in video_part.mime_type:
            raise RuntimeError(f"Vertex AI did not return a video. Response: {response.text}")
            
        video_bytes = video_part._raw_part.inline_data.data
        with open(output_path, "wb") as f:
            f.write(video_bytes)
        logging.info(f"Vertex AI video saved to {output_path}")


class WaveSpeedClient:
    """Client for securely interacting with the WaveSpeed AI routing endpoints."""
    def __init__(self, api_key):
        self.api_key = api_key

    def _poll_and_download(self, req_id: str, output_path: str, timeout: int = 600):
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        poll_url = WAVESPEED_POLL_URL.format(req_id)
        start_time = time.time()
        while time.time() - start_time < timeout:
            poll_response = requests.get(poll_url, headers=headers, timeout=60)
            poll_response.raise_for_status()
            status = poll_response.json().get("data", {}).get("status")
            if status == "completed":
                logging.info("Generation completed dynamically. Downloading output asset...")
                url = poll_response.json()["data"]["outputs"][0]
                with open(output_path, "wb") as f: f.write(requests.get(url).content)
                logging.info(f"Asset successfully saved to {output_path}"); return
            elif status == "failed":
                raise RuntimeError(f"WaveSpeed Model task failed: {poll_response.json()['data'].get('error')}")
            else:
                logging.info(f"Task status is '{status}'. Yielding and Waiting...")
                time.sleep(10)
        raise TimeoutError("WaveSpeed model request timed out tracking loop.")

    def text_to_video(self, model_id: str, prompt: str, output_path: str, size: str):
        if not self.api_key: raise ValueError("WaveSpeed AI key is missing.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        api_url = WAVESPEED_BASE_ENDPOINT.format(model_id)
        # Map human-readable size strings to the short aspect_ratio format WaveSpeed expects
        aspect_ratio_map = {
            "16:9 (Horizontal)": "16:9",
            "9:16 (Vertical)": "9:16",
            "1:1 (Square)": "1:1",
            "16:9": "16:9",
            "9:16": "9:16",
            "1:1": "1:1",
        }
        aspect_ratio = aspect_ratio_map.get(size, "16:9")
        payload = {"prompt": prompt, "aspect_ratio": aspect_ratio}
        logging.info(f"Sending video task to WaveSpeed via {model_id}...")
        initial_response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        if not initial_response.ok:
            logging.error(f"WaveSpeed video error ({initial_response.status_code}): {initial_response.text}")
        initial_response.raise_for_status()
        req_id = initial_response.json().get("data", {}).get("id")
        self._poll_and_download(req_id, output_path, timeout=600)

    def text_to_image(self, model_id: str, prompt: str, output_path: str):
        if not self.api_key: raise ValueError("WaveSpeed AI key is missing.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        api_url = WAVESPEED_BASE_ENDPOINT.format(model_id)
        payload = {"prompt": prompt, "format": "png", "aspect_ratio": "16:9"}
        logging.info(f"Sending image task to WaveSpeed via {model_id}...")
        initial_response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        initial_response.raise_for_status()
        req_id = initial_response.json().get("data", {}).get("id")
        self._poll_and_download(req_id, output_path, timeout=600)

    def text_to_speech(self, model_id: str, text: str, output_path: str):
        if not self.api_key: raise ValueError("WaveSpeed AI key is missing.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        api_url = WAVESPEED_BASE_ENDPOINT.format(model_id)
        payload = {"text": text, "voice": "Brian"}
        logging.info(f"Sending text-to-speech task to WaveSpeed via {model_id}...")
        initial_response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        initial_response.raise_for_status()
        
        resp_json = initial_response.json()
        if "url" in resp_json:
             url = resp_json["url"]
             with open(output_path, "wb") as f: f.write(requests.get(url).content)
             return
             
        req_id = resp_json.get("data", {}).get("id")
        self._poll_and_download(req_id, output_path, timeout=600)
