# SHAVY OS - AI Shell v0.4
# Built by Parth Ajmera
# Case-insensitive COMMAND/ANSWER parsing, and now reports executed
# commands back to the daemon via Remember() - so "what did I just run"
# actually has real data behind it, not just past conversations.

import subprocess
from dasbus.connection import SessionMessageBus

bus = SessionMessageBus()
shavy = bus.get_proxy("com.shavy.AICore", "/com/shavy/AICore")

BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    "shutdown",
]

def ask_ai(what_you_want):
    instruction = f"""The user said: "{what_you_want}"

Decide: does this need a bash command run on the system, or is it a
question you can answer directly, including from anything relevant
in your memory of past interactions?

If it needs a command, reply EXACTLY in this format (nothing else):
COMMAND: <the bash command>

If it's a question you can just answer, reply EXACTLY in this format:
ANSWER: <your answer>

Reply with ONLY one line, starting with COMMAND: or ANSWER:"""

    response = shavy.Query(instruction, "shell interaction")
    return response.strip()

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
    print("  SHAVY OS - AI Shell v0.4")
    print("  Built by Parth Ajmera")
    print("  Powered by the shared Intelligence Core Daemon")
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
        response = ask_ai(user_input)
        response_upper = response.upper()

        if response_upper.startswith("COMMAND:"):
            command = response[8:].strip()  # slice ORIGINAL, preserves casing
            print(f"   Command: {command}          ")

            if not is_safe(command):
                print("   SHAVY: I won't run that -- it could be dangerous.\n")
                continue

            permission = input("   Run this? (y/n): ").lower()
            if permission == "y":
                output = run_command(command)

                # Report what actually happened back to shared memory
                remembered_output = output.strip()[:300] if output.strip() else "No output"
                shavy.Remember(f"Command executed: {command}", remembered_output)

                if output.strip():
                    print(f"   Result:\n{output}")
                else:
                    print("   Done! (no output)")
            else:
                print("   Skipped.\n")

        elif response_upper.startswith("ANSWER:"):
            answer = response[7:].strip()  # "ANSWER:" is 7 characters
            print(f"   SHAVY: {answer}          \n")

        else:
            print(f"   SHAVY (unformatted): {response}          \n")

        print()

if __name__ == "__main__":
    shavy_shell()