# 📄 AI Resume ATS Checker

Upload a resume (PDF, DOCX or TXT), optionally paste a job description, and get:

- An overall **ATS score** (0-100) and a breakdown by formatting, keywords, experience impact, skills, education and readability
- Strengths and weaknesses
- Matched and missing keywords
- Prioritised improvements (High / Medium / Low)
- Before/after rewrite examples
- A downloadable JSON report

Built with [Streamlit](https://streamlit.io) and the Google Gemini Flash model (`google-genai` SDK).

## Project structure

```
.
├── app.py            # Streamlit app
├── requirements.txt  # Python dependencies
└── README.md
```

## Run locally

1. Get a free Gemini API key at <https://aistudio.google.com/apikey>.
2. Install dependencies (Python 3.10+ recommended):
   ```bash
   pip install -r requirements.txt
   ```
3. Provide your API key in one of these ways:
   - Paste it into the sidebar when the app is running, **or**
   - Set an environment variable:
     - macOS/Linux: `export GEMINI_API_KEY="your-key"`
     - Windows (PowerShell): `$env:GEMINI_API_KEY="your-key"`
   - **or** create `.streamlit/secrets.toml` containing `GEMINI_API_KEY = "your-key"`
4. Start the app:
   ```bash
   streamlit run app.py
   ```

## Change the model

The default model is `gemini-2.5-flash`. You can type any other Gemini Flash model id in the sidebar, or change `DEFAULT_MODEL` at the top of `app.py`. If you get a "model not found" error, check the current model names at <https://ai.google.dev/gemini-api/docs/models>.

## Push to GitHub (using the website, no command line)

1. Sign in at <https://github.com> and click **+** (top right) → **New repository**.
2. Enter a name such as `ats-resume-checker`, choose **Public** (Streamlit's free hosting needs a public repo unless you connect a private one), and click **Create repository**.
3. On the new repo page, click **uploading an existing file**.
4. Drag and drop `app.py`, `requirements.txt` and `README.md` into the page.
5. Write a commit message like `Initial commit` and click **Commit changes**.

> **Never upload your API key.** Do not put it in any file you upload, and do not upload a `secrets.toml` file.

## Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with your GitHub account (authorise access if asked).
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Choose your repository, branch `main`, and set **Main file path** to `app.py`.
4. Open **Advanced settings** → **Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```
5. Click **Deploy**. The first build takes a couple of minutes, then you get a public `*.streamlit.app` link.

To update the app later, edit a file on GitHub (pencil icon → **Commit changes**); Streamlit redeploys automatically.

> If you deploy publicly with your own key in Secrets, anyone with the link uses your Gemini quota. To avoid that, leave the secret out and let visitors paste their own key in the sidebar, or restrict app access in Streamlit's sharing settings.

## Notes and limitations

- Scanned (image-only) PDFs cannot be read. That is also a problem for real ATS software, so use a text-based PDF or DOCX.
- The score is an AI estimate of ATS-friendliness and keyword fit, not the output of a specific ATS product. Use it as guidance.
- Resume text is sent to Google's Gemini API for analysis. Do not upload resumes you are not comfortable sharing with that service.
- Files are limited to 5 MB and the first 20,000 characters of text are analysed.
