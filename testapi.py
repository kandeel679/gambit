import os
import time
from google import genai
from google.genai import types

# 1. Setup the Client
# Ensure you have set your API key in your terminal: export GEMINI_API_KEY='your_key'
client = genai.Client(api_key="AIzaSyDM1IjtKgewJO4aCzta9bwx2GMZlGsukKc")
def generate_with_retry(prompt, model_id="gemini-2.5-flash-lite"):
    """
    Generates content with built-in retry logic for the Free Tier.
    Configured for 2026 SDK standards.
    """
    
    # Configure automatic SDK retries for transient errors (500s, 503s)
    # Note: 429 (Rate Limit) often requires manual pacing on the Free Tier
    http_options = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=5,
            initial_delay=2.0, # Start with 2s delay
            max_delay=60.0,    # Max wait of 1 minute
            http_status_codes=[429, 500, 503] 
        )
    )

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=http_options,
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        return f"Request failed after retries: {str(e)}"

# Example Usage
my_prompt = "Explain the benefit of using a Flash model for a lightweight API project."
result = generate_with_retry(my_prompt)
print(result)