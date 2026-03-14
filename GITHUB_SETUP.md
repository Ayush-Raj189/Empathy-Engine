# GitHub Setup Guide (Windows)

## 1) Create virtual environment
From `empathy_engine`:

```bash
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `python` maps to a different interpreter, use your full path:

```bash
"C:/Ayush files/Python P/venv/Scripts/python.exe" -m pip install -r requirements.txt
```

## 2) Run app locally

```bash
streamlit run app.py
```

## 3) Push only `empathy_engine` from your existing parent repo
Your current git root is the parent folder (`Python P`) with many projects.
To keep this push clean, commit only this project path:

```bash
cd "C:/Ayush files/Python P"
git add empathy_engine
git commit -m "Add empathy_engine project"
```

Add your remote (replace URL):

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
```

If `origin` already exists:

```bash
git remote set-url origin <YOUR_GITHUB_REPO_URL>
```

Push:

```bash
git branch -M main
git push -u origin main
```

## 4) Optional: make `empathy_engine` its own independent repo
If you prefer this folder alone as a standalone repo:

```bash
cd "C:/Ayush files/Python P/empathy_engine"
rm -rf .git
git init
git add .
git commit -m "Initial commit: empathy_engine"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 5) Before pushing, sanity check

```bash
git status
```

Confirm these are NOT staged:
- `venv/`
- `__pycache__/`
- generated files in `audio_output/`
