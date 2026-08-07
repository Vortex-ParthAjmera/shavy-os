# SHAVY OS - Intelligence Core Daemon v0.2
# The always-on D-Bus service every other piece of SHAVY calls into.
# ai_shell.py and brief.py call this instead of talking to Ollama directly,
# so there's one shared brain instead of every script reinventing the
# same Ollama calls.
# v0.2 adds Remember() - lets other components report real events (like
# "I ran this command, here's the output") directly into shared memory,
# without needing a full LLM round-trip just to store a fact.

import sys
import requests
from pathlib import Path

# Reuse the Memory class we already built and tested
sys.path.insert(0, str(Path(__file__).parent))
from memory import Memory

from dasbus.connection import SessionMessageBus
from dasbus.server.interface import dbus_interface
from dasbus.loop import EventLoop

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

@dbus_interface("com.shavy.AICore")
class ShavyCore:
    """
    The D-Bus service itself. Any process on this machine can call
    Query() or Remember() on this over the session bus - that's the
    whole point of it existing.
    """

    def __init__(self):
        print("SHAVY Core: loading memory system...")
        self.memory = Memory()
        print("SHAVY Core: ready.")

    def Query(self, prompt: str, context: str) -> str:
        """
        The main method everything else calls to actually talk to the AI.
        prompt: what the user said
        context: extra info as a string (can be empty "" for now)
        Returns: the AI's response
        """
        # Pull in relevant past memories, so responses have continuity
        relevant_memories = self.memory.recall_similar(prompt, n=3)
        memory_text = "\n".join(relevant_memories) if relevant_memories else "None yet."

        full_prompt = f"""You are SHAVY, an AI operating system assistant.

Relevant past context:
{memory_text}

Current context: {context}

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

        # Remember this exchange for next time
        self.memory.store(prompt, answer)

        return answer

    def Remember(self, content: str, metadata: str) -> bool:
        """
        Store something directly in memory, no LLM call involved.
        Lets other SHAVY components (like ai_shell.py) report real events
        - "I ran X, got Y" - so future memory-based answers have
        something true to draw on, instead of just past conversations.
        """
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