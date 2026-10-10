import os
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Load settings (OpenRouter key, model name) from .env
load_dotenv()


# ── 1. OpenRouter setup ─────────────────────────────────────────────────────
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set.")

# ── 2. The reasons the model may choose ─────────────────────────────────────
# "failed" is not here on purpose: only our code sets it, never the model.
ISSUE_TYPES = [
    "too_small", "too_large", "colour_mismatch", "quality", "damaged",
    "wrong_item", "changed_mind", "delivery_late", "unclear",
]

# Dropdown label -> our reason name (no AI needed for these)
DROPDOWN_TO_ISSUE = {
    "Size too small": "too_small",
    "Size too large": "too_large",
    "Colour different from image": "colour_mismatch",
    "Quality not as expected": "quality",
    "Product damaged": "damaged",
    "Wrong item received": "wrong_item",
}


# ── 3. The answer shape ─────────────────────────────────────────────────────
class ReturnReason(BaseModel):
    """What the model must give back for one return comment."""

    issue_type: Literal[
        "too_small", "too_large", "colour_mismatch", "quality", "damaged",
        "wrong_item", "changed_mind", "delivery_late", "unclear",
    ] = Field(description="The single main reason the customer returned the item.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How sure you are, from 0.0 to 1.0.",
    )
    evidence_phrase: str = Field(
        description='The exact words from the comment that show the reason. '
                    'Copy them word for word. Use "" if there are none.',
    )


# ── 4. Model connection ─────────────────────────────────────────────────────
CHEAP_MODEL = os.getenv("CHEAP_MODEL")
if not CHEAP_MODEL:
    raise RuntimeError("CHEAP_MODEL is not set.")

cheap_llm = ChatOpenAI(
    model_name=CHEAP_MODEL,
    openai_api_key=API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.0,
    max_retries=1,
    request_timeout=10,
    max_tokens=500,
)

STRONG_MODEL = os.getenv("STRONG_MODEL")
if not STRONG_MODEL:
    raise RuntimeError("STRONG_MODEL is not set.")

strong_llm = ChatOpenAI(
    model_name=STRONG_MODEL,
    openai_api_key=API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.0,
    max_retries=1,
    request_timeout=20,
    max_tokens=500,
)

# ── 5. The prompt ───────────────────────────────────────────────────────────
classify_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You read return comments for Dhaga & Co., an Indian online fashion brand. "
     "Customers often write in Hinglish (Hindi in English letters), with typos, "
     "short forms and the odd emoji. Pick the ONE main reason the item was returned.\n\n"
     "Reasons:\n"
     "- too_small: the right product, but it fits small or tight. e.g. 'size chota hai', 'bahut tight h'\n"
     "- too_large: the right product, but it fits big or loose. e.g. 'bahut loose hai', 'size bada hai'\n"
     "- colour_mismatch: the colour or shade differs from the photo or from what was ordered. e.g. 'rang alag hai', 'photo me maroon dikha'\n"
     "- quality: poor fabric or making: thin cloth, bad stitching, fading or shrinking after wash. "
     "e.g. 'kapda patla hai', 'ek wash me rang chala gaya'\n"
     "- damaged: arrived broken or spoiled: hole, stain, torn, broken zip or button. "
     "e.g. 'phata hua aaya', 'daag hai'\n"
     "- wrong_item: a different product or design was sent than ordered. "
     "e.g. 'galat product aaya', 'kurti mangayi thi top aaya'\n"
     "- changed_mind: nothing wrong with the item; the customer no longer wants it. "
     "e.g. 'pasand nahi aaya', 'ab zarurat nahi'\n"
     "- delivery_late: it arrived too late to be useful. e.g. 'function nikal gaya', 'bahut late aaya'\n"
     "- unclear: no real reason is given. e.g. 'not good', 'bekar', 'ok', '...'\n\n"
     "Rules:\n"
     "1. Fabric problems are quality; problems that were there on arrival are damaged.\n"
     "2. If the right product came in a size that does not fit, it is too_small or too_large, not wrong_item.\n"
     "3. 'pasand nahi aaya' is changed_mind. Only use unclear when no reason is stated at all.\n"
     "4. If two reasons are mentioned, pick the main one, usually the first.\n"
     "5. evidence_phrase must be copied word for word from the comment. Use an empty string for unclear.\n"
     "6. Give a lower confidence when the comment is short, vague or could fit two reasons.\n"
     "7. A colour different from what was ordered or shown is colour_mismatch; "
     "wrong_item is only for a different product or design."),
    ("human", "Return comment: {comment}"),
])

# ── 6. classify_comment(text) ───────────────────────────────────────────────
# The cheap model with the ReturnReason answer shape attached.
# include_raw=True gives back three things for every call:
#   out["parsed"]        -> a ReturnReason, or None if the answer was the wrong shape
#   out["parsing_error"] -> what went wrong, when parsed is None
#   out["raw"]           -> the model's raw reply; raw.usage_metadata has the token counts
classifier = cheap_llm.with_structured_output(
    ReturnReason, method="function_calling", include_raw=True
)
classify_chain = classify_prompt | classifier

strong_classifier = strong_llm.with_structured_output(
    ReturnReason, method="function_calling", include_raw=True
)
strong_chain = classify_prompt | strong_classifier


def classify_comment(text: str, model: str = "cheap") -> dict:
    """Ask a model (cheap by default) for the reason behind one return comment.

    Args:
        text: the customer's comment, exactly as written. Nothing else is sent.
        model: the model to use, either "cheap" or "strong".

    Returns:
        A dict with issue_type, confidence, evidence_phrase, model_name,
        tokens and attempts.
        If the model answers in the wrong shape twice, issue_type is "failed"
        and "error" says why.
    """
    chain = strong_chain if model == "strong" else classify_chain
    model_name = STRONG_MODEL if model == "strong" else CHEAP_MODEL

    tokens = {"input_tokens": 0, "output_tokens": 0}
    last_error = None

    for attempt in (1, 2):
        out = chain.invoke({"comment": text})

        # Count tokens on every try, failed ones included: we pay for them too
        usage = out["raw"].usage_metadata or {}
        tokens["input_tokens"] += usage.get("input_tokens", 0)
        tokens["output_tokens"] += usage.get("output_tokens", 0)

        if out["parsed"] is not None:
            return {**out["parsed"].model_dump(), "model_name": model_name,
                    "tokens": tokens, "attempts": attempt}

        last_error = out["parsing_error"]

    return {
        "issue_type": "failed",
        "confidence": None,
        "evidence_phrase": None,
        "model_name": model_name,
        "error": str(last_error),
        "tokens": tokens,
        "attempts": 2,
    }


# ── 7. Helpers (plain code, no AI) ──────────────────────────────────────────
def is_junk(text: str) -> bool:
    """True if the comment has nothing to read: under 3 characters or no letters."""
    t = (text or "").strip()
    return len(t) < 3 or not any(ch.isalpha() for ch in t)


def evidence_ok(text: str, phrase: str, min_similarity: float = 0.8) -> bool:
    """True if the quoted evidence appears in the comment, allowing for small typos.

    The model often fixes a customer's typo when quoting ("pasad" -> "pasand"),
    so an exact match is too strict. We accept the quote if some part of the
    comment is at least `min_similarity` alike (0.8 = 80%).

    Args:
        text: the customer's comment.
        phrase: the evidence the model quoted.
        min_similarity: how alike the quote and the comment must be, 0 to 1.
    """
    clean = lambda s: " ".join((s or "").lower().split())
    quote, comment = clean(phrase), clean(text)
    if not quote:
        return False
    if quote in comment:
        return True
    n = len(quote)
    best = max(SequenceMatcher(None, quote, comment[i:i + n]).ratio()
               for i in range(max(1, len(comment) - n + 1)))
    return best >= min_similarity


# ── 8. The full pipeline ────────────────────────────────────────────────────
def run_pipeline(rows: list[dict], threshold: float, workers: int = 10) -> list[dict]:
    """Give every return a reason: dropdown, junk check, cheap model, strong model.

    Args:
        rows: returns to classify, each with return_id, reason_dropdown, other_text.
        threshold: below this confidence, a real reason gets a second opinion.
        workers: how many comments go to a model at the same time.

    Returns:
        One result per return: return_id, issue_type, confidence,
        evidence_phrase, evidence_found, source, model_name, tokens.
    """
    no_tokens = {"input_tokens": 0, "output_tokens": 0}
    results = []   # returns that are finished
    to_ai = []     # returns that need a model to read them

    # Part 1: sort (plain code, free)
    for row in rows:
        if row["reason_dropdown"] != "Other":
            results.append({
                "return_id": row["return_id"],
                "issue_type": DROPDOWN_TO_ISSUE[row["reason_dropdown"]],
                "confidence": 1.0, "evidence_phrase": "",
                "evidence_found": None,
                "source": "dropdown", "model_name": None, "tokens": no_tokens,
            })
        elif is_junk(row["other_text"]):
            results.append({
                "return_id": row["return_id"],
                "issue_type": "unclear",
                "confidence": 1.0, "evidence_phrase": "",
                "evidence_found": None,
                "source": "gate", "model_name": None, "tokens": no_tokens,
            })
        else:
            to_ai.append(row)

    # Part 2: cheap model on the AI pile, in parallel
    def ask(row: dict, model: str) -> dict:
        """Classify one comment; a network error becomes 'failed' instead of stopping the run."""
        try:
            return classify_comment(row["other_text"], model)
        except Exception as e:
            return {"issue_type": "failed", "confidence": None, "evidence_phrase": None,
                    "model_name": None, "error": str(e), "tokens": no_tokens}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        answers = list(pool.map(lambda row: ask(row, "cheap"), to_ai))
    sources = ["cheap_model"] * len(answers)

    # Part 3a: second opinion for failed answers and shaky real reasons ("unclear" is trusted)
    needs_second = [
        i for i, a in enumerate(answers)
        if a["issue_type"] == "failed"
        or (a["issue_type"] != "unclear" and a["confidence"] < threshold)
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        second = list(pool.map(lambda i: ask(to_ai[i], "strong"), needs_second))
    for i, answer in zip(needs_second, second):
        answer["tokens_cheap"] = answers[i]["tokens"]   # keep what the first try cost
        answers[i] = answer
        sources[i] = "strong_model"

    # Part 3b: evidence check. Keep the reason; flag it if the quote isn't in the comment
    for row, a, source in zip(to_ai, answers, sources):
        has_reason = a["issue_type"] not in ("unclear", "failed")
        results.append({
            "return_id": row["return_id"],
            "issue_type": a["issue_type"],
            "confidence": a["confidence"],
            "evidence_phrase": a["evidence_phrase"],
            "evidence_found": evidence_ok(row["other_text"], a["evidence_phrase"]) if has_reason else None,
            "source": source,
            "model_name": a["model_name"],
            "tokens": a["tokens"],
            "tokens_cheap": a.get("tokens_cheap"),
        })
    return results
