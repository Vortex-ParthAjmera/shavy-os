# SHAVY OS - AI Shell v0.1
# Built by Parth Ajmera
# This is the first piece of SHAVY OS

import subprocess
import requests

# The address of your local AI (running on YOUR computer, not the internet)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

# Commands that are too dangerous to ever run
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "shutdown",
]

def ask_ai(what_you_want):
    """Send your words to the AI and get a command back"""

    instruction = f"""You are SHAVY, an AI operating system.
The user wants to do something on their Linux computer.
Convert their request into ONE bash command.
Reply with ONLY the command. No explanation. No markdown. No extra words.

User request: {what_you_want}
Command:"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": instruction,
            "stream": False,
            "think": False
        },
        timeout=30
    )

    command = response.json()["response"].strip()
    return command

def is_safe(command):
    """Check if the command is safe to run"""
    for dangerous in BLOCKED_COMMANDS:
        if dangerous in command:
            return False
    return True

def run_command(command):
    """Actually run the command on your computer"""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout + result.stderr

def shavy_shell():
    """The main SHAVY shell loop"""
    print("=" * 50)
    print("  SHAVY OS - AI Shell v0.1")
    print("  Built by Parth Ajmera")
    print("  Type what you want to do. Type 'quit' to exit.")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("You -> ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("SHAVY: Goodbye!")
            break

        if not user_input:
            continue

        print("   SHAVY thinking...", end="\r")
        command = ask_ai(user_input)

        print(f"   Command: {command}          ")

        if not is_safe(command):
            print("   SHAVY: I won't run that -- it could be dangerous.\n")
            continue

        permission = input("   Run this? (y/n): ").lower()

        if permission == "y":
            output = run_command(command)
            if output.strip():
                print(f"   Result:\n{output}")
            else:
                print("   Done! (no output)")
        else:
            print("   Skipped.\n")

        print()

if __name__ == "__main__":
    shavy_shell()