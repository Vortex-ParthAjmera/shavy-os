# SHAVY OS - Intelligence Core Daemon v0.4
# v0.4: added debug visibility into what memory actually gets retrieved,
# so we can SEE the internal state instead of guessing at it from outside.
# Also relabeled the memory section to more directly tell the model to
# check it before deciding a new command is needed.

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

        # DEBUG: show exactly what's being retrieved, right here in the
        # daemon's own terminal - this is the thing we actually need to see
        print(f"\n[DEBUG] Incoming query: {prompt}")
        print(f"[DEBUG] Memories retrieved:\n{memory_text}")
        print("[DEBUG] ---")

        full_prompt = f"""You are SHAVY, an AI operating system assistant.

FACTS FROM YOUR MEMORY (check here FIRST - if the answer is already here, use it, don't generate a new command):
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

        self.memory.store(prompt, answer)
        return answer

    def Remember(self, content: str, metadata: str) -> bool:
        try:
            self.memory.store(content, metadata)
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