// Transcriber page: one page, three views (import → job in progress → result).
// The server streams the current Job over /api/job/events; this page just renders it.

const $ = (id) => document.getElementById(id);

const views = {
  import: $("import-view"),
  job: $("job-view"),
  result: $("result-view"),
};

const STAGES = ["extracting_audio", "transcribing"];
const FINISHED = ["done", "failed", "cancelled"];

let events = null;
let job = null;
let segments = [];
let cancelling = false;

function show(name) {
  for (const [key, el] of Object.entries(views)) el.hidden = key !== name;
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

function segmentItem(segment) {
  const li = document.createElement("li");
  li.className = "segment";
  const time = document.createElement("span");
  time.className = "segment-time";
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
  list.append(...newSegments.map(segmentItem));
  if (nearBottom) list.scrollTop = list.scrollHeight;
}

function renderProgress() {
  $("job-recording").textContent = job.recording_name;
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

function renderResult() {
  $("result-recording").textContent = job.recording_name;
  $("saved-note").textContent = `Saved to ${job.saved_to}`;
  $("result-segments").replaceChildren(...segments.map(segmentItem));
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
    if (!job || FINISHED.includes(job.state)) events.close();
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
    body: JSON.stringify({ path: $("path-input").value }),
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
