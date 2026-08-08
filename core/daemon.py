# SHAVY OS - Intelligence Core Daemon v0.5
# v0.5: memory now distinguishes VERIFIED FACTS (real events, like actual
# command output) from PAST CONVERSATION (what the model said before,
# which might have been wrong). Without this split, a wrong answer once
# gets treated as precedent and repeats itself forever.

import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from memory import Memory

from dasbus.connection import SessionMessageBus
from dasbus.server.interface import dbus_interface
from dasbus.loop import EventLoop

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

@dbus_interface("com.shavy.AICore")
class ShavyCore:
    def __init__(self):
        print("SHAVY Core: loading memory system...")
        self.memory = Memory()
        print("SHAVY Core: ready.")

    def Query(self, prompt: str, context: str) -> str:
        relevant_memories = self.memory.recall_similar(prompt, n=3)
        memory_text = "\n---\n".join(relevant_memories) if relevant_memories else "None yet."

        print(f"\n[DEBUG] Incoming query: {prompt}")
        print(f"[DEBUG] Memories retrieved:\n{memory_text}")
        print("[DEBUG] ---")

        full_prompt = f"""You are SHAVY, an AI operating system assistant.

MEMORY (mixed: some entries are [VERIFIED FACT] - real events, trust these
completely. Others are [PAST CONVERSATION] - what you said before, which
may have been wrong. Never treat a [PAST CONVERSATION] answer as proof it
was correct - only [VERIFIED FACT] entries are ground truth):
{memory_text}

{context}

User: {prompt}
SHAVY:"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": full_prompt,
                "stream": False,
                "think": False
            },
            timeout=30
        )
        answer = response.json()["response"].strip()

        # This exchange gets stored as CONVERSATION, not fact - it's what
        # the model said, not something independently verified as true
        self.memory.store(f"[PAST CONVERSATION] {prompt}", answer)
        return answer

    def Remember(self, content: str, metadata: str) -> bool:
        """
        Store a VERIFIED FACT - something that actually happened
        (a real command execution and its real output), not just
        something the model said. This is what future memory-based
        answers should trust over their own past conversational guesses.
        """
        try:
            self.memory.store(f"[VERIFIED FACT] {content}", metadata)
            return True
        except Exception:
            return False


def main():
    bus = SessionMessageBus()
    core = ShavyCore()

    bus.publish_object("/com/shavy/AICore", core)
    bus.register_service("com.shavy.AICore")

    print("SHAVY Core Daemon is running on D-Bus as com.shavy.AICore")
    print("Press Ctrl+C to stop.")

    loop = EventLoop()
    loop.run()


if __name__ == "__main__":
    main()