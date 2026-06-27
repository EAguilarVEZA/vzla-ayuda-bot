#!/usr/bin/env python3
"""Terminal tester for the bot — chat with it without Twilio or a phone.

    python scripts/chat.py

Type messages and see replies. Commands: '/reset' new tester, '/quit' to exit.
Set ANTHROPIC_API_KEY to also test free-text understanding + translation; without
it, the numeric menu (1-11) and keywords still work fully.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.matching import init_db  # noqa: E402
from app import bot               # noqa: E402


def main():
    init_db()
    user = "cli:" + uuid.uuid4().hex[:8]
    print("Ayuda Venezuela — terminal tester. /reset, /quit.\n")
    print("bot> Type 'hola' to start.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if text == "/quit":
            break
        if text == "/reset":
            bot.handle(user, "BORRAR")
            user = "cli:" + uuid.uuid4().hex[:8]
            print("(new tester)\n")
            continue
        reply = bot.handle(user, text)
        print("\nbot> " + str(reply) + "\n")


if __name__ == "__main__":
    main()
