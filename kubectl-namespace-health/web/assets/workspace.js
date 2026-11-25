const byId = (id) => document.getElementById(id);
const form = byId("analysis-form");
const source = byId("source");
const fixture = byId("fixture");
const namespace = byId("namespace");
let activeRequest;
let namespaceRequest;
let displayed;
let sortKey = "name";
let ascending = true;

function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function set(id, text) {
  byId(id).textContent = text;
}

function show(id, visible) {
  byId(id).hidden = !visible;
}

function message(id, text) {
  set(id, text);
  show(id, Boolean(text));
}

function pending() {
  show("pending", true);
}

function setNamespaces(values) {
  const options = values.filter((name) => typeof name === "string");
  byId("namespaces").replaceChildren(...options.map((name) => {
    const option = document.createElement("option");
    option.value = name;
    return option;
  }));
}

async function loadNamespaces() {
  namespaceRequest?.abort();
  const controller = new AbortController();
  namespaceRequest = controller;
  setNamespaces([]);
  if (source.value === "custom") return;
  try {
    const response = await fetch("/api/scenarios/" + source.value, {signal: controller.signal});
    if (response.ok) {
      const metadata = await response.json();
      if (!controller.signal.aborted) setNamespaces(metadata.namespaces);
    }
  } catch {
    // Namespace input and the analysis request remain available without suggestions.
  }
}

function setSourceFields() {
  const custom = source.value === "custom";
  show("file-field", custom);
  fixture.required = custom;
}

function updateFixtureSuggestions() {
  const file = fixture.files[0];
  const controller = new AbortController();
  namespaceRequest?.abort();
  namespaceRequest = controller;
  setNamespaces([]);
  if (!file || file.size > 4 * 1024 * 1024) return;
  file.text().then((content) => {
    if (controller.signal.aborted) return;
    const names = JSON.parse(content)?.metadata?.namespaces;
    if (Array.isArray(names)) setNamespaces(names);
  }).catch(() => {
    // The Python API reports detailed fixture validation on submission.
  });
}

function readInputs() {
  const scenario = source.value;
  return {
    scenario,
    file: scenario === "custom" ? fixture.files[0] : null,
    label: scenario === "custom" ? fixture.files[0]?.name : source.selectedOptions[0].label,
    namespace: namespace.value.trim(),
    restart_threshold: byId("restart-threshold").valueAsNumber,
    recent_minutes: byId("recent-minutes").valueAsNumber,
    now: byId("reference-time").value.trim() || null,
  };
}

async function runAnalysis() {
  if (!form.reportValidity()) return;
  const inputs = readInputs();
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  let reachedAPI = false;
  show("pending", false);
  message("error", "");
  message("loading", `Analyzing ${inputs.namespace} · ${inputs.label}…`);
  set("api-state", "Requesting analysis");
  try {
    if (!inputs.namespace || !Number.isSafeInteger(inputs.recent_minutes) ||
        !Number.isSafeInteger(inputs.restart_threshold)) {
      throw new Error("Enter a namespace and whole-number analysis settings within the supported range.");
    }
    const {namespace, restart_threshold, recent_minutes, now} = inputs;
    const payload = {namespace, restart_threshold, recent_minutes, now};
    if (inputs.file) {
      if (inputs.file.size > 4 * 1024 * 1024) throw new Error("The snapshot exceeds the 4 MiB request limit.");
      payload.fixture = await inputs.file.text();
    } else {
      payload.scenario = inputs.scenario;
    }
    const body = JSON.stringify(payload);
    if (new TextEncoder().encode(body).length > 4 * 1024 * 1024) {
      throw new Error("The snapshot and settings exceed the 4 MiB request limit.");
    }
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body,
      signal: controller.signal,
    });
    reachedAPI = response.ok || response.status === 422;
    const data = await response.json().catch(() => null);
    if (controller.signal.aborted) return;
    if (!response.ok) {
      throw new Error(typeof data?.detail === "string" ? data.detail : `Analysis failed (HTTP ${response.status}). Try again.`);
    }
    if (!data?.summary) {
      reachedAPI = false;
      throw new Error("The API returned an incomplete analysis report. Try again.");
    }
    displayed = {data, inputs};
    renderReport();
    set("api-state", "Analysis API responded");
  } catch (error) {
    if (controller.signal.aborted) return;
    const details = error instanceof TypeError ? "The analysis API could not be reached. Try again." : error.message;
    const previous = displayed ? " The previous report is still shown." : "";
    message("error", details + previous);
    set("api-state", reachedAPI ? "Analysis API responded" : "Analysis incomplete");
  } finally {
    if (!controller.signal.aborted) message("loading", "");
  }
}

function shellQuote(value) {
  return "'" + String(value).replaceAll("'", "'\"'\"'") + "'";
}

function renderReport() {
  const {data, inputs} = displayed;
  set("snapshot-label", inputs.label);
  set("namespace-title", data.namespace);
  set("health-status", data.status);
  byId("health-status").className = "health-status " + data.status.toLowerCase();
  const time = byId("report-time");
  time.dateTime = data.reference_time;
  time.textContent = data.reference_time.replace("T", " ").replace("+00:00", " UTC");
  set("applied-settings", `Restart threshold ${data.thresholds.restart_threshold} per pod · Warning window ${data.thresholds.recent_minutes} min`);
  const summary = data.summary;
  set("ready-value", `${summary.ready_pods} / ${summary.evaluated_pods}`);
  set("completed-value", summary.completed_pods);
  set("restart-value", summary.total_restarts);
  set("warning-value", summary.recent_warning_records);
  byId("findings").replaceChildren(...data.reasons.map((reason) => element("li", reason)));
  const unknownTimes = data.timestamp_diagnostics.unusable_warning_records;
  message("timestamp-note", unknownTimes.length ? "Warning time unavailable for " + unknownTimes.join(", ") : "");
  const snapshot = inputs.file ? "--fixture ./snapshot.json" : "--scenario " + inputs.scenario;
  const command = [
    "kubectl ns-health",
    snapshot,
    "--namespace " + shellQuote(data.namespace),
    "--restart-threshold " + data.thresholds.restart_threshold,
    "--recent-minutes " + data.thresholds.recent_minutes,
    "--now",
    "  " + shellQuote(data.reference_time),
    "--json",
  ].join(" \\\n  ");
  set("command", command);
  set("copy-feedback", "");
  show("command-help", Boolean(inputs.file));
  renderPods();
  renderEvents();
  show("report", true);
  show("reproduce", true);
}

function podReadiness(pod) {
  if (pod.terminating) return ["Terminating", "degraded"];
  if (pod.phase === "Succeeded") return ["Completed", "secondary"];
  if (pod.ready) return ["Ready", "healthy"];
  return ["Not ready", pod.phase === "Failed" ? "critical" : "degraded"];
}

function showPod(pod) {
  set("pod-dialog-title", pod.name);
  const details = [
    ["Phase", pod.phase],
    ["Readiness", podReadiness(pod)[0]],
    ["Cumulative restarts", pod.restarts],
    ["Waiting reasons", pod.waiting_reasons.join(", ") || "None reported"],
  ];
  byId("pod-detail").replaceChildren(...details.flatMap(([label, value]) => [
    element("dt", label), element("dd", value),
  ]));
  byId("pod-dialog").showModal();
}

function renderPods() {
  const pods = displayed.data.pods;
  const query = byId("pod-search").value.trim().toLowerCase();
  const filter = byId("pod-filter").value;
  const visible = pods.filter((pod) => {
    const phaseMatches = filter === "all" ||
      (filter === "ready" && pod.ready) ||
      (filter === "completed" && pod.phase === "Succeeded") ||
      (filter === "unready" && !pod.ready && pod.phase !== "Succeeded");
    return phaseMatches && pod.name.toLowerCase().includes(query);
  });
  visible.sort((a, b) => {
    const difference = sortKey === "name" ? a.name.localeCompare(b.name) : a.restarts - b.restarts;
    return (ascending ? difference : -difference) || a.name.localeCompare(b.name);
  });
  byId("pod-rows").replaceChildren(...visible.map((pod) => {
    const row = document.createElement("tr");
    const name = element("th", "", "pod-name");
    name.scope = "row";
    const inspect = element("button", pod.name, "row-link");
    inspect.type = "button";
    inspect.addEventListener("click", () => showPod(pod));
    name.append(inspect);
    const [status, color] = podReadiness(pod);
    row.append(name, element("td", pod.phase), element("td", status, color), element("td", pod.restarts, "number"));
    return row;
  }));
  set("pod-count", visible.length === pods.length ? pods.length : `${visible.length}/${pods.length}`);
  show("pod-table-wrap", Boolean(visible.length));
  message("pod-empty", visible.length ? "" : pods.length ? "No pods match these filters." : "This snapshot contains no pods for the selected namespace.");
}

function renderEvents() {
  const events = displayed.data.recent_warning_events;
  const query = byId("event-search").value.trim().toLowerCase();
  const visible = events.filter(({name, reason, message}) => `${name} ${reason} ${message}`.toLowerCase().includes(query));
  byId("event-rows").replaceChildren(...visible.map((event) => {
    const row = document.createElement("tr");
    const name = element("th", "", "event-name");
    name.scope = "row";
    name.append(element("span", event.name, "technical"), element("span", event.reason, "event-reason"));
    row.append(name, element("td", event.message), element("td", event.timestamp.replace("T", " ").replace("+00:00", ""), "technical"));
    return row;
  }));
  set("event-count", visible.length === events.length ? events.length : `${visible.length}/${events.length}`);
  show("event-table-wrap", Boolean(visible.length));
  message("event-empty", visible.length ? "" : events.length ? "No warning events match this filter." : "No warning events in the selected window.");
}

function sortBy(key) {
  ascending = sortKey === key ? !ascending : key === "name";
  sortKey = key;
  for (const [column, id] of [["name", "name"], ["restarts", "restart"]]) {
    const heading = byId(id + "-heading");
    const marker = heading.querySelector("span");
    heading.removeAttribute("aria-sort");
    marker.textContent = "";
    if (column === key) {
      heading.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      marker.textContent = ascending ? "↑" : "↓";
    }
  }
  renderPods();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runAnalysis();
});
form.addEventListener("input", pending);
source.addEventListener("change", () => {
  setSourceFields();
  loadNamespaces();
});
fixture.addEventListener("change", updateFixtureSuggestions);
byId("reset-analysis").addEventListener("click", () => {
  form.reset();
  setSourceFields();
  loadNamespaces();
  byId("pod-search").value = "";
  byId("pod-filter").value = "all";
  byId("event-search").value = "";
  runAnalysis();
});
byId("pod-search").addEventListener("input", renderPods);
byId("pod-filter").addEventListener("change", renderPods);
byId("event-search").addEventListener("input", renderEvents);
byId("sort-name").addEventListener("click", () => sortBy("name"));
byId("sort-restarts").addEventListener("click", () => sortBy("restarts"));
byId("copy-command").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(byId("command").textContent);
    set("copy-feedback", "Command copied.");
  } catch {
    set("copy-feedback", "Clipboard unavailable. Select the command to copy it.");
  }
});
byId("export-report").addEventListener("click", () => {
  const payload = JSON.stringify(displayed.data, null, 2) + "\n";
  const url = URL.createObjectURL(new Blob([payload], {type: "application/json"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = "namespace-health.json";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
});
loadNamespaces();
runAnalysis();
