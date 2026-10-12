# 05: Language Modes

**What to build:** At import time the user picks the Recording's Language Mode from a dropdown: English, Indonesian, or Mixed. It always defaults to English. Mixed is for Indonesian with English words and phrases woven into the same sentences. It forces Indonesian and gives Whisper an initial prompt of code-mixed example text, so English words are written as spoken instead of translated. There is deliberately no "Auto" option.

**Blocked by:** 01 (Walking skeleton)

**Status:** done

- [x] The import screen has a Language Mode dropdown with English / Indonesian / Mixed, defaulting to English on every load
- [x] English and Indonesian force that language for the whole Recording
- [x] Mixed forces Indonesian and supplies a short code-mixed Indonesian/English initial prompt
- [x] The chosen Language Mode is shown while the Job runs and on the result

## Comments

Mixed has not been validated on a real code-mixed Recording yet. Validating it is a follow-up once a sample clip is available.

Implementation finding: passing the hint as a prompt to faster-whisper's batched pipeline collapses Segments to ~30 seconds. Mixed therefore runs the sequential pipeline (sentence-sized Segments, ~9x slower: roughly 15 minutes per hour of Recording on an RTX 4070 SUPER). English and Indonesian stay batched. Also observed: forced Indonesian *without* the hint already left English speech untranslated, so once a real code-mixed clip is available, compare Mixed against plain Indonesian; if they match, Mixed could drop the hint and get the batched speed back.
