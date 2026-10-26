"""AI Resume ATS Checker - Streamlit app powered by Gemini Flash."""

import io
import json
import os
import re

import streamlit as st
from docx import Document
from google import genai
from google.genai import types
from pypdf import PdfReader

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-3.8-flash"  # change to any Gemini Flash model id
MAX_RESUME_CHARS = 20000
MAX_FILE_MB = 5

st.set_page_config(page_title="AI Resume ATS Checker", page_icon="📄", layout="wide")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def get_api_key(user_key: str = "") -> str:
    """Priority: key typed in sidebar > Streamlit secrets > environment variable."""
    if user_key.strip():
        return user_key.strip()
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def extract_text(uploaded_file) -> str:
    """Extract plain text from an uploaded PDF, DOCX or TXT file."""
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception:
                unlocked = 0
            if not unlocked:
                raise ValueError("This PDF is password protected. Please upload an unlocked copy.")
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages).strip()

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts).strip()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore").strip()

    raise ValueError("Unsupported file type. Please upload a PDF, DOCX or TXT file.")


def build_prompt(resume_text: str, job_description: str) -> str:
    jd_block = (
        f"JOB DESCRIPTION:\n{job_description.strip()}\n\n"
        "Score the resume against this job description. Keywords must come from it."
        if job_description.strip()
        else "No job description was provided. Evaluate the resume for general ATS "
        "compatibility and for common expectations of the role it appears to target."
    )
    return f"""You are an expert ATS (Applicant Tracking System) analyst and professional resume reviewer.

Analyse the resume below and return ONLY a JSON object (no markdown, no commentary) with exactly this shape:

{{
  "ats_score": <integer 0-100, overall ATS score>,
  "summary": "<2-3 sentence overall assessment>",
  "section_scores": {{
    "formatting": <0-100>,
    "keywords": <0-100>,
    "experience_impact": <0-100>,
    "skills": <0-100>,
    "education": <0-100>,
    "readability": <0-100>
  }},
  "strengths": ["<short point>", ...],
  "weaknesses": ["<short point>", ...],
  "matched_keywords": ["<keyword>", ...],
  "missing_keywords": ["<keyword>", ...],
  "improvements": [
    {{"priority": "High|Medium|Low", "area": "<section or topic>", "issue": "<what is wrong>", "suggestion": "<specific fix>"}}
  ],
  "rewrite_examples": [
    {{"original": "<weak line taken from the resume>", "improved": "<stronger rewrite using action verbs and metrics>"}}
  ]
}}

Rules:
- Be honest and strict; do not inflate the score.
- Give 5-8 improvements, ordered by priority.
- Give 2-4 rewrite examples using real lines from the resume. Never invent numbers as facts; use placeholders like [X%] where metrics are unknown.
- Return valid JSON only.

{jd_block}

RESUME:
\"\"\"
{resume_text[:MAX_RESUME_CHARS]}
\"\"\"
"""


def parse_json_response(text: str) -> dict:
    """Parse model output into a dict, tolerating code fences or stray text."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("The AI returned an unreadable response. Please try again.")


def clamp_score(value) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def analyse_resume(api_key: str, model: str, resume_text: str, jd: str) -> dict:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=build_prompt(resume_text, jd),
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    result = parse_json_response(response.text)
    result["ats_score"] = clamp_score(result.get("ats_score"))
    sections = result.get("section_scores") or {}
    result["section_scores"] = {k: clamp_score(v) for k, v in sections.items()}
    return result


def score_label(score: int) -> str:
    if score >= 80:
        return "🟢 Excellent"
    if score >= 60:
        return "🟡 Good, but improvable"
    if score >= 40:
        return "🟠 Needs work"
    return "🔴 Poor"


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def render_results(result: dict) -> None:
    score = result["ats_score"]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("ATS Score", f"{score} / 100")
        st.progress(score / 100)
        st.caption(score_label(score))
    with col2:
        st.subheader("Summary")
        st.write(result.get("summary", ""))

    sections = result.get("section_scores", {})
    if sections:
        st.subheader("Score breakdown")
        cols = st.columns(len(sections))
        for col, (name, val) in zip(cols, sections.items()):
            col.metric(name.replace("_", " ").title(), val)
            col.progress(val / 100)

    left, right = st.columns(2)
    with left:
        st.subheader("✅ Strengths")
        for item in result.get("strengths", []):
            st.markdown(f"- {item}")
    with right:
        st.subheader("⚠️ Weaknesses")
        for item in result.get("weaknesses", []):
            st.markdown(f"- {item}")

    kl, kr = st.columns(2)
    with kl:
        st.subheader("Matched keywords")
        matched = result.get("matched_keywords", [])
        st.write(", ".join(f"`{k}`" for k in matched) if matched else "None found.")
    with kr:
        st.subheader("Missing keywords")
        missing = result.get("missing_keywords", [])
        st.write(", ".join(f"`{k}`" for k in missing) if missing else "None found.")

    st.subheader("🛠 Recommended improvements")
    icons = {"high": "🔴", "medium": "🟠", "low": "🟢"}
    for imp in result.get("improvements", []):
        priority = str(imp.get("priority", "")).strip()
        icon = icons.get(priority.lower(), "🔹")
        with st.expander(f"{icon} {priority} - {imp.get('area', 'General')}"):
            st.markdown(f"**Issue:** {imp.get('issue', '')}")
            st.markdown(f"**Fix:** {imp.get('suggestion', '')}")

    examples = result.get("rewrite_examples", [])
    if examples:
        st.subheader("✍️ Rewrite examples")
        for ex in examples:
            st.markdown(f"**Before:** {ex.get('original', '')}")
            st.markdown(f"**After:** {ex.get('improved', '')}")
            st.divider()

    st.download_button(
        "Download report (JSON)",
        data=json.dumps(result, indent=2),
        file_name="ats_report.json",
        mime="application/json",
    )


def main() -> None:
    st.title("📄 AI Resume ATS Checker")
    st.write("Upload your resume to get an ATS score and specific suggestions to improve it.")

    with st.sidebar:
        st.header("Settings")
        user_key = st.text_input(
            "Gemini API key",
            type="password",
            help="Leave empty if the key is set in Streamlit secrets or the GEMINI_API_KEY environment variable.",
        )
        model = st.text_input("Gemini model", value=DEFAULT_MODEL)
        st.markdown("[Get a free API key](https://aistudio.google.com/apikey)")
        st.caption("Your resume is sent to Google's Gemini API for analysis.")

    uploaded = st.file_uploader("Upload resume", type=["pdf", "docx", "txt"])
    jd = st.text_area(
        "Job description (optional, recommended)",
        height=180,
        placeholder="Paste the job description here for a targeted score and keyword match...",
    )

    if st.button("Analyse resume", type="primary", disabled=uploaded is None):
        api_key = get_api_key(user_key)
        if not api_key:
            st.error("Please enter a Gemini API key in the sidebar.")
            return
        if uploaded.size > MAX_FILE_MB * 1024 * 1024:
            st.error(f"File is too large. Maximum size is {MAX_FILE_MB} MB.")
            return

        try:
            with st.spinner("Reading your resume..."):
                text = extract_text(uploaded)
        except Exception as e:
            st.error(f"Could not read the file: {e}")
            return

        if len(text) < 100:
            st.error(
                "Very little text could be extracted. The file may be a scanned image, "
                "which an ATS would not be able to read either. Use a text-based PDF or DOCX."
            )
            return

        try:
            with st.spinner("Analysing with Gemini..."):
                result = analyse_resume(api_key, model.strip() or DEFAULT_MODEL, text, jd)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return

        st.session_state["result"] = result

    if "result" in st.session_state:
        render_results(st.session_state["result"])


if __name__ == "__main__":
    main()
