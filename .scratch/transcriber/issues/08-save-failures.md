# 08: Save failures: Copy and Save as…

**What to build:** Sometimes the Transcript can't be written next to the Recording, for example on a read-only folder, a network share, or a protected location. When that happens the result screen still shows the full Transcript, plus a clear "Couldn't save next to the video" message and two ways to keep the work: **Copy** (to clipboard) and **Save as…** (the native OS save dialog, reusing the mechanism from 04).

**Blocked by:** 01 (Walking skeleton), 04 ("Choose file" via the OS dialog)

**Status:** ready-for-agent

- [ ] If writing the `.txt` next to the Recording fails, the Job still finishes as done, and the result screen shows the Transcript with a clear error naming the folder
- [ ] **Copy** puts the whole Transcript, in the `[hh:mm:ss] text` format, on the clipboard and confirms it
- [ ] **Save as…** opens the native save dialog, pre-filled with the usual `<name>.transcript.<timestamp>.txt` name, and writes the Transcript where the user chooses
- [ ] A successful save via **Save as…** replaces the error with the saved location
