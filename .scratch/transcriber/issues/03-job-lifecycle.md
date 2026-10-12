# 03: Job lifecycle: lock, cancel, reconnect

**What to build:** There is only ever one Job, with no queue. While a Job is running the user can't start another, but they can cancel it. If they refresh or close the tab mid-Job, reopening the app puts them back on the running Job's live progress, including the Segments produced so far. After a Job finishes, a refresh still shows that last result until they import the next Recording.

**Blocked by:** 02 (Live progress)

**Status:** done

- [x] While a Job is running, importing is disabled in the UI, and the server rejects a second Job even if the UI is bypassed
- [x] A Cancel button stops the running Job promptly. A cancelled Job writes no `.txt`, and importing becomes available again
- [x] Refreshing or reopening the page during a Job reconnects to it: current stage, progress, and all Segments produced so far are shown, and live updates continue
- [x] After a Job finishes, refreshing shows the last result until the next import
- [x] Automated tests cover the Job states (importing → transcribing → done / failed / cancelled) and the single-Job rule
