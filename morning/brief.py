# SHAVY OS - Morning Brief v0.2
# Fetches: new papers (astrophysics, quantum computing, AI/ML, data science,
# computer science), Codeforces contests, your deadlines
# v0.2: now calls the shared Intelligence Core Daemon over D-Bus, same as
# ai_shell.py, instead of talking to Ollama directly.
# Requires core/daemon.py to be running in another terminal first.

import subprocess
import requests
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from dasbus.connection import SessionMessageBus

DB_PATH = Path.home() / ".ai-os" / "memory.db"

# Connect to the daemon over D-Bus
bus = SessionMessageBus()
shavy = bus.get_proxy("com.shavy.AICore", "/com/shavy/AICore")

def init_db():
    """Make sure the deadlines table exists before we use it"""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""CREATE TABLE IF NOT EXISTS deadlines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        due_date TEXT NOT NULL,
        subject TEXT,
        completed INTEGER DEFAULT 0
    )""")
    db.commit()
    return db

def get_new_papers():
    """New papers across your research areas"""
    domains = {
        "Astrophysics": "cat:astro-ph.CO AND (dark+matter OR axion OR WIMP)",
        "Quantum Computing": "cat:quant-ph AND (quantum+error+correction OR qubit)",
        "AI/ML": "cat:cs.LG AND (large+language+model OR transformer)",
        "Data Science": "cat:stat.ML AND (time+series OR causal+inference OR data+pipeline)",
        "Computer Science": "cat:cs.OS AND (operating+system OR kernel OR distributed+system)",
    }
    all_papers = []
    for domain_name, query in domains.items():
        params = {
            "search_query": query,
            "start": 0,
            "max_results": 1,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        try:
            resp = requests.get("http://export.arxiv.org/api/query", params=params, timeout=10)
            root = ET.fromstring(resp.content)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entry = root.find("a:entry", ns)
            if entry is not None:
                title = entry.find("a:title", ns).text.strip().replace("\n", " ")
                all_papers.append(f"[{domain_name}] {title}")
        except Exception:
            continue
    return all_papers if all_papers else ["(no new papers found)"]

def get_contests():
    """Upcoming Codeforces contests (free API, no key needed)"""
    try:
        r = requests.get("https://codeforces.com/api/contest.list", timeout=10).json()
        upcoming = [c for c in r["result"] if c["phase"] == "BEFORE"][:2]
        return [c["name"] for c in upcoming]
    except Exception as e:
        return [f"(couldn't fetch contests: {e})"]

def get_deadlines(db):
    """Your saved deadlines, soonest first"""
    rows = db.execute(
        "SELECT task, due_date, subject FROM deadlines "
        "WHERE completed = 0 ORDER BY due_date LIMIT 4"
    ).fetchall()
    return [f"{task} ({subject}) due {due}" for task, due, subject in rows]

def get_system_health():
    disk = subprocess.run("df -h / | awk 'NR==2{print $4}'",
                         shell=True, capture_output=True, text=True).stdout.strip()
    gpu = subprocess.run(
        "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null",
        shell=True, capture_output=True, text=True).stdout.strip()
    return f"{disk} disk free, GPU at {gpu or 'N/A'} degrees C"

def add_deadline(db, task, due_date, subject="General"):
    db.execute("INSERT INTO deadlines (task, due_date, subject) VALUES (?, ?, ?)",
              (task, due_date, subject))
    db.commit()
    print(f"Added: {task} due {due_date}")

def remove_deadline(db, task):
    cursor = db.execute("DELETE FROM deadlines WHERE task = ?", (task,))
    db.commit()
    if cursor.rowcount > 0:
        print(f"Removed: {task}")
    else:
        print(f"No deadline found matching: {task}")

def generate_brief(papers, contests, deadlines, health):
    # The DATA is the "prompt" (clean, meaningful, worth remembering/searching)
    data_summary = f"""Date: {datetime.now().strftime('%A, %B %d')}
New papers: {papers}
Upcoming contests: {contests}
Deadlines: {deadlines or ['Nothing urgent']}
System: {health}"""

    # The STYLE RULES are the "context" (formatting instructions, not data)
    instructions = """You are SHAVY, a morning briefing assistant for a CS
student and researcher across astrophysics, quantum computing, AI/ML, data
science, and computer science. Write a short brief (60-90 words). Be direct.
Lead with the most time-sensitive item."""

    return shavy.Query(data_summary, instructions)

if __name__ == "__main__":
    db = init_db()

    if len(sys.argv) >= 4 and sys.argv[1] == "add":
        add_deadline(db, sys.argv[2], sys.argv[3],
                    sys.argv[4] if len(sys.argv) > 4 else "General")
    elif len(sys.argv) >= 3 and sys.argv[1] == "remove":
        remove_deadline(db, sys.argv[2])
    else:
        print("Gathering your morning brief...\n")
        papers = get_new_papers()
        contests = get_contests()
        deadlines = get_deadlines(db)
        health = get_system_health()

        brief = generate_brief(papers, contests, deadlines, health)
        print("=" * 50)
        print(brief)
        print("=" * 50)