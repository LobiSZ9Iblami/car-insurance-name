import re
from huggingface_hub import InferenceClient
import asyncio

from bot_config import HUGGIN_API_KEY


# model = "mistralai/Mistral-7B-Instruct-v0.2"
# client = InferenceClient(token=HUGGIN_API_KEY, model=model, timeout=60)

# def ask_mistral(prompt: str) -> str:
#
#     try:
#         response = client.text_generation(
#             prompt=prompt,
#             max_new_tokens=500,
#             temperature=0.7
#         )
#         return response.generated_text
#     except Exception as e:
#         return f"Error: {str(e)}"


model = "CohereLabs/c4ai-command-a-03-2025"
client = InferenceClient(
    provider="cohere",
    api_key=HUGGIN_API_KEY,
)

escape_chars = r'_*[\]()~`>#+-=|{}.!'
async def ask_cohere_labs(prompt: str) -> str:
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        raw_response = response.choices[0].message.content

        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', raw_response)

    except Exception as e:
        return f"❌ Error: {str(e)}"
