import streamlit as st
import requests
import os

# =========================
# CONFIG
# =========================
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ResumeIQ",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(css_path, "r") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    st.markdown("""
    <style>
        [data-testid="stIconMaterial"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)
load_css()

# =========================
# SESSION STATE (PAGE ROUTING)
# =========================
if "page" not in st.session_state:
    st.session_state.page = "dashboard"


# =========================
# SIDEBAR NAVIGATION
# =========================
with st.sidebar:
    st.title("ResumeIQ")
    st.divider()

    if st.button("Dashboard"):
        st.session_state.page = "dashboard"

    if st.button("Upload Resume"):
        st.session_state.page = "upload"

    if st.button("Search"):
        st.session_state.page = "search"


# =========================
# DASHBOARD PAGE
# =========================
if st.session_state.page == "dashboard":

    st.markdown("""
    <div style="padding:70px 20px; text-align:center;">
        <h1 style="font-size:64px;">ResumeIQ</h1>
        <p style="font-size:22px; color:gray;">
            AI-Powered Resume Intelligence System
        </p>
        <p style="font-size:18px; max-width:700px; margin:auto;">
            Upload resumes, extract insights, and search candidates using AI-powered semantic search.
        </p>
    </div>
    """, unsafe_allow_html=True)


# =========================
# UPLOAD PAGE (CONNECTS TO BACKEND)
# =========================
elif st.session_state.page == "upload":

    st.title("Upload Resume")

    uploaded_file = st.file_uploader("Choose PDF Resume", type=["pdf"])

    if uploaded_file:

        st.success(f"Selected file: {uploaded_file.name}")

        if st.button("Upload to Server"):

            try:
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf"
                    )
                }

                response = requests.post(
                    f"{BACKEND_URL}/upload_pdf",
                    files=files
                )

                if response.status_code == 200:
                    st.success("Resume uploaded successfully 🚀")
                    st.json(response.json())
                else:
                    st.error(f"Upload failed: {response.text}")

            except Exception as e:
                st.error(f"Backend connection error: {e}")


# =========================
# SEARCH PAGE (CONNECTS TO BACKEND)
# =========================
elif st.session_state.page == "search":

    st.title("Search Candidates")

    query = st.text_input("Enter search query")

    if st.button("Search") and query:

        try:
            response = requests.get(
                f"{BACKEND_URL}/search",
                params={"query": query}
            )

            if response.status_code == 200:

                data = response.json()

                query_type = data.get("type")

                # ==================================================
                # PERSON QUERY UI
                # ==================================================
                if query_type == "person_query":

                    st.subheader("Answer")

                    answer = data.get("answer", "")

                    if isinstance(answer, list):
                        for a in answer:
                            st.markdown(f"- {a}")
                    else:
                        st.write(answer)

                # ==================================================
                # SKILL QUERY UI
                # ==================================================
                elif query_type == "skill_query":

                    st.subheader("Matched Candidates")

                    for c in data.get("matched_candidates", []):
                        st.markdown(f"- {c}")
                        
                # -------------------------
                # FILES
                # -------------------------
                st.subheader("Matched Files")

                for f in data.get("matched_files", []):
                    st.markdown(f"- 📄 {f}")

            else:
                st.error(f"Error: {response.text}")

        except Exception as e:
            st.error(f"Connection error: {e}")