import json
from agent import load_sop, build_system_prompt, _init_genai, _clients, _api_keys, _current_key_idx, _use_modern, _model_name
from google.genai import types

_init_genai()

sop = load_sop()
prompt = build_system_prompt(sop)

client = _clients[_current_key_idx]

contents = [
    {"role": "user", "parts": ["Hi"]},
    {"role": "model", "parts": ["Hello, how can I help?"]},
    {"role": "user", "parts": ["What are your hours?"]}
]

config = types.GenerateContentConfig(
    system_instruction=prompt,
    temperature=0.3
)

response = client.models.generate_content(
    model=_model_name,
    contents=contents,
    config=config
)
print(response.text)
