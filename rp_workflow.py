import os
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

# ── 5. The prompt ───────────────────────────────────────────────────────────
classify_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You read return comments for Dhaga & Co., an Indian online fashion brand. "
     "Customers often write in Hinglish (Hindi in English letters), with typos, "
     "short forms and the odd emoji. Pick the ONE main reason the item was returned.\n\n"
     "Reasons:\n"
     "- too_small: the right product, but it fits small or tight. e.g. 'size chota hai', 'bahut tight h'\n"
     "- too_large: the right product, but it fits big or loose. e.g. 'bahut loose hai', 'size bada hai'\n"
     "- colour_mismatch: the colour or shade differs from the photo. e.g. 'rang alag hai', 'photo me maroon dikha'\n"
     "- quality: poor fabric or making: thin cloth, bad stitching, fading or shrinking after wash. "
     "e.g. 'kapda patla hai', 'ek wash me rang chala gaya'\n"
     "- damaged: arrived broken or spoiled: hole, stain, torn, broken zip or button. "
     "e.g. 'phata hua aaya', 'daag hai'\n"
     "- wrong_item: a different product, design or colour was sent than ordered. "
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
     "6. Give a lower confidence when the comment is short, vague or could fit two reasons."),
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


def classify_comment(text: str) -> dict:
    """Ask the cheap model for the reason behind one return comment.

    Args:
        text: the customer's comment, exactly as written. Nothing else is sent.

    Returns:
        A dict with issue_type, confidence, evidence_phrase, tokens and attempts.
        If the model answers in the wrong shape twice, issue_type is "failed"
        and "error" says why.
    """
    tokens = {"input_tokens": 0, "output_tokens": 0}
    last_error = None

    for attempt in (1, 2):
        out = classify_chain.invoke({"comment": text})

        # Count tokens on every try, failed ones included: we pay for them too
        usage = out["raw"].usage_metadata or {}
        tokens["input_tokens"] += usage.get("input_tokens", 0)
        tokens["output_tokens"] += usage.get("output_tokens", 0)

        if out["parsed"] is not None:
            return {**out["parsed"].model_dump(), "tokens": tokens, "attempts": attempt}

        last_error = out["parsing_error"]

    return {
        "issue_type": "failed",
        "confidence": None,
        "evidence_phrase": None,
        "error": str(last_error),
        "tokens": tokens,
        "attempts": 2,
    }
