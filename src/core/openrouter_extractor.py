"""OpenRouter VLM Extractor - Lightweight wrapper for multi-model support"""
from typing import List, Optional, Tuple
import logging
import requests
import base64
from io import BytesIO
from pathlib import Path

try:
    from pdf2image import convert_from_path, convert_from_bytes
    from PIL import Image
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

logger = logging.getLogger(__name__)


class OpenRouterExtractor:
    """Simple OpenRouter VLM extractor"""
    
    MODELS = {
        'free': 'google/gemini-2.0-flash-exp:free',        # FREE! $0.00
        'balanced': 'google/gemini-2.0-flash-lite-001',     # $0.075/1M = ~$0.00008/page
        'premium': 'google/gemini-2.5-pro'                  # $1.25/1M = ~$0.0013/page
    }
    
    PROMPT = """Extract ALL text from this document image. Preserve structure (headers, tables, lists). Output clean markdown only."""
    
    def __init__(self, api_key: str, model: str = 'free'):
        if not DEPS_AVAILABLE:
            raise ImportError("pip install pdf2image pillow requests")
        self.api_key = api_key
        self.model_id = self.MODELS.get(model, model)
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        logger.info(f"🤖 OpenRouter: {self.model_id}")
    
    def extract_from_pdf(self, pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None, dpi: int = 200) -> Tuple[List[str], float]:
        """Extract text from PDF
        
        Returns:
            Tuple[List[str], float]: (pages, total_cost_usd)
        """
        if pdf_path:
            images = convert_from_path(pdf_path, dpi=dpi)
        else:
            images = convert_from_bytes(pdf_bytes, dpi=dpi)
        
        pages = []
        total_cost = 0.0
        
        for i, img in enumerate(images, 1):
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Call OpenRouter
            try:
                response = requests.post(
                    self.url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_id,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": self.PROMPT},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                            ]
                        }]
                    },
                    timeout=60
                )
                response.raise_for_status()
                response_data = response.json()
                text = response_data['choices'][0]['message']['content']
                pages.append(text.strip())
                
                # Extract actual cost from OpenRouter response
                if 'usage' in response_data:
                    # OpenRouter returns cost in USD directly (if available)
                    page_cost = response_data['usage'].get('total_cost', 0.0)
                    if page_cost > 0:
                        total_cost += page_cost
                        logger.info(f"✅ Page {i}: {len(text)} chars, cost=${page_cost:.6f}")
                    else:
                        logger.info(f"✅ Page {i}: {len(text)} chars")
                else:
                    logger.info(f"✅ Page {i}: {len(text)} chars")
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"⚠️  Page {i}: Rate limited (429). Continuing with partial results...")
                    # Don't add error placeholder, just skip this page
                    # VLM will still return pages that succeeded
                else:
                    logger.error(f"❌ Page {i} failed: {e}")
                    pages.append(f"[Error: {str(e)}]")
            except Exception as e:
                logger.error(f"❌ Page {i} failed: {e}")
                pages.append(f"[Error: {str(e)}]")
        
        logger.info(f"💰 Total VLM cost: ${total_cost:.6f} for {len(pages)} pages")
        return pages, total_cost
