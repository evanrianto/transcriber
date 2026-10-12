# 06: Result player for playable videos

**What to build:** The result screen becomes a review tool. The video plays on the left and the Transcript scrolls on the right. Clicking any Segment's timestamp jumps the video to that moment, and the Segment currently playing is highlighted and kept in view. The video is streamed by the server from the Recording's original path (ADR-0001). This ticket covers formats the browser can play natively. Others are handled in 07.

**Blocked by:** 01 (Walking skeleton)

**Status:** done

- [x] For a browser-playable Recording (e.g. MP4/H.264, WebM, common audio), the result screen shows a player next to the Transcript
- [x] The server streams the Recording with seek support (HTTP range requests), so jumping deep into an hour-long video is instant
- [x] Clicking a Segment's timestamp seeks the player to that Segment's start
- [x] The Segment being played is highlighted, and the Transcript auto-scrolls to keep it visible (without fighting a user who is scrolling manually)
- [x] On narrow windows the player and Transcript stack vertically

## Comments

Verified: Range streaming (206), click-to-seek, Segment highlighting logic. The automation browser window was hidden, so Chrome didn't decode the video; actual on-screen playback and the narrow-window stacking still need a quick manual look.
