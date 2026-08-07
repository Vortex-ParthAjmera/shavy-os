# SHAVY OS - Intelligence Core Daemon v0.3
# v0.3 fix: Query() now keeps "prompt" (what gets remembered/searched)
# separate from "context" (formatting/instructions that shape the
# response but shouldn't pollute memory with repeated boilerplate).

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
        """
        prompt: the CLEAN thing being asked/said - this is what gets
        searched and stored in memory, kept short and meaningful.
        context: formatting rules or extra instructions - shapes the
        LLM's response but is never itself stored as "what the user said".
        """
        relevant_memories = self.memory.recall_similar(prompt, n=3)
        memory_text = "\n".join(relevant_memories) if relevant_memories else "None yet."

        full_prompt = f"""You are SHAVY, an AI operating system assistant.

Relevant past context:
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