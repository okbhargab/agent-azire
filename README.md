# agent-azire

## Setup

1. Clone the repository:

```powershell
git clone https://github.com/okbhargab/agent-azire.git
cd agent-azire
```

2. Create and activate a Python virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies if a `requirements.txt` file is added later. If you use `.env`, install `python-dotenv` too:

```powershell
pip install -r requirements.txt
pip install python-dotenv
```

4. Copy `.env.example` to `.env` and add your secrets. This repo already ignores `.env`.

```powershell
copy .env.example .env
```

```text
GENAI_API_KEY=your_api_key_here
```

5. Run tests:

```powershell
python -m pytest
```

## Notes

- The project currently includes `test_gem.py` and `test_trace.py`.
- If you add dependencies, commit a `requirements.txt` file so others can install them easily.
