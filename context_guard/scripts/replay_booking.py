"""Replay caller turns through the booking reader and the booking steps.

Usage inside the guard container:
    python scripts/replay_booking.py
No call is placed and nothing is saved. A "book" outcome is printed, not posted.
"""

import asyncio
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dialogue.booking import decide  # noqa: E402
from dialogue.graph import graph_for  # noqa: E402
from dialogue.intent import classify  # noqa: E402
from dialogue.understand import understand  # noqa: E402

CAMPAIGN = "b7e1a4c2-6d38-4f90-8a15-2c9e0d4b6f71"
TODAY = datetime.date(2026, 10, 22)

CONVERSATIONS = {
    "ashutosh, year only, then a real date": [
        "हां ज़रूर, क्या क्या details चाहिए?",
        "पूरा नाम है आशुतोष रवि गुप्ता.",
        "दो हज़ार चौबीस को.",
        "सत्ताईस October",
        "सुबह साढ़े दस",
        "नहीं सब ठीक है, धन्यवाद.",
    ],
    "akaash with filler, period asked": [
        "हां जी. क्या वेदन है?",
        "Hey, then, um, hey. आकाश चोपड़ा.",
        "मुझे चाहिए तीस October.",
        "चार पंद्रह",
        "शाम को",
        "ठीक है",
    ],
    "first name then surname, change time": [
        "हां बताइए",
        "मेरा नाम है अनुज",
        "तिवारी",
        "बाइस तारीख का सुबह छह बजे.",
        "मेरे को समय change करना था",
        "सुबह start है दस बजे",
        "ठीक है",
    ],
    "mixed phrasing": [
        "yes please, my name is Akash Chopra",
        "next Monday",
        "ded baje dopahar",
        "date change karni hai, 5 November kar do",
        "bas itna hi, thank you",
    ],
}


async def run():
    graph = graph_for(CAMPAIGN)
    for title, turns in CONVERSATIONS.items():
        print(f"\n=== {title}")
        step, opened, slots, last_bot = "offer", False, {}, graph.step("offer").ask
        for text in turns:
            intent = classify(text, graph)
            started = time.perf_counter()
            heard = await understand(text, step, slots, last_bot, TODAY, intent)
            took = (time.perf_counter() - started) * 1000
            outcome = decide(graph, step, opened, text, slots, heard, TODAY)
            opened = True
            slots = outcome["slots"]
            step = outcome["step"]
            if outcome["action"] == "book":
                said = f"[BOOK name={slots.get('name')} date={slots.get('date')} time={slots.get('time')}]"
                step = "confirm"
            elif outcome["action"] == "hangup":
                said = "[HANGUP]"
            else:
                said = outcome.get("text") or f"[{outcome['action']}]"
            print(f"USER {text}")
            print(f"     heard[{heard.source} {took:.0f}ms] intent={heard.intent} name={heard.name!r} sure={heard.name_sure} "
                  f"date={heard.date} issue={heard.date_issue} year={heard.year} time={heard.time} clock={heard.clock} change={heard.change}")
            print(f"BOT  {said}")
            last_bot = said
            if outcome["action"] == "hangup":
                break


asyncio.run(run())
