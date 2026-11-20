from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CORPUS_PATH = ROOT / "data" / "corpus.jsonl"
PROMPTS = ROOT / "haq" / "prompts"
