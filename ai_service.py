import os, json, re
from groq import Groq

def ai_available():
    return bool(os.getenv("GROQ_API_KEY"))

def _client():
    key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

def _json_from_text(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.I|re.M).strip()
    return json.loads(text)

def generate_case(category, difficulty):
    client = _client()
    if not client: return None
    prompt = f"""Create one original, fair-play fictional detective game case.
Category: {category}. Difficulty: {difficulty}.
Return ONLY valid JSON with keys: title, synopsis, location, suspects, evidence, puzzle, hint,
solution_keywords, solution_explanation. suspects and evidence should be readable numbered/newline text.
solution_keywords must contain 2-4 acceptable short answers separated by |.
Do not use real people or real unresolved crimes. Include enough clues for a solvable answer."""
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role":"system","content":"You design fair, internally consistent fictional mystery game content."},
                      {"role":"user","content":prompt}],
            temperature=0.8, max_tokens=1200)
        return _json_from_text(response.choices[0].message.content)
    except Exception:
        return None

def detective_reply(case, question):
    client = _client()
    context = f"""Case: {case.title}
Story: {case.synopsis}
Suspects: {case.suspects}
Evidence: {case.evidence}
Puzzle: {case.puzzle}
Do not reveal the solution or solution keywords. Give a concise helpful investigative response based only on known case facts.
If the player asks for the answer, offer a subtle clue instead."""
    if client:
        try:
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[{"role":"system","content":"You are Detective AI, a careful in-game assistant. Do not invent evidence or reveal the answer directly."},
                          {"role":"user","content":context+"\nPlayer question: "+question}],
                temperature=0.4, max_tokens=350)
            return response.choices[0].message.content.strip()
        except Exception:
            pass
    return ("Demo Detective: Compare the timeline with the physical evidence. "
            "Ask yourself which clue is independently verifiable, and avoid accusing someone based on motive alone.")
