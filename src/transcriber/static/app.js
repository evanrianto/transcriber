// Transcriber page: one page, three views (import → job in progress → result).
// The server streams the current Job over /api/job/events; this page just renders it.

const $ = (id) => document.getElementById(id);

const views = {
  import: $("import-view"),
  job: $("job-view"),
  result: $("result-view"),
};

const STAGES = ["extracting_audio", "transcribing"];
const LANGUAGE_NAMES = { english: "English", indonesian: "Indonesian", mixed: "Mixed" };
const FINISHED = ["done", "failed", "cancelled"];

let events = null;
let job = null;
let segments = [];
let cancelling = false;

function show(name) {
  for (const [key, el] of Object.entries(views)) el.hidden = key !== name;
  document.querySelector(".page").classList.toggle("wide", name === "result");
  if (name !== "result") $("player").pause();
}

function formatTimestamp(seconds) {
  const total = Math.floor(seconds);
  const h = String(Math.floor(total / 3600)).padStart(2, "0");
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function formatEta(seconds) {
  if (seconds == null || !isFinite(seconds)) return "";
  if (seconds < 60) return "less than a minute left";
  const minutes = Math.round(seconds / 60);
  return `about ${minutes} minute${minutes === 1 ? "" : "s"} left`;
}

function segmentItem(segment, index, seekable = false) {
  const li = document.createElement("li");
  li.className = "segment";
  const time = document.createElement(seekable ? "button" : "span");
  time.className = "segment-time";
  if (seekable) {
    time.type = "button";
    time.dataset.index = String(index);
    time.title = "Play from here";
  }
  time.textContent = formatTimestamp(segment.start);
  const text = document.createElement("p");
  text.className = "segment-text";
  text.textContent = segment.text;
  li.append(time, text);
  return li;
}

function appendLiveSegments(newSegments, replace) {
  const list = $("live-segments");
  const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 40;
  if (replace) list.replaceChildren();
  list.append(...newSegments.map((segment, i) => segmentItem(segment, i)));
  if (nearBottom) list.scrollTop = list.scrollHeight;
}

function describeJob() {
  return `${job.recording_name} · ${LANGUAGE_NAMES[job.language_mode]}`;
}

function renderProgress() {
  $("job-recording").textContent = describeJob();
  const stageIndex = STAGES.indexOf(job.state);
  for (const el of document.querySelectorAll(".stage")) {
    const index = STAGES.indexOf(el.dataset.stage);
    el.classList.toggle("active", index === stageIndex);
    el.classList.toggle("complete", index < stageIndex);
  }

  const cancel = $("cancel-button");
  cancel.disabled = cancelling;
  cancel.textContent = cancelling ? "Cancelling…" : "Cancel";

  const transcribing = job.state === "transcribing";
  $("job-title").textContent = transcribing ? "Transcribing" : "Extracting audio";
  const started = transcribing && segments.length > 0;
  $("progress").classList.toggle("indeterminate", !started);
  $("progress-fill").style.width = started ? `${job.percent}%` : "";
  $("progress").setAttribute("aria-valuenow", String(started ? job.percent : 0));
  $("progress-percent").textContent = started ? `${Math.round(job.percent)}%` : "";
  $("progress-eta").textContent = started ? formatEta(job.eta_seconds) : "";
}

let renderedResultKey = null;

function renderResult() {
  $("result-recording").textContent = describeJob();
  $("saved-note").textContent = `Saved to ${job.saved_to}`;
  // Preview progress keeps updating after the Job is done; only rebuild the list when needed.
  const key = `${job.id}:${segments.length}`;
  if (key !== renderedResultKey) {
    renderedResultKey = key;
    $("result-segments").replaceChildren(...segments.map((s, i) => segmentItem(s, i, true)));
    currentIndex = -1;
  }
  renderPlayer();
}

// Result player: the video plays beside the Transcript; timestamps seek, and the
// Segment being played is highlighted and kept in view.

let playerSource = null;
let currentIndex = -1;
let userScrolledAt = 0;

function renderPlayer() {
  const { status, percent } = job.preview;
  if (status === "converting") {
    setPlayerNote(`Preparing preview… ${Math.round(percent)}%`);
    return;
  }
  if (status === "failed" || status === "discarded") {
    setPlayerNote("Preview unavailable for this file.");
    return;
  }
  const source = `/api/job/media?job=${job.id}&preview=${status}`;
  if (playerSource === source) return;
  playerSource = source;
  const player = $("player");
  player.classList.remove("audio-only");
  setPlayerNote("");
  player.src = source;
}

function setPlayerNote(message) {
  $("player-note").textContent = message;
  $("player-note").hidden = !message;
  $("player").hidden = Boolean(message);
}

function segmentIndexAt(time) {
  // Binary search for the last Segment starting at or before `time`.
  let low = 0;
  let high = segments.length - 1;
  let found = -1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (segments[mid].start <= time) {
      found = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return found;
}

function highlightSegment(index) {
  if (index === currentIndex) return;
  const items = $("result-segments").children;
  items[currentIndex]?.classList.remove("current");
  currentIndex = index;
  const item = items[index];
  if (!item) return;
  item.classList.add("current");
  // Don't fight someone scrolling the Transcript themselves.
  if (Date.now() - userScrolledAt > 4000) item.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

$("player").addEventListener("timeupdate", () => highlightSegment(segmentIndexAt($("player").currentTime)));

$("player").addEventListener("loadedmetadata", () => {
  $("player").classList.toggle("audio-only", $("player").videoWidth === 0);
});

$("player").addEventListener("error", () => {
  setPlayerNote("This format can't be previewed in the browser.");
});

$("result-segments").addEventListener("click", (event) => {
  const button = event.target.closest("button.segment-time");
  if (!button) return;
  const player = $("player");
  player.currentTime = segments[Number(button.dataset.index)].start;
  player.play();
});

for (const type of ["wheel", "touchmove", "keydown"]) {
  $("transcript-card").addEventListener(type, () => (userScrolledAt = Date.now()), { passive: true });
}

function render() {
  if (!job) {
    show("import");
  } else if (job.state === "done") {
    renderResult();
    show("result");
  } else if (job.state === "failed") {
    showImportError(`Couldn't transcribe ${job.recording_name}: ${job.error}`);
    show("import");
  } else if (job.state === "cancelled") {
    showImportNote(`Cancelled ${job.recording_name}. Nothing was saved.`);
    show("import");
  } else {
    renderProgress();
    show("job");
  }
}

function showImportNote(message) {
  const el = $("import-note");
  el.textContent = message;
  el.hidden = !message;
}

function showImportError(message) {
  const el = $("import-error");
  el.textContent = message;
  el.hidden = !message;
}

function isSettled(job) {
  return FINISHED.includes(job.state) && job.preview.status !== "converting";
}

function watchJob() {
  if (events) events.close();
  events = new EventSource("/api/job/events");
  events.onmessage = (message) => {
    const update = JSON.parse(message.data);
    job = update.job;
    const replace = update.segments_from === 0;
    segments = replace ? update.new_segments : segments.concat(update.new_segments);
    if (job && !FINISHED.includes(job.state)) {
      appendLiveSegments(update.new_segments, replace);
    }
    render();
    // The server closes the stream once the Job is finished; don't let EventSource reconnect.
    if (!job || isSettled(job)) events.close();
  };
}

$("import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showImportError("");
  showImportNote("");
  cancelling = false;
  const response = await fetch("/api/job", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: $("path-input").value,
      language_mode: $("language-select").value,
    }),
  });
  if (!response.ok) {
    const { detail } = await response.json();
    showImportError(detail);
    return;
  }
  watchJob();
});

$("choose-button").addEventListener("click", async () => {
  const button = $("choose-button");
  button.disabled = true;
  try {
    const response = await fetch("/api/dialog/open", { method: "POST" });
    if (!response.ok) {
      showImportError("Couldn't open the file dialog. Paste the path instead.");
      return;
    }
    const { path } = await response.json();
    if (path) {
      $("path-input").value = path;
      showImportError("");
    }
  } finally {
    button.disabled = false;
  }
});

$("cancel-button").addEventListener("click", async () => {
  cancelling = true;
  renderProgress();
  const response = await fetch("/api/job/cancel", { method: "POST" });
  if (!response.ok) cancelling = false; // already finished; the event stream shows the outcome
});

$("new-button").addEventListener("click", () => {
  showImportError("");
  showImportNote("");
  show("import");
});

watchJob();
