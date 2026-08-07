# SHAVY OS - AI Shell v0.2
# Built by Parth Ajmera
# Now calls the shared Intelligence Core Daemon over D-Bus,
# instead of talking to Ollama directly (v0.1 style).
# Requires core/daemon.py to be running in another terminal first.

import subprocess
from dasbus.connection import SessionMessageBus

# Connect to the daemon over D-Bus
bus = SessionMessageBus()
shavy = bus.get_proxy("com.shavy.AICore", "/com/shavy/AICore")

# Commands that are too dangerous to ever run
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "shutdown",
]

def ask_ai(what_you_want):
    """Send your words to SHAVY's shared brain and get a command back"""

    instruction = f"""Convert this request into ONE bash command.
Reply with ONLY the command. No explanation. No markdown. No extra words.

Request: {what_you_want}
Command:"""

    command = shavy.Query(instruction, "shell command generation")
    return command.strip()

def is_safe(command):
    for dangerous in BLOCKED_COMMANDS:
        if dangerous in command:
            return False
    return True

def run_command(command):
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout + result.stderr

def shavy_shell():
    print("=" * 50)
    print("  SHAVY OS - AI Shell v0.2")
    print("  Built by Parth Ajmera")
    print("  Now powered by the shared Intelligence Core Daemon")
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