# SHAVY OS - Memory System v0.1
# Two tiers: SQLite for recency, ChromaDB for semantic (meaning-based) search.
# This is a standalone, testable piece - the daemon will use it, but it
# doesn't need the daemon to work on its own.

import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = Path.home() / ".ai-os" / "memory.db"
VEC_PATH = Path.home() / ".ai-os" / "memory_vec"

class Memory:
    def __init__(self):
        # Make sure the .ai-os folder exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # SQLite: fast, recent, chronological
        self.db = sqlite3.connect(str(DB_PATH))
        self.db.execute("""CREATE TABLE IF NOT EXISTS interactions (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            user_input TEXT,
            ai_response TEXT
        )""")
        self.db.commit()

        # ChromaDB: semantic search by meaning, not just recency
        self.vec_client = chromadb.PersistentClient(str(VEC_PATH))
        self.collection = self.vec_client.get_or_create_collection("interactions")

        # This line downloads the embedding model the FIRST time you run it
        # (a few hundred MB from HuggingFace). After that, it's cached locally.
        print("Loading embedding model (first run downloads it, then it's cached)...")
        self.embedder = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5")
        print("Ready.")

    def store(self, user_input, ai_response):
        """Save one interaction to both memory tiers"""
        memory_id = str(uuid.uuid4())  # always unique, never overwrites
        timestamp = datetime.now().isoformat()

        # Tier 1: SQLite
        self.db.execute(
            "INSERT INTO interactions VALUES (?, ?, ?, ?)",
            (memory_id, timestamp, user_input, ai_response)
        )
        self.db.commit()

        # Tier 2: ChromaDB (embed the combined text so search finds
        # matches based on either the question or the answer)
        combined = f"User: {user_input}\nSHAVY: {ai_response}"
        embedding = self.embedder.encode([combined])[0].tolist()
        self.collection.add(
            documents=[combined],
            embeddings=[embedding],
            ids=[memory_id],
            metadatas=[{"timestamp": timestamp}]
        )

    def recall_recent(self, n=5):
        """Get the last N interactions, most recent first"""
        rows = self.db.execute(
            "SELECT timestamp, user_input, ai_response FROM interactions "
            "ORDER BY timestamp DESC LIMIT ?", (n,)
        ).fetchall()
        return rows

    def recall_similar(self, query, n=5):
        """Find past interactions similar in MEANING to the query,
        even if they don't share any of the same words"""
        query_embedding = self.embedder.encode([query])[0].tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n
        )
        return results["documents"][0] if results["documents"] else []


if __name__ == "__main__":
    print("Testing SHAVY's memory system...\n")
    mem = Memory()

    # Store a few test memories
    mem.store("What is dark matter?", "Dark matter is invisible matter that doesn't interact with light.")
    mem.store("How do I list files in Linux?", "Use the ls command, or ls -la for details.")
    mem.store("What's the capital of Japan?", "Tokyo is the capital of Japan.")

    print("Stored 3 test memories.\n")

    print("Recent memories:")
    for timestamp, user_input, ai_response in mem.recall_recent(3):
        print(f"  [{timestamp}] {user_input} -> {ai_response}")

    print("\nSearching for something about 'physics' (semantic match, not exact words):")
    similar = mem.recall_similar("tell me about physics and space", n=2)
    for result in similar:
        print(f"  {result}")