import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from openai import OpenAI

# ----------------------------
# Load secrets / API key
# ----------------------------
load_dotenv()
OPENAI_KEY = None
try:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_KEY:
    st.warning("⚠️ OPENAI_API_KEY not found in st.secrets or environment variables.")
client = OpenAI(api_key=OPENAI_KEY)

# ----------------------------
# Streamlit page setup
# ----------------------------
st.set_page_config(page_title="ClauseMatrix: Browser-based Legal Analyzer")
st.title("📄 ClauseMatrix: Browser-based Legal Analyzer")

# ----------------------------
# File uploader & mode
# ----------------------------
uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

mode = st.radio(
    "What would you like to do?",
    ["🔍 Analyze a Single Document", "📊 Analyze and Compare Multiple Documents"]
)

# ----------------------------
# Helpers
# ----------------------------
def extract_text_from_pdf(uploaded_file):
    """
    Read text from a single PDF (no pre-reads; keep UploadedFile intact).
    """
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def analyze_text_full(text: str, instruction: str) -> str:
    """
    Single-pass analysis using OpenAI v1 Chat Completions API (no chunking).
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise legal document analyzer."},
            {"role": "user", "content": f"{instruction}\n\n{text}"}
        ],
        temperature=0.2
    )
    return resp.choices[0].message.content.strip()

def process_single_document(uploaded_file) -> str:
    """
    Extract text and run a single analysis call (no chunking).
    """
    text = extract_text_from_pdf(uploaded_file)
    if not text:
        return "⚠️ The uploaded PDF appears to be empty or unreadable."
    with st.spinner("Analyzing document..."):
        analysis_output = analyze_text_full(
            text,
            "Analyze this legal PDF and produce a concise, structured result with these sections:\n"
            "1. Parties\n2. Effective Date\n3. Term\n4. Confidential Information\n"
            "5. Obligations\n6. Jurisdiction\n7. Risk Flags"
        )
    return analysis_output

def process_multiple_documents(files) -> dict:
    """
    For multiple PDFs, analyze each in a single pass (no chunking) and return a dict: {filename: analysis}.
    """
    results = {}
    for f in files:
        with st.spinner(f"Analyzing {f.name}..."):
            text = extract_text_from_pdf(f)
            if not text:
                results[f.name] = "⚠️ Empty or unreadable PDF."
                continue
            analysis_output = analyze_text_full(
                text,
                "Analyze this legal PDF and produce a concise, structured result with these sections:\n"
                "1. Parties\n2. Effective Date\n3. Term\n4. Confidential Information\n"
                "5. Obligations\n6. Jurisdiction\n7. Risk Flags"
            )
            results[f.name] = analysis_output
    return results

# ----------------------------
# Main logic
# ----------------------------
if uploaded_files:
    if mode == "🔍 Analyze a Single Document":
        if len(uploaded_files) != 1:
            st.warning("Please upload exactly one PDF for single-document analysis.")
        else:
            uploaded_file = uploaded_files[0]
            if uploaded_file.type != "application/pdf":
                st.error("Please upload a PDF file.")
            else:
                try:
                    analysis_output = process_single_document(uploaded_file)
                    st.subheader("Analysis Result")
                    st.write(analysis_output)
                except Exception as e:
                    st.error(f"❌ Error during analysis:\n\n{e}")

    elif mode == "📊 Analyze and Compare Multiple Documents":
        if len(uploaded_files) < 2:
            st.warning("Please upload at least two PDFs for comparison.")
        else:
            try:
                analysis_results = process_multiple_documents(uploaded_files)
                st.subheader("Comparison Results")

                # ================================
                # Section-based comparison table (side-by-side)
                # rows = sections, columns = file names
                # ================================
                sections = [
                    "Parties",
                    "Effective Date",
                    "Term",
                    "Confidential Information",
                    "Obligations",
                    "Jurisdiction",
                    "Risk Flags",
                ]

                def extract_section(summary_text: str, section_name: str) -> str:
                    """
                    Extract a section block following the pattern:
                    <Section Name>:
                      <content...>
                    Stops at the next section heading or end of text.
                    """
                    pattern = rf"{section_name}\s*:([\s\S]*?)(?=\n[A-Z][A-Za-z ]+:\s*|$)"
                    m = re.search(pattern, summary_text, flags=re.IGNORECASE)
                    return m.group(1).strip() if m else "Not specified"

                # Build a matrix: rows = sections, columns = file names
                matrix = {section: {} for section in sections}
                file_names = list(analysis_results.keys())

                for fname, analysis_text in analysis_results.items():
                    for section in sections:
                        matrix[section][fname] = extract_section(analysis_text, section)

                df_matrix = pd.DataFrame(matrix).T  # rows=sections, cols=file names (side-by-side)

                # If extraction failed badly, fallback to simple view
                if df_matrix.empty or df_matrix.isna().all(axis=None):
                    df_simple = pd.DataFrame.from_dict(
                        analysis_results, orient="index", columns=["Analysis"]
                    )
                    st.dataframe(df_simple)
                else:
                    st.dataframe(df_matrix)

                # Raw analysis expanders per file (readable view)
                st.subheader("🗂 Per-file Analysis")
                for fname, analysis in analysis_results.items():
                    with st.expander(f"📄 {fname}", expanded=False):
                        st.write(analysis)

            except Exception as e:
                st.error(f"❌ Error during comparison analysis:\n\n{e}")
else:
    st.info("Upload one or more PDFs to begin.")
