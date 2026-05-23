import json
from agent import load_sop, build_system_prompt, call_gemini

sop = load_sop()
prompt = build_system_prompt(sop)
reply = call_gemini(prompt, [], "Hi, what are your hours?")
print(reply)
