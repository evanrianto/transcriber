# 02: Live progress

**What to build:** While a Job runs, the user sees where it is instead of a static "Transcribing…". The page shows the stages *Extracting audio → Transcribing*, with a percentage and an estimated time remaining while transcribing. Segments appear in the Transcript view live as each one finishes, so the user can start reading before the Job is done.

**Blocked by:** 01 (Walking skeleton)

**Status:** done

- [x] The page shows the current stage: Extracting audio, then Transcribing
- [x] While transcribing, a progress bar shows the percentage complete (Segment end time ÷ Recording duration) and an estimated time remaining
- [x] Each Segment appears in the Transcript view as soon as it's produced, in order, without a page reload
- [x] When the Job finishes, the progress UI gives way to the complete Transcript and confirms where the `.txt` was saved
- [x] An error during the Job (e.g. an undecodable Recording) moves it to a failed state with a readable message
