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
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
WAVESPEED_POLL_URL = "https://api.wavespeed.ai/api/v3/predictions/{}/result"
WAVESPEED_BASE_ENDPOINT = "https://api.wavespeed.ai/api/v3/{}"
VEO_MODEL_ID = "veo-3.0-generate-preview" # For Vertex AI Video
NANO_BANANA_IMAGE_MODEL = "gemini-2.5-flash-image-preview" # For Vertex AI Image

# --- Style Profiles: Single source of truth for all content styles ---
STYLE_PROFILES = {
    "Podcast": {
        "script": "Craft an ultra-realistic, multi-layered dual-host podcast conversation. Utilize advanced conversational dynamics: interruptions, active listening ('mm-hmm', 'wow'), tangents, and callbacks. The dialogue must flow organically, balancing deep analytical insights with accessible humor and relatable analogies.",
        "tts": "(Speaking with authentic conversational cadence, utilizing natural pauses, micro-breaths, and varied intonation to simulate spontaneous unscripted thought)",
        "video": "Cinematic 4K podcast studio, professional multi-camera setup. Volumetric soft-box lighting, rich amber and teal color grading, shallow depth of field (f/1.8). High-end broadcast aesthetic, soundproof acoustic panels in the blurred background.",
        "image": "Ultra-realistic 8k architectural photography of a modern high-end podcast studio. Warm ambient lighting, professional condenser microphones, cinematic depth of field, hyper-detailed textures.",
        "research": "Uncover counter-narratives, deep-cut historical analogies, controversial expert opinions, and hidden connections that challenge conventional wisdom.",
    },
    "ASMR Video": {
        "script": "Compose a deeply immersive, sensory-rich script. Prioritize auditory and tactile descriptions over action. Sentences must be profoundly rhythmic, slow, and hypnotic. Utilize repetition and phonetic softness (sibilance) to trigger autonomic meridian responses (ASMR).",
        "tts": "(Whispering with extreme intimacy and softness. Enunciate every syllable with deliberate, glacial pacing. Employ intentional lip smacks and breathy pauses)",
        "video": "Hyper-macro 8K cinematography. Slow-motion 120fps. Exquisite focus on tactile textures (velvet, liquid, powder, wood grain). Dreamlike pastel color grading, volumetric golden hour lighting, hypnotic and fluid motion.",
        "image": "Award-winning macro photography. Razor-sharp subject focus with buttery smooth bokeh. Earth tones, soft diffused natural light, conveying absolute tranquility and stillness.",
        "research": "Identify highly specific sensory details, textural anomalies, and rhythmic acoustic properties relevant to the topic.",
    },
    "Documentary": {
        "script": "Adopt the gravitas of a BBC/HBO premium documentary. Structure the narrative with a cold open, historical contextualization, rising tension, and a profound philosophical conclusion. Interweave hard empirical data with emotionally resonant human-interest subplots.",
        "tts": "(Speaking with immense gravitas, profound resonance, and measured authority. Utilize strategic silence to let heavy statements linger)",
        "video": "Award-winning IMAX documentary cinematography. Sweeping anamorphic aerial drone shots, slow deliberate push-ins (Ken Burns effect), dramatic chiaroscuro lighting, desaturated gritty color palette (teal/orange bias).",
        "image": "Pulitzer-prize winning photojournalism aesthetic. High-contrast black-and-white or heavily desaturated cinematic color. Gritty realism, emotional depth, perfect rule-of-thirds composition.",
        "research": "Source primary empirical data, verified historical records, direct quotes from leading academics, and profound socio-economic impacts.",
    },
    "Story": {
        "script": "Construct a masterful narrative utilizing the Hero's Journey framework. Establish deep character motivations, escalating stakes, and visceral emotional beats. Employ 'show, don't tell' methodology through vivid environmental storytelling and sensory anchoring.",
        "tts": "(Speaking with dynamic theatrical range. Shift seamlessly between hushed tension during buildup and explosive energy during the climax)",
        "video": "Hollywood blockbuster cinematography (ARRI Alexa 65). Dramatic motivated lighting, dynamic camera blocking, lush stylized color grading (e.g., Cyberpunk neon, or Fantasy golden hour). Evocative and atmospheric.",
        "image": "Concept art by Craig Mullins or Greg Rutkowski. Epic scale, masterful digital painting techniques, dramatic lighting, intense emotional resonance, hyper-detailed foreground.",
        "research": "Extract the core dramatic conflict, identifying the specific 'inciting incident' and the human cost or emotional triumph at the center of the topic.",
    },
    "Kids Story": {
        "script": "Write a highly engaging, cognitively optimized script for young children (ages 4-8). Employ rhythmic rhyming structures, repetitive learning anchors, and highly visual, optimistic language. Structure around a clear, easily digestible moral lesson.",
        "tts": "(Speaking with hyper-animated, exuberant energy. Highly melodic intonation, exaggerated expressions of surprise and joy, crisp and slow articulation)",
        "video": "High-budget 3D animation (Pixar/Disney aesthetic). Vibrant, hyper-saturated primary colors. Bouncy, physics-defying fluid motion. Soft, plush textures, whimsical environments, and radiant volumetric lighting.",
        "image": "Premium 3D CGI render, Unreal Engine 5. Adorable, expressive character designs. Bright, cheerful lighting, pastel color palettes, magical atmosphere, highly detailed but soft edges.",
        "research": "Identify the foundational educational concepts (colors, numbers, simple ethics) embedded within the topic and translate them into playful analogies.",
    },
    "Horror Story": {
        "script": "Engineer a narrative of psychological terror. Utilize the 'slow burn' technique, dripping with existential dread. Focus on the uncanny valley, isolation, and sensory deprivation. Avoid jump-scares in favor of deeply unsettling, lingering descriptive horror.",
        "tts": "(Speaking with a hollow, breathy, and deeply sinister undertone. Erratic pacing, sudden drops to a whisper, conveying genuine terror and instability)",
        "video": "Found-footage or A24-style psychological horror cinematography. Extreme low-key lighting, heavy film grain, unsettling Dutch angles, claustrophobic framing. Sickly green/yellow color grading, deep crushing blacks.",
        "image": "Macabre fine-art photography (Beksinski or Giger inspired). Terrifying surrealism, liminal spaces, extreme shadows, muted desolate colors, evoking intense claustrophobia and paranoia.",
        "research": "Uncover the most disturbing, unsolved, or psychologically damaging historical facts, local folklore, or morbid scientific anomalies related to the topic.",
    },
    "Viral Video": {
        "script": "Optimize for maximum algorithmic retention (TikTok/Shorts). Deploy an aggressive pattern-interrupt hook in the first 3 seconds. Utilize rapid-fire delivery, relentless dopamine hits (curiosity gaps), and a high-stakes call-to-action.",
        "tts": "(Speaking with relentless, high-octane energy. Fast-paced, extremely punchy, zero dead air, projecting absolute confidence and urgency)",
        "video": "Hyper-kinetic social media editing style. Rapid snap-zooms, aggressive motion graphics, glowing neon text overlays, whip-pan transitions. Insanely high saturation and contrast.",
        "image": "Clickbait YouTube thumbnail aesthetic. Over-saturated colors, extreme close-ups of shocked expressions, glowing outlines, high-contrast dynamic angles designed for maximum CTR.",
        "research": "Identify the absolute most shocking, counter-intuitive, or controversial 'secret' regarding the topic that challenges common knowledge.",
    },
    "Product Ad": {
        "script": "Engineer a high-converting direct-response copywriting script. Utilize the AIDA framework (Attention, Interest, Desire, Action). Agitate a specific pain point intensely before introducing the product as the ultimate, exclusive paradigm shift.",
        "tts": "(Speaking with magnetic, authoritative sales charisma. Smooth, persuasive, confident, and inherently trustworthy)",
        "video": "Premium commercial cinematography (Apple/Nike aesthetic). Sleek minimalist backgrounds, macroscopic product beauty shots, buttery smooth slow-motion, elegant typography, pristine studio lighting.",
        "image": "High-end commercial product photography. Razor-sharp focus, infinite white or sleek dark backgrounds, dramatic edge lighting, emphasizing premium build quality and luxury.",
        "research": "Determine the core buyer psychology, specific pain points, and the ultimate unique value proposition (UVP) that destroys competitors.",
    },
}

def get_style_profile(content_style: str) -> dict:
    """Returns the style profile for the given content style, falling back to Podcast."""
    return STYLE_PROFILES.get(content_style, STYLE_PROFILES["Podcast"])





def handle_api_errors(func):
    """A decorator to catch and handle common API errors, with automatic rate-limit retries."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 5
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
                    wait_time = 30 * (attempt + 1)
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
            
            model_id = self.config.get("WAVESPEED_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            # Using the proper OpenAI-compatible Chat Completions API as per WaveSpeed docs
            submit_url = "https://api.wavespeed.ai/v1/chat/completions"
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
            }
            if as_json:
                payload["response_format"] = {"type": "json_object"}
                payload["messages"][0]["content"] = prompt + "\n\nRespond ONLY with valid JSON."
                
            logging.info(f"Generating text via WaveSpeed LLM ({model_id}) using v1/chat/completions...")
            try:
                response = requests.post(submit_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                response_json = response.json()
                text = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not text:
                    raise RuntimeError(f"WaveSpeed LLM returned empty content. Response: {response.text}")
                return text
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

        engine = self.config.get("TEXT_ENGINE", "Gemini API")
        
        prompt = (
            f"You are a research analyst. Create a single, comprehensive summary on the topic '{topic}'. "
            f"Use Google Search to find key sub-topics, entities, and controversies. "
            f"Also, incorporate these recent news headlines if relevant:\n{external_data}\n"
            "Your summary must cover the topic's background, why it is trending, key facts, primary controversies, and future outlook. "
            f"Be factual, dense, and coherent. {language_instruction}"
        )
        
        if engine == "Gemini API":
            logging.info("Using Gemini native Google Search for single-pass research...")
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TEXT_MODEL}:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
            try:
                response = requests.post(api_url, json=payload, timeout=120)
                response.raise_for_status()
                response_json = response.json()
                summary = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if not summary: raise ValueError("No text content found in Gemini research.")
                return summary
            except requests.exceptions.HTTPError:
                raise # Let the @handle_api_errors wrapper manage retries
            except Exception as e:
                logging.error(f"Failed during Research: {e}")
                raise RuntimeError(f"Failed research: {e}")
        else:
            logging.info("Using non-Gemini engine for research. Relying on NewsAPI context.")
            return self._generate_text(prompt)

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
            return json.loads(response_text)
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

        word_limits = {
            "Micro (< 1 minute)": "STRICTLY under 130 words in total (around 45 seconds of speech)",
            "Short (~2 minutes)": "STRICTLY between 250 to 300 words in total (around 2 minutes of speech)",
            "Medium (~5 minutes)": "STRICTLY between 700 to 800 words in total (around 5 minutes of speech)",
            "Long (~10 minutes)": "STRICTLY between 1400 to 1500 words in total (around 10 minutes of speech)"
        }
        target_words = word_limits.get(script_length, "STRICTLY between 700 to 800 words in total")
        length_instruction = f"CRITICAL REQUIREMENT: The total word count MUST be {target_words}. Do not exceed this limit under any circumstances."
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
- VOCAL TONE: The overall vocal style should be: {tts_instruction}. Add brief, varied acting notes in parentheses occasionally (e.g., (Laughs), (Surprised), (Thoughtful)). Do NOT repeat the same direction on every line.

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
- VOCAL TONE: The overall vocal style should be: {tts_instruction}. Add brief, varied acting notes in parentheses occasionally (e.g., (Chuckles), (Serious tone)).
- Example: (Enthusiastically) The story begins...
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
            f"IMPORTANT: If characters are in the scene, explicitly describe dynamic human poses and gestures (e.g., pointing at camera, looking shocked, gesturing with hands, leaning thoughtfully). Avoid stiff standing poses.\n"
            "Output ONLY the final image prompt, nothing else."
        )
        return self._generate_text(refinement_prompt).strip().replace('"', '')

    @handle_api_errors
    def generate_image_prompts_batch(self, content_style: str, topic: str, script_segments: list, style_guide: str = "") -> list:
        logging.info(f"Batch generating {len(script_segments)} image prompts in a single API call...")
        profile = get_style_profile(content_style)
        image_style = profile["image"]
        extra = f" Additional style notes: {style_guide}" if style_guide and style_guide.strip() else ""
        
        segments_json = json.dumps(script_segments)
        
        prompt = (
            f"You are an expert prompt engineer for an AI image generator. "
            f"I have a video script about '{topic}'. "
            f"Below is a JSON array of script segments. For EACH segment, generate a concise visual prompt (under 60 words). "
            f"Visual style MUST match this aesthetic: {image_style}{extra}\n"
            f"IMPORTANT: If characters are in the scene, explicitly describe dynamic human poses and gestures (e.g., pointing, looking shocked, gesturing with hands). Avoid stiff poses.\n"
            f"Your output MUST be a valid JSON array of strings, where each string is the image prompt for the corresponding segment.\n"
            f"Script segments:\n{segments_json}"
        )
        
        response_text = self._generate_text(prompt, as_json=True)
        try:
            prompts = json.loads(response_text)
            if isinstance(prompts, dict) and "prompts" in prompts:
                prompts = prompts["prompts"]
            if not isinstance(prompts, list):
                raise ValueError("Expected a JSON array of strings.")
            while len(prompts) < len(script_segments):
                prompts.append(f"A cinematic shot reflecting the topic of {topic}.")
            return prompts[:len(script_segments)]
        except Exception as e:
            logging.error(f"Failed to decode batch JSON prompts: {e}")
            return [f"A cinematic shot reflecting the topic of {topic}."] * len(script_segments)


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
        response_text = self._generate_text(prompt, as_json=True)
        try:
            text = response_text.strip().replace("```json", "").replace("```", "")
            return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            logging.error(f"Failed to parse chapter titles JSON. Raw: {response_text}")
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
            chunk = chunk.strip()
            if not chunk:
                logging.info(f"Skipping empty chunk {i+1}/{len(script_chunks)}")
                continue

            logging.info(f"Generating audio for chunk {i+1}/{len(script_chunks)}...")
            
            instruction = (
                "You are a highly realistic human voice actor. Deliver the following script with "
                "natural emotion, dynamic pacing, breathing, and conversational tone to completely "
                "eliminate any robotic feel. Do not read this instruction, ONLY read the script:\\n\\n"
            )
            
            payload = {
                "contents": [{"parts": [{"text": instruction + chunk}]}],
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
3. IMPORTANT: If characters are in the scene, explicitly describe dynamic human poses and cinematic motion (e.g., gesturing enthusiastically, walking toward the camera, leaning in closely). Avoid stiff, static standing poses.
4. Output ONLY the final video prompt, nothing else.
TOPIC: {topic}
SCENE DIALOGUE/NARRATION: '{script_segment}'
Generate the final video prompt now.
"""
        return self._generate_text(prompt).strip().replace('"', '')

    @handle_api_errors
    def generate_search_query(self, topic: str, script_segment: str) -> str:
        """Generates a short 1-3 word search query for fetching stock video (e.g. from Pixabay)."""
        prompt = f"""
        Topic: {topic}
        Script Segment: {script_segment}
        
        Extract the most visually prominent subject from this script segment into a short, 1 to 3 word keyword search query suitable for a stock video database like Pixabay. 
        Only output the keywords, no punctuation or explanation.
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
                data = poll_response.json().get("data", {})
                outputs = data.get("outputs", [])
                if not outputs:
                    raise RuntimeError("WaveSpeed Model task completed but returned no outputs.")
                url = outputs[0] if isinstance(outputs, list) else outputs.get("url", str(outputs))
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

    def text_to_speech(self, model_id: str, text: str, output_path: str, voice: str = "Brian"):
        if not self.api_key: raise ValueError("WaveSpeed AI key is missing.")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        api_url = WAVESPEED_BASE_ENDPOINT.format(model_id)
        payload = {"text": text, "voice": voice}
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

class PixabayClient:
    """Client for fetching stock footage (B-Roll) from Pixabay."""
    def __init__(self, api_key):
        self.api_key = api_key
        
    def download_video(self, query: str, output_path: str, is_vertical: bool = False) -> bool:
        """Searches Pixabay for a video matching the query and downloads it."""
        if not self.api_key:
            logging.warning("Pixabay API key not provided. Skipping stock footage search.")
            return False
            
        logging.info(f"Searching Pixabay for video: '{query}'")
        try:
            orientation = "vertical" if is_vertical else "horizontal"
            url = f"https://pixabay.com/api/videos/?key={self.api_key}&q={requests.utils.quote(query)}&per_page=3&safesearch=true&orientation={orientation}"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("totalHits", 0) == 0 or not data.get("hits"):
                logging.warning(f"No Pixabay videos found for query '{query}'.")
                return False
                
            # Get highest quality MP4 link from the first hit
            first_hit = data["hits"][0]
            videos = first_hit.get("videos", {})
            
            # Prefer large, then medium, then small
            video_url = None
            for size in ["large", "medium", "small"]:
                if size in videos and videos[size].get("url"):
                    video_url = videos[size]["url"]
                    break
                    
            if not video_url:
                return False
                
            logging.info(f"Downloading Pixabay video from: {video_url}")
            vid_resp = requests.get(video_url, timeout=30)
            vid_resp.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(vid_resp.content)
            logging.info(f"Successfully downloaded Pixabay B-roll to {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to fetch Pixabay video for '{query}': {e}")
            return False
