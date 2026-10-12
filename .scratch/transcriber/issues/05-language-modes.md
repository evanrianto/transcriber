# 05: Language Modes

**What to build:** At import time the user picks the Recording's Language Mode from a dropdown: English, Indonesian, or Mixed. It always defaults to English. Mixed is for Indonesian with English words and phrases woven into the same sentences. It forces Indonesian and gives Whisper an initial prompt of code-mixed example text, so English words are written as spoken instead of translated. There is deliberately no "Auto" option.

**Blocked by:** 01 (Walking skeleton)

**Status:** ready-for-agent

- [ ] The import screen has a Language Mode dropdown with English / Indonesian / Mixed, defaulting to English on every load
- [ ] English and Indonesian force that language for the whole Recording
- [ ] Mixed forces Indonesian and supplies a short code-mixed Indonesian/English initial prompt
- [ ] The chosen Language Mode is shown while the Job runs and on the result

## Comments

Mixed has not been validated on a real code-mixed Recording yet. Validating it is a follow-up once a sample clip is available.
