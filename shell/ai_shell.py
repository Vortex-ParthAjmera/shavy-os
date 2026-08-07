# SHAVY OS - AI Shell v0.5
# Built by Parth Ajmera
# v0.5 fix: sends your CLEAN words as the memory-searchable prompt,
# and moves the COMMAND/ANSWER formatting rules into context instead -
# so memory stores real content, not repeated formatting boilerplate.

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

FORMAT_INSTRUCTIONS = """Decide: does this need a bash command run on the system, or is it a
question you can answer directly, including from anything relevant
in your memory of past interactions?

If it needs a command, reply EXACTLY in this format (nothing else):
COMMAND: <the bash command>

If it's a question you can just answer, reply EXACTLY in this format:
ANSWER: <your answer>

Reply with ONLY one line, starting with COMMAND: or ANSWER:"""

def ask_ai(what_you_want):
    response = shavy.Query(what_you_want, FORMAT_INSTRUCTIONS)
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
    print("  SHAVY OS - AI Shell v0.5")
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
            command = response[8:].strip()
            print(f"   Command: {command}          ")

            if not is_safe(command):
                print("   SHAVY: I won't run that -- it could be dangerous.\n")
                continue

            permission = input("   Run this? (y/n): ").lower()
            if permission == "y":
                output = run_command(command)
                remembered_output = output.strip()[:300] if output.strip() else "No output"
                shavy.Remember(f"Command executed: {command}", remembered_output)

                if output.strip():
                    print(f"   Result:\n{output}")
                else:
                    print("   Done! (no output)")
            else:
                print("   Skipped.\n")

        elif response_upper.startswith("ANSWER:"):
            answer = response[7:].strip()
            print(f"   SHAVY: {answer}          \n")

        else:
            print(f"   SHAVY (unformatted): {response}          \n")

        print()

if __name__ == "__main__":
    shavy_shell()