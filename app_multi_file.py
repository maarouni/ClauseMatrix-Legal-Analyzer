import streamlit as st
import fitz  # PyMuPDF
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import io

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Password gate (same as single app)
app_password = os.getenv("STREAMLIT_PASSWORD")
entered_password = st.text_input("Enter access password", type="password")
if entered_password != app_password:
    st.stop()

st.title("AI-Powered Legal PDF Summarizer – Multi-file Comparison")
st.markdown("""
Upload multiple legal PDFs (NDA, lease, contract) to generate a side-by-side
summary for comparison.

**How to use:**
1. Upload 2–5 PDF files.
2. Click "Process Files".
3. Review the table and download it as Excel.
""")

# --- Helper: extract text ---
def extract_text_from_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()

    # Form fields if present
    if pdf.is_form_pdf:
        text += "\n\nForm Fields:\n"
        for page in pdf:
            for widget in page.widgets():
                field_name = widget.field_name if widget.field_name else "UnnamedField"
                field_value = widget.field_value if widget.field_value else ""
                text += f"{field_name}: {field_value}\n"
    return text

# Multi-file uploader
uploaded_files = st.file_uploader(
    "Upload multiple PDFs", type="pdf", accept_multiple_files=True
)

if uploaded_files and st.button("Process Files"):
    st.info("Processing all files...")

    summaries = {}
    # Summarize each file
    for file in uploaded_files:
        text = extract_text_from_pdf(file)

        prompt = f"""
        Summarize the following legal document with detailed sections.
        If any info is missing, write "Not specified".

        Sections to include:
        1. Parties
        2. Effective Date (start, end, renewal terms)
        3. Term (duration)
        4. Confidential Information
        5. Obligations
        6. Jurisdiction
        7. Risk Flags

        Document text and any Form Fields:
        {text[:8000]}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        summaries[file.name] = response.choices[0].message.content

    # --- Build comparison table ---
    # Each summary is split by lines and stored in DataFrame
    rows = ["Parties", "Effective Date", "Term", "Confidential Information",
            "Obligations", "Jurisdiction", "Risk Flags"]

    data = {}
    for fname, summary in summaries.items():
        section_map = {}
        for r in rows:
            # Try to find a line containing that section
            found = ""
            for line in summary.splitlines():
                if r.lower() in line.lower():
                    found = line
                    break
            section_map[r] = found if found else "Not specified"
        data[fname] = section_map

    df = pd.DataFrame(data)

    st.subheader("Comparison Table")
    st.dataframe(df)

    # --- Download as Excel ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Comparison")
    buffer.seek(0)

    st.download_button(
        label="Download Comparison as Excel",
        data=buffer,
        file_name="comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.write("### Full Summaries")
    for fname, summary in summaries.items():
        st.markdown(f"**{fname}**")
        st.write(summary)
