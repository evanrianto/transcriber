# 04: "Choose file" via the OS dialog

**What to build:** Instead of having to paste a path, the user clicks **Choose file**, picks the Recording in their operating system's normal file dialog, and the path is filled in. Pasting a path still works. Because the server runs on the same machine (ADR-0001), the backend can open the native dialog.

**Blocked by:** 01 (Walking skeleton)

**Status:** ready-for-agent

- [ ] Clicking **Choose file** opens the native OS file dialog, filtered to common video and audio types with an "All files" option
- [ ] Choosing a file fills in its path; cancelling the dialog changes nothing
- [ ] Pasting a path by hand still works
- [ ] The dialog works on Windows, macOS, and Linux (on macOS it must not crash from being opened off the main thread)
