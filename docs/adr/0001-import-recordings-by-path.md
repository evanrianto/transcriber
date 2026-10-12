# Import Recordings by file path, not browser upload

Transcriber is a web app, but the user imports a Recording by choosing it on disk (native file dialog, or a pasted path) and the server reads it in place, rather than uploading it through the browser. Browsers never reveal a file's real location, so an upload would make it impossible to save the Transcript next to its video, and it would copy up to several gigabytes per hour-long video for no benefit when server and browser are the same machine.

## Consequences

- The server can read any file the user can, so it must only ever listen on `localhost`. Never bind it to a network interface.
- The browser video player is served from the server (streamed from the original path, or from a converted preview), not from a browser-side copy.
