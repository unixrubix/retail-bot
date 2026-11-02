import os
import re
import requests
from flask import Flask, render_template, request

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
REQUEST_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

# Lightweight, explainable "decision model": customer segment influences the
# recommended copy angle and vocabulary. Users can still choose the tone.
SEGMENT_GUIDANCE = {
    "Everyday shoppers": "Emphasize practical benefits, ease of use, and clear value. Avoid hype.",
    "Budget-conscious shoppers": "Emphasize useful value, durability when supported, and cost-conscious benefits. Do not invent prices or savings.",
    "Premium buyers": "Use refined language and focus on design, experience, and craftsmanship only when supported by the supplied facts.",
    "Gift buyers": "Emphasize why the product could make a thoughtful, convenient gift. Do not assume the recipient or occasion.",
    "Tech enthusiasts": "Highlight relevant features and practical use cases. Explain technical terms plainly and do not invent specifications.",
    "Eco-conscious shoppers": "Mention sustainability only if the input explicitly provides evidence. Never infer that a product is eco-friendly from keywords alone."
}

TONE_GUIDANCE = {
    "Friendly": "Warm, approachable, and conversational.",
    "Professional": "Clear, credible, and polished.",
    "Playful": "Energetic and lightly witty, without being childish.",
    "Luxury": "Elegant, restrained, and sensory, without unsupported luxury claims.",
    "Minimalist": "Concise, direct, and benefit-led."
}


def clean_list(raw):
    """Split comma-separated keywords, trim whitespace, and remove duplicates."""
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return list(dict.fromkeys(values))[:20]


def build_prompt(product_name, keywords, tone, segment):
    keyword_text = ", ".join(keywords) if keywords else "No keywords supplied"
    return f"""
You are an experienced retail e-commerce copywriter.

Write a compelling, customer-focused product description using only the
information supplied below.

Product name: {product_name}
Keywords / product facts supplied by the user: {keyword_text}
Writing tone: {tone} — {TONE_GUIDANCE[tone]}
Target customer segment: {segment}
Customer-segment guidance: {SEGMENT_GUIDANCE[segment]}

Requirements:
- Write one polished description of about 90–140 words.
- Start with a useful hook, then explain customer benefits naturally.
- Work relevant keywords into the copy without keyword stuffing.
- Do not make up materials, dimensions, compatibility, certifications,
  performance claims, health benefits, environmental claims, warranties,
  prices, discounts, or other facts not provided.
- If the keywords are vague, keep the claims appropriately general.
- Avoid clichés such as "revolutionary", "game-changing", and "must-have".
- Return only the product description, with no heading or commentary.
""".strip()


def generate_description(product_name, keywords, tone, segment):
    prompt = build_prompt(product_name, keywords, tone, segment)
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "top_p": 0.9}
        },
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    description = (data.get("response") or "").strip()
    if not description:
        raise RuntimeError("The model returned an empty response.")
    return description


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    form = {
        "product_name": "",
        "keywords": "",
        "tone": "Friendly",
        "segment": "Everyday shoppers"
    }

    if request.method == "POST":
        form.update({
            "product_name": request.form.get("product_name", "").strip(),
            "keywords": request.form.get("keywords", "").strip(),
            "tone": request.form.get("tone", "Friendly"),
            "segment": request.form.get("segment", "Everyday shoppers")
        })

        if not form["product_name"]:
            error = "Please enter a product name."
        elif len(form["product_name"]) > 120:
            error = "Product name must be 120 characters or fewer."
        elif len(form["keywords"]) > 1000:
            error = "Please keep the keyword list under 1,000 characters."
        elif form["tone"] not in TONE_GUIDANCE:
            error = "Please choose a valid writing tone."
        elif form["segment"] not in SEGMENT_GUIDANCE:
            error = "Please choose a valid customer segment."
        else:
            try:
                keywords = clean_list(form["keywords"])
                result = generate_description(
                    form["product_name"], keywords, form["tone"], form["segment"]
                )
            except requests.exceptions.ConnectionError:
                error = (
                    "Could not connect to Ollama. Make sure the Ollama service "
                    "is running and the model has finished downloading."
                )
            except requests.exceptions.Timeout:
                error = "The model took too long to respond. Try again or use a smaller model."
            except requests.exceptions.HTTPError as exc:
                detail = exc.response.text[:300] if exc.response is not None else str(exc)
                error = f"Ollama returned an error: {detail}"
            except Exception as exc:
                error = f"Could not generate a description: {exc}"

    return render_template(
        "index.html",
        result=result,
        error=error,
        form=form,
        tones=list(TONE_GUIDANCE.keys()),
        segments=list(SEGMENT_GUIDANCE.keys()),
        model=OLLAMA_MODEL
    )


@app.get("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
