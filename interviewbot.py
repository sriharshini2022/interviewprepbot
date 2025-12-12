import streamlit as st
import random
from datetime import datetime
import google.generativeai as genai
import json

GOOGLE_API_KEY = "abcd"  # <-- Replace with your Google API key
genai.configure(api_key=GOOGLE_API_KEY)

QUESTION_TYPES = ["coding", "technical", "behavioral/aptitude"]

# Prompt templates
CODING_PROMPTS = {
    "Python": "Generate a unique Python coding interview question (medium complexity, 1-3 years experience, output only the question).",
    "JavaScript": "Generate a unique JavaScript coding interview question (medium complexity, 1-3 years experience, output only the question).",
    "Java": "Generate a unique Java coding interview question (medium complexity, 1-3 years experience, output only the question).",
    "C++": "Generate a unique C++ coding interview question (medium complexity, 1-3 years experience, output only the question).",
    "Data Science": "Generate a unique data science coding interview question (e.g., pandas, numpy, scikit-learn; 1-3 years experience, output only the question).",
    "React": "Generate a unique React coding interview question (e.g., write a component, manage state, hooks; 1-3 years experience, output only the question).",
    "SQL": "Generate a unique SQL coding question (write a query or function, medium complexity, 1-3 years experience, output only the question).",
    "DevOps": "Generate a unique DevOps coding question (e.g., scripting, CI/CD, Docker; 1-3 years experience, output only the question)."
}
# These will always be real-world, placement-style (not stack-specific) for non-coding
REALTIME_PROMPTS = {
    "technical": "Generate a real-world technical interview question commonly asked in campus placements for freshers or candidates with 1-3 years experience. Avoid stack-specific or coding questions. Output only the question.",
    "behavioral/aptitude": "Generate a behavioral or aptitude interview question suitable for campus placements or job interviews for freshers or candidates with 1-3 years experience. Output only the question."
}

def generate_new_question(role: str, qtype: str) -> str:
    if qtype == "coding":
        prompt = CODING_PROMPTS.get(role, f"Generate a unique {role} coding interview question for 1-3 years experience. Output only the question.")
    else:
        prompt = REALTIME_PROMPTS[qtype]
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[AI error: {e}]"

def ai_feedback(question: str, answer: str) -> dict:
    prompt = f"""
    You are an interview coach. Evaluate the user's answer to the question below.
    - Question: {question}
    - Answer: {answer}
    Give:
    1. Score (0-100)
    2. Short feedback (max 3 sentences)
    3. What could be improved
    Respond in JSON like:
    {{"score": 85, "feedback": "Good answer...", "improvement": "Mention optimization."}}
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            json_str = text[start:end]
            return json.loads(json_str)
        except Exception:
            return {"score": 50, "feedback": "AI response parsing error.", "improvement": text.strip()}
    except Exception as e:
        return {"score": 50, "feedback": f"AI error: {e}", "improvement": "Try again."}

def get_progress(session):
    if "progress" not in session:
        session["progress"] = []
    return session["progress"]

def add_progress(session, qtype, score):
    session["progress"].append({"type": qtype, "score": score, "time": str(datetime.now())})

def average_score(progress, qtype=None):
    scores = [p["score"] for p in progress if (qtype is None or p["type"] == qtype)]
    return round(sum(scores)/len(scores), 2) if scores else 0

# == APP ==
st.set_page_config("Interview Preparation Bot ", "💬")
st.title("💬 Interview Preparation Bot ")
st.write("Practice interviews for coding (stack specific), and technical or behavioral/aptitude rounds (real-world placement style). Get instant AI feedback and track your progress!")

roles = list(CODING_PROMPTS.keys())
role = st.selectbox("Select your job role/tech stack:", roles)
qtype = st.selectbox("Select question type:", QUESTION_TYPES)

if (
    "current_qtype" not in st.session_state or
    st.session_state.get("last_role") != role or
    st.session_state.get("last_qtype") != qtype
):
    st.session_state.current_qtype = qtype
    st.session_state.current_question = generate_new_question(role, qtype)
    st.session_state.next_question = False
    st.session_state.last_role = role
    st.session_state.last_qtype = qtype
elif "current_question" not in st.session_state or st.session_state.get("next_question", False):
    st.session_state.current_question = generate_new_question(role, st.session_state.current_qtype)
    st.session_state.next_question = False

# Main Q/A loop
if st.session_state.current_question:
    st.markdown(f"**Question ({st.session_state.current_qtype.title()}):** {st.session_state.current_question}")
    answer = st.text_area("Your answer:", key="answer")
    if st.button("Submit Answer"):
        user_answer = answer.strip()
        if not user_answer:
            st.warning("Please provide an answer.")
        else:
            with st.spinner("Analyzing your answer..."):
                feedback = ai_feedback(st.session_state.current_question, user_answer)
            st.success(f"Score: {feedback['score']} / 100")
            st.info(f"💡 Feedback: {feedback['feedback']}")
            st.warning(f"🔧 Improvement: {feedback['improvement']}")
            add_progress(st.session_state, st.session_state.current_qtype, feedback['score'])
            st.session_state.next_question = True
            # Use st.rerun() for Streamlit >=1.32, fallback to .experimental_rerun() otherwise
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()
else:
    st.info("No more questions available for this role. Try another role or reset.")

# Progress Dashboard
st.markdown("---")
st.header("📈 Progress Tracker")
progress = get_progress(st.session_state)
if progress:
    st.write("Your last 5 answers:")
    for p in progress[-5:][::-1]:
        st.write(f"- **{p['type'].title()}** | Score: {p['score']} | {p['time']}")
    st.write(f"**Average Score:** {average_score(progress)}")
    for qt in QUESTION_TYPES:
        st.write(f"{qt.title()} Avg: {average_score(progress, qt)}")
    st.progress(min(average_score(progress)/100, 1.0))
else:
    st.write("No progress yet. Start answering questions!")

if st.button("🔄 Reset Progress"):
    for k in ["current_qtype", "current_question", "progress", "next_question", "last_role", "last_qtype"]:
        if k in st.session_state:
            del st.session_state[k]
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


st.caption("Made For Placement Preparation")
