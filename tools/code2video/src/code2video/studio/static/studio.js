const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let config = null;
let following = null;
let source = null;
let currentSpeakers = [];
let selectedScenes = new Set();

const EYE = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>`;

async function init() {
  config = await (await fetch("/api/config")).json();
  fill("voTtsMode", config.ttsModes, "v3turbo");
  const langs = config.languages || [{ code: "vi", label: "Tiếng Việt" }];
  $("language").innerHTML = langs.map((l) => `<option value="${l.code}">${l.label}</option>`).join("");
  $("language").value = config.defaultLanguage || "vi";
  $("language").addEventListener("change", () => { syncVoiceMode(); renderSpeakers(currentSpeakers); });
  const fmts = config.formats || [];
  $("format").innerHTML = fmts.map((f) => `<option value="${f.code}">${f.label}</option>`).join("");
  $("format").value = config.defaultFormat || "16:9";
  syncVoiceMode();
  fill("fps", (config.fpsOptions || [24, 30, 48, 60, 120]).map(String), String(config.defaultFps || 60));
  const workerOpts = Array.from({ length: config.maxWorkers || 4 }, (_, i) => String(i + 1));
  fill("workers", workerOpts, String(config.workers || 3));
  $("workers").addEventListener("change", async (e) => {
    const body = new FormData();
    body.append("workers", e.target.value);
    await fetch("/api/settings", { method: "POST", body });
    $("status").textContent = `Chạy song song: ${e.target.value} luồng.`;
  });
  renderEnvPills();
  $("renderer").addEventListener("change", applyMode);
  $("voTtsMode").addEventListener("change", () => renderSpeakers(currentSpeakers));
  document.querySelectorAll(".nav-item").forEach((btn) => btn.addEventListener("click", () => setNav(btn.dataset.nav)));
  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((b) => b.classList.toggle("is-active", b === btn));
      $("runMode").value = btn.dataset.run;
      updateHints();
    });
  });
  $("compScript").addEventListener("change", onScriptInput);
  $("addScene").addEventListener("click", () => addWhiteboardScene());
  $("wbFolder").addEventListener("change", onWhiteboardFolder);
  $("projectFiles").addEventListener("change", onFolderInput);
  $("run").addEventListener("click", submitJob);
  $("mergeScenes").addEventListener("click", mergeScenes);
  $("downloadScenes").addEventListener("click", downloadScenes);
  $("clear").addEventListener("click", clearHistory);
  applyMode();
  addWhiteboardScene();
  renderSpeakers([]);
  refreshQueue();
  setInterval(refreshQueue, 4000);
}

const RUN_LABEL = { files: "Render composition", upload: "Render folder" };

function applyMode() {
  let mode = $("mode").value;
  const whiteboard = $("renderer").value === "whiteboard";
  if (whiteboard) {
    mode = "whiteboard-scenes";
  } else if (mode === "whiteboard-scenes") {
    mode = "upload";
  }
  $("mode").value = mode;
  document.querySelector(".runmode").hidden = whiteboard;
  document.querySelectorAll(".mode-panel").forEach((p) => { p.hidden = p.dataset.panel !== (whiteboard ? "whiteboard" : mode); });
  $("standaloneScriptInput").hidden = whiteboard;
  document.querySelectorAll("#commonBar [data-engine]").forEach((el) => { el.hidden = el.dataset.engine !== $("renderer").value; });
  $("uploadNote").innerHTML = whiteboard
    ? 'Mỗi folder là một cảnh: một ảnh <b>PNG</b>, annotation cùng tên và một file <b>script.srt</b>. Render xong nhiều cảnh thì chọn chúng trong hàng đợi và bấm Ghép cảnh.'
    : 'Chọn folder chứa <b>index.html</b> + <b>assets/</b> + <b>script.srt</b>. App render thẳng.';
  $("run").textContent = whiteboard ? "Render các scene" : RUN_LABEL[mode] || "Chạy";
  syncNav();
  updateHints();
}

// ── Sidebar điều hướng: engine + chức năng + Workflow/Settings ──
const NAV_STATE = {
  "hf-files": { renderer: "hyperframes", mode: "files" },
  "hf-folder": { renderer: "hyperframes", mode: "upload" },
  "wb-folder": { renderer: "whiteboard", wb: "folder" },
  "wb-manual": { renderer: "whiteboard", wb: "manual" },
  "wb-ai": { renderer: "whiteboard", wb: "ai" },
};
let currentView = "studio";

function setView(view) {
  currentView = view;
  $("studioView").hidden = view !== "studio";
  $("workflowView").hidden = view !== "workflow";
  $("settingsView").hidden = view !== "settings";
  if (view === "studio") applyMode(); else syncNav();
  document.dispatchEvent(new CustomEvent("viewchange", { detail: view }));
}

function setNav(key) {
  const target = NAV_STATE[key];
  if (!target) { setView(key); return; }
  $("renderer").value = target.renderer;
  if (target.mode) $("mode").value = target.mode;
  if (target.wb) $("wbTab").value = target.wb;
  setView("studio");
}

function syncNav() {
  const engine = $("renderer").value;
  document.querySelectorAll("#nav [data-engine]").forEach((el) => { el.hidden = el.dataset.engine !== engine; });
  const key = currentView !== "studio"
    ? currentView
    : engine === "whiteboard" ? "wb-" + $("wbTab").value : $("mode").value === "upload" ? "hf-folder" : "hf-files";
  document.querySelectorAll(".nav-item").forEach((btn) => {
    const active = btn.dataset.nav === key;
    btn.classList.toggle("is-active", active);
    if (active) btn.setAttribute("aria-current", "page"); else btn.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-wbpanel]").forEach((p) => { p.hidden = p.dataset.wbpanel !== $("wbTab").value; });
  $("commonBar").hidden = currentView !== "studio";
}

function updateHints() {
  const mode = $("mode").value;
  const batch = $("runMode").value === "batch";
  const whiteboard = $("renderer").value === "whiteboard";
  $("runhint").textContent = whiteboard
    ? (config.whiteboardReady ? "Mỗi scene thành một job riêng. Chọn các scene đã xong trong hàng đợi để ghép." : "Cấu hình WHITEBOARD_ROOT trỏ tới repo srt-whiteboard-animation trên server.")
    : mode === "upload"
      ? (batch ? "Batch: folder chứa nhiều project (nhiều index.html) → mỗi project một video." : "Queue: folder phải chứa đúng một project.")
      : "Render composition từ file tải lên."
  ;
}

function addWhiteboardScene() {
  const entry = document.createElement("div");
  entry.className = "whiteboard-scene-input";
  entry.innerHTML = `
    <div class="scene-input-head"><strong>Scene ${$("whiteboardScenes").children.length + 1}</strong><button class="ghost remove-scene" type="button">Xóa scene</button></div>
    <label class="file"><span>Script / SRT</span><input data-scene-script type="file" accept=".srt,.txt"></label>
    <div class="two">
      <label class="file"><span>Ảnh cảnh (PNG)</span><input data-scene-image type="file" accept=".png,image/png"></label>
      <label class="file"><span>Annotation JSON</span><input data-scene-annotation type="file" accept=".json,application/json"></label>
    </div>`;
  entry.querySelector(".remove-scene").addEventListener("click", () => {
    if ($("whiteboardScenes").children.length === 1) return;
    entry.remove();
    [...$("whiteboardScenes").children].forEach((scene, index) => {
      scene.querySelector(".scene-input-head strong").textContent = `Scene ${index + 1}`;
    });
    updateWhiteboardSpeakers();
  });
  entry.querySelector("[data-scene-script]").addEventListener("change", updateWhiteboardSpeakers);
  $("whiteboardScenes").appendChild(entry);
}

async function updateWhiteboardSpeakers() {
  const names = [];
  for (const input of document.querySelectorAll("[data-scene-script]")) {
    const file = input.files[0];
    if (!file) continue;
    for (const name of detectSpeakers(await readText(file))) if (!names.includes(name)) names.push(name);
  }
  renderSpeakers(names);
}

function relPath(file) {
  return (file.webkitRelativePath || file.name).replace(/\\/g, "/");
}

async function onWhiteboardFolder() {
  const files = [...$("wbFolder").files];
  const box = $("wbDetected");
  box.innerHTML = "";
  if (!files.length) { renderSpeakers([]); return; }
  const byPath = new Map(files.map((f) => [relPath(f), f]));
  const annotations = files.filter((f) => /\.annotation\.json$/i.test(relPath(f)));
  const scenes = [];
  for (const ann of annotations) {
    const rel = relPath(ann);
    const dir = rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "";
    const stem = ann.name.replace(/\.annotation\.json$/i, "");
    const png = byPath.get((dir ? dir + "/" : "") + stem + ".png");
    const prefix = dir ? dir + "/" : "";
    const scriptRel = files.map(relPath).find((r) => r.startsWith(prefix) && /\.(srt|txt)$/i.test(r));
    const script = scriptRel ? byPath.get(scriptRel) : null;
    scenes.push({ dir, stem, png, annotation: ann, script });
  }
  const names = [];
  for (const s of scenes) {
    const ok = s.png && s.script;
    const row = document.createElement("div");
    row.className = "wb-detected-row";
    row.innerHTML = `<div class="scene-input-head"><strong>${s.dir ? s.dir.split("/").pop() : s.stem}</strong>` +
      `<span class="tag ${ok ? "done" : "error"}">${ok ? "đủ file" : "thiếu file"}</span></div>` +
      `<div class="wb-files">PNG ${s.png ? "✓" : "✗"} · annotation ✓ · script ${s.script ? "✓" : "✗"}</div>`;
    box.appendChild(row);
    if (s.script) {
      for (const name of detectSpeakers(await readText(s.script))) if (!names.includes(name)) names.push(name);
    }
  }
  renderSpeakers(names);
}

function fill(id, values, selected) {
  const el = $(id);
  el.innerHTML = values.map((v) => `<option ${v === selected ? "selected" : ""}>${v}</option>`).join("");
}

function voiceList() {
  const lang = ($("language") && $("language").value) || "vi";
  if (lang !== "vi") {
    const list = (config.edgeVoices && config.edgeVoices[lang]) || [];
    return list.map((v) => ({ value: v.id, label: v.label }));
  }
  const names = config.voicePresets[$("voTtsMode").value] || config.voicePresets.v3turbo;
  return names.map((n) => ({ value: n, label: n }));
}

function syncVoiceMode() {
  const edge = (($("language") && $("language").value) || "vi") !== "vi";
  const el = $("voTtsMode");
  if (!el) return;
  el.disabled = edge;
  const label = el.closest("label");
  if (label) label.style.opacity = edge ? ".45" : "1";
}

function detectSpeakers(text) {
  const blocks = text.split(/\r?\n\s*\r?\n/).map((b) => b.trim()).filter(Boolean);
  const names = [];
  const re = /^\[([^\]]+)\]\s*\[[^\]]+\]\s*:/;
  for (const block of blocks) {
    const m = block.match(re);
    if (m && !names.includes(m[1])) names.push(m[1]);
  }
  return names; // [] => single speaker
}

function renderSpeakers(names) {
  currentSpeakers = names;
  const box = $("speakers");
  box.innerHTML = "";
  const list = voiceList();
  const defaultVoice = list.some((o) => o.value === config.defaultVoice) ? config.defaultVoice : (list[0] && list[0].value);
  const rows = names.length ? names : [""];
  rows.forEach((name) => {
    const row = document.createElement("label");
    row.className = "field speaker-row";
    const label = name || "Giọng đọc (1 nhân vật)";
    row.innerHTML = `<span class="lbl"><span class="avatar">${name ? name.slice(0, 1).toUpperCase() : "◎"}</span>${label}</span>`;
    const sel = document.createElement("select");
    sel.dataset.speaker = name;
    list.forEach((item) => { const opt = document.createElement("option"); opt.value = item.value; opt.textContent = item.label; if (item.value === defaultVoice) opt.selected = true; sel.appendChild(opt); });
    row.appendChild(sel);
    box.appendChild(row);
  });
  $("scriptHint").textContent = names.length
    ? `Phát hiện ${names.length} nhân vật — gán giọng cho từng người.`
    : "1 nhân vật (1 giọng). Nhiều nhân vật: [Tên][start --> end]: lời, cách nhau dòng trống.";
}

async function readText(file) {
  return await file.text();
}

async function onScriptInput() {
  const file = $("compScript").files[0];
  if (!file) { renderSpeakers([]); return; }
  const names = detectSpeakers(await readText(file));
  renderSpeakers(names);
}

async function onFolderInput() {
  const files = [...$("projectFiles").files];
  const box = $("hfDetected");
  box.innerHTML = "";
  const names = [];
  if (!files.length) { renderSpeakers([]); return; }

  const indexFiles = files.filter((f) => /(^|\/)index\.html$/i.test(relPath(f)));
  if (!indexFiles.length) {
    const row = document.createElement("div");
    row.className = "wb-detected-row";
    row.innerHTML = `<div class="scene-input-head"><strong>Không thấy project</strong><span class="tag error">thiếu index.html</span></div>` +
      `<div class="wb-files">Mode Folder cần index.html + assets/ + script.</div>`;
    box.appendChild(row);
    const anyScript = files.find((f) => /\.(srt|txt)$/i.test(f.name));
    renderSpeakers(anyScript ? detectSpeakers(await readText(anyScript)) : []);
    return;
  }

  const dirs = [...new Set(indexFiles.map((f) => {
    const rel = relPath(f);
    return rel.includes("/") ? rel.slice(0, rel.lastIndexOf("/")) : "";
  }))];
  for (const dir of dirs) {
    const prefix = dir ? dir + "/" : "";
    const directChild = (f) => {
      const rest = relPath(f).slice(prefix.length);
      return relPath(f).startsWith(prefix) && !rest.includes("/");
    };
    const scripts = files.filter((f) => directChild(f) && /\.(srt|txt)$/i.test(f.name));
    const script = scripts.find((f) => /script/i.test(f.name)) || scripts[0];
    const assets = files.filter((f) => relPath(f).startsWith(prefix) && /\.(svg|png|jpe?g|webp|gif)$/i.test(f.name)).length;
    const label = dir ? dir.split("/").pop() : "project";
    const ok = !!script;
    const row = document.createElement("div");
    row.className = "wb-detected-row";
    row.innerHTML = `<div class="scene-input-head"><strong>${label}</strong><span class="tag ${ok ? "done" : "error"}">${ok ? "đủ" : "thiếu script"}</span></div>` +
      `<div class="wb-files">index.html ✓ · assets ${assets} · script ${ok ? "✓" : "✗"}</div>`;
    box.appendChild(row);
    if (script) {
      for (const name of detectSpeakers(await readText(script))) if (!names.includes(name)) names.push(name);
    }
  }
  renderSpeakers(names);
}

function speakersJson() {
  const map = {};
  document.querySelectorAll("#speakers select[data-speaker]").forEach((sel) => { map[sel.dataset.speaker] = sel.value; });
  return JSON.stringify(map);
}

function appendVoice(fd) {
  fd.append("makeVoiceover", "true");
  fd.append("voTtsMode", $("voTtsMode").value);
  fd.append("voDry", $("voDry").checked);
  fd.append("speakers", speakersJson());
  const ref = $("voRef").files[0];
  if (ref) fd.append("voRef", ref);
}

function buildForm() {
  const mode = $("mode").value;
  const fd = new FormData();
  fd.append("mode", mode);
  fd.append("renderer", $("renderer").value);
  fd.append("runMode", $("runMode").value);
  fd.append("fps", $("fps").value);
  fd.append("hfQuality", $("hfQuality").value);
  fd.append("wbLongEdge", $("wbLongEdge").value);
  fd.append("language", $("language").value);
  fd.append("format", $("format").value);
  fd.append("formatMode", $("formatMode").value);

  if (mode === "whiteboard-scenes") {
    if ($("wbTab").value === "folder") {
      const folderFiles = [...$("wbFolder").files];
      if (!folderFiles.length) { $("status").textContent = "Chọn folder các scene."; return null; }
      fd.set("mode", "whiteboard-folder");
      for (const f of folderFiles) fd.append("files", f, f.webkitRelativePath || f.name);
      fd.append("autoMerge", $("wbAutoMerge").checked);
      appendVoice(fd);
      return fd;
    }
    const entries = [...$("whiteboardScenes").children];
    if (!entries.length) { $("status").textContent = "Thêm ít nhất một scene."; return null; }
    for (const [index, entry] of entries.entries()) {
      const script = entry.querySelector("[data-scene-script]").files[0];
      const image = entry.querySelector("[data-scene-image]").files[0];
      const annotation = entry.querySelector("[data-scene-annotation]").files[0];
      if (!script || !image || !annotation) {
        $("status").textContent = `Scene ${index + 1} cần đủ script, ảnh PNG và annotation JSON.`;
        return null;
      }
      fd.append("sceneScripts", script, script.name);
      fd.append("sceneImages", image, image.name);
      fd.append("sceneAnnotations", annotation, annotation.name);
    }
    appendVoice(fd);
    return fd;
  }

  if (mode === "files") {
    const html = $("htmlFile").files[0];
    if (!html) { $("status").textContent = "Cần chọn index.html."; return null; }
    fd.append("htmlFile", html);
    for (const a of $("assetFiles").files) fd.append("assetFiles", a, a.name);
    for (const a of $("assetDir").files) fd.append("assetFiles", a, a.webkitRelativePath || a.name);
    const script = $("compScript").files[0];
    if (script) fd.append("compScript", script);
  } else {
    const picked = $("projectFiles").files;
    if (!picked.length) { $("status").textContent = "Chưa chọn folder nào."; return null; }
    for (const f of picked) fd.append("files", f, f.webkitRelativePath || f.name);
  }
  appendVoice(fd);
  return fd;
}

async function sendForm(form) {
  return withBusy([$("run"), $("aiRender")], () => sendFormInner(form));
}

async function sendFormInner(form) {
  $("status").textContent = "Đang gửi job...";
  try {
    const res = await fetch("/api/jobs", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    const ids = data.jobIds || (data.jobId ? [data.jobId] : []);
    if (!ids.length) throw new Error("Không nhận được job.");
    follow(ids[0]);
    if (ids.length > 1) $("status").textContent = `Đã thêm ${ids.length} job vào hàng đợi.`;
    toast(ids.length > 1 ? `Đã thêm ${ids.length} job vào hàng đợi.` : "Đã gửi job, đang xử lý...", "info");
    refreshQueue();
  } catch (err) {
    $("status").textContent = "Lỗi: " + err.message;
    toast("Không gửi được job: " + err.message, "error");
  }
}

async function submitJob() {
  const aiTab = $("renderer").value === "whiteboard" && $("wbTab").value === "ai";
  const form = aiTab ? aiBuildForm() : buildForm();
  if (!form) return;
  await sendForm(form);
}

function follow(jobId) {
  if (source) source.close();
  following = jobId;
  $("barFill").style.width = "0%";
  $("progPct").textContent = "0%";
  $("status").textContent = "Đang theo dõi job " + jobId + "...";
  setRunning($("status"), true);
  source = new EventSource(`/api/jobs/${jobId}/events`);
  source.addEventListener("stage", (e) => {
    const d = JSON.parse(e.data);
    const pct = Math.round(d.progress * 100);
    $("barFill").style.width = pct + "%";
    $("progPct").textContent = pct + "%";
    const pos = d.queuePosition > 0 ? ` (còn ${d.queuePosition} job trước)` : "";
    $("status").textContent = `${d.label}${pos}`;
    refreshQueue();
  });
  source.addEventListener("done", (e) => {
    const d = JSON.parse(e.data);
    $("barFill").style.width = "100%";
    $("progPct").textContent = "100%";
    $("status").textContent = "Hoàn tất.";
    setRunning($("status"), false);
    toast("Hoàn tất. Video đã sẵn sàng ở phần Kết quả.", "success");
    renderResult(d);
    source.close();
    refreshQueue();
  });
  source.addEventListener("error", (e) => {
    let msg = "Job lỗi hoặc mất kết nối.";
    try { msg = JSON.parse(e.data).message; } catch (_) {}
    $("status").textContent = "Lỗi: " + msg;
    setRunning($("status"), false);
    toast("Job lỗi: " + msg, "error");
    source.close();
    refreshQueue();
  });
}

const artUrl = (id, kind) => `/api/jobs/${id}/artifacts/${kind}`;

function renderResult(d) {
  const id = d.jobId;
  if (d.durationMs != null) {
    $("summary").innerHTML =
      `Thời lượng <code>${(d.durationMs / 1000).toFixed(2)}s</code> · Cue <code>${d.cueCount}</code> · Scene <code>${d.sceneCount}</code>`;
  } else if (d.renderer === "whiteboard-merge") {
    $("summary").innerHTML = `Đã ghép các cảnh Whiteboard thành <code>output.mp4</code>`;
  } else if (d.renderer === "whiteboard") {
    $("summary").innerHTML = `Đã render cảnh <code>${d.sceneName || "Whiteboard"}</code>; chọn cảnh trong hàng đợi để ghép video.`;
  } else {
    $("summary").innerHTML = `Đã render composition từ <code>${d.outputDir}</code>`;
  }
  const audio = $("audioOut");
  if (d.audio) { audio.src = artUrl(id, "audio"); audio.hidden = false; } else { audio.hidden = true; audio.removeAttribute("src"); }
  const video = $("videoOut");
  if (d.video) { video.src = artUrl(id, "video"); video.hidden = false; } else { video.hidden = true; video.removeAttribute("src"); }
  const links = [];
  if (d.audio) links.push(`<a href="${artUrl(id, "audio")}" download>Voiceover WAV</a>`);
  if (d.timeline) links.push(`<a href="${artUrl(id, "timeline")}" download>timeline.json</a>`);
  if (d.composition) links.push(`<a href="${artUrl(id, "composition")}" download>index.html</a>`);
  if (d.video) links.push(`<a href="${artUrl(id, "video")}" download>output.mp4</a>`);
  $("links").innerHTML = links.join("");
}

async function refreshQueue() {
  const jobs = await (await fetch("/api/jobs")).json();
  const ul = $("queue");
  ul.innerHTML = "";
  $("queueCount").textContent = jobs.length;
  jobs.slice().reverse().forEach((j) => {
    const li = document.createElement("li");
    if (j.jobId === following) li.classList.add("is-active");
    const label = j.status === "error" ? "lỗi" :
      j.status === "queued" ? `#${j.queuePosition + 1}` :
      j.status === "running" ? `${Math.round(j.progress * 100)}%` : "xong";
    const isScene = j.status === "done" && j.result?.renderer === "whiteboard";
    const sceneName = isScene ? (j.result.sceneName || "Whiteboard scene") : j.jobId;
    li.innerHTML = `${isScene ? `<input class="scene-select" type="checkbox" aria-label="Chọn cảnh ${sceneName}" ${selectedScenes.has(j.jobId) ? "checked" : ""}>` : ""}<span class="job-name">${sceneName}</span><span class="tag ${j.status}">${label}</span>`;
    const checkbox = li.querySelector(".scene-select");
    if (checkbox) checkbox.addEventListener("click", (event) => event.stopPropagation());
    if (checkbox) checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedScenes.add(j.jobId);
      else selectedScenes.delete(j.jobId);
      updateMergeButton();
    });
    li.addEventListener("click", () => follow(j.jobId));
    ul.appendChild(li);
  });
  const available = new Set(jobs.filter((j) => j.status === "done" && j.result?.renderer === "whiteboard").map((j) => j.jobId));
  selectedScenes = new Set([...selectedScenes].filter((id) => available.has(id)));
  updateMergeButton();
}

function updateMergeButton() {
  const count = selectedScenes.size;
  $("mergeScenes").disabled = count < 2;
  $("mergeScenes").hidden = count === 0;
  $("mergeScenes").textContent = `Ghép cảnh (${count})`;
  const download = $("downloadScenes");
  if (download) {
    download.disabled = count < 1;
    download.hidden = count === 0;
    download.textContent = `Tải scene (zip) (${count})`;
  }
}

async function mergeScenes() {
  return withBusy($("mergeScenes"), mergeScenesInner);
}

async function mergeScenesInner() {
  const jobs = await (await fetch("/api/jobs")).json();
  const sceneJobIds = jobs
    .filter((job) => selectedScenes.has(job.jobId) && job.status === "done" && job.result?.renderer === "whiteboard")
    .sort((a, b) => a.created - b.created)
    .map((job) => job.jobId);
  if (sceneJobIds.length < 2) return;
  const form = new FormData();
  form.append("sceneJobIds", JSON.stringify(sceneJobIds));
  form.append("format", $("format").value);
  form.append("formatMode", $("formatMode").value);
  $("mergeScenes").disabled = true;
  try {
    const response = await fetch("/api/whiteboard/merge", { method: "POST", body: form });
    if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
    const data = await response.json();
    follow(data.jobId);
    refreshQueue();
  } catch (error) {
    $("status").textContent = "Lỗi ghép cảnh: " + error.message;
    toast("Lỗi ghép cảnh: " + error.message, "error");
    updateMergeButton();
  }
}

async function downloadScenes() {
  const jobs = await (await fetch("/api/jobs")).json();
  const ids = jobs
    .filter((job) => selectedScenes.has(job.jobId) && job.status === "done" && job.result?.renderer === "whiteboard")
    .sort((a, b) => a.created - b.created)
    .map((job) => job.jobId);
  if (!ids.length) return;
  toast("Đang chuẩn bị file zip các scene...", "info");
  window.location.assign(`/api/whiteboard/download?jobIds=${encodeURIComponent(JSON.stringify(ids))}`);
}

async function clearHistory() {
  return withBusy($("clear"), clearHistoryInner);
}

async function clearHistoryInner() {
  if (source) { source.close(); source = null; }
  following = null;
  selectedScenes.clear();
  setRunning($("status"), false);
  await fetch("/api/jobs", { method: "DELETE" });
  $("barFill").style.width = "0%";
  $("progPct").textContent = "0%";
  $("status").textContent = "Đã xóa lịch sử.";
  toast("Đã xóa lịch sử hàng đợi.", "success");
  $("summary").innerHTML = "";
  $("links").innerHTML = "";
  const audio = $("audioOut"); audio.hidden = true; audio.removeAttribute("src");
  const video = $("videoOut"); video.hidden = true; video.removeAttribute("src");
  refreshQueue();
}

// ── AI Kịch bản ──
let aiState = { providers: [], skills: [], doodles: [], defaultProvider: "", defaultSkill: "" };

async function loadAiSettings() {
  setLoading($("settingsView"), true);
  try { await loadAiSettingsInner(); } finally { setLoading($("settingsView"), false); }
}

function renderEnvPills() {
  $("env").innerHTML =
    `<span>HyperFrames <b>${config.hyperframesReady ? "sẵn sàng" : "thiếu node/npx/ffprobe"}</b></span>` +
    `<span>Whiteboard <b>${config.whiteboardReady ? "sẵn sàng" : "chưa cấu hình"}</b></span>`;
}

async function loadTools() {
  const res = await fetch("/api/tools");
  if (!res.ok) return;
  const t = await res.json();
  $("toolRoot").value = t.values.WHITEBOARD_ROOT || "";
  $("toolPython").value = t.values.WHITEBOARD_PYTHON || "";
  const status = $("toolStatus"), bad = Object.entries(t.problems);
  status.hidden = false;
  status.className = "ai-status " + (!bad.length && t.whiteboardReady ? "is-ok" : "is-error");
  status.textContent = bad.length ? "✗ " + bad.map(([k, v]) => `${k}: ${v}`).join(" · ")
    : t.whiteboardReady ? "✓ Whiteboard sẵn sàng." : "Chưa cấu hình Whiteboard: nhập thư mục srt-whiteboard-animation.";
  $("toolBadges").innerHTML = Object.entries(t.tools).map(([name, path]) =>
    `<span class="tag" title="${esc(path || "không tìm thấy trong PATH")}">${path ? "✓" : "✗"} ${esc(name)}</span>`).join(" ");
}

async function saveTools() {
  const res = await fetch("/api/tools", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ WHITEBOARD_ROOT: $("toolRoot").value, WHITEBOARD_PYTHON: $("toolPython").value }) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { toast("Không lưu được đường dẫn: " + (data.detail || res.statusText), "error"); await loadTools(); return; }
  config = await (await fetch("/api/config")).json();
  renderEnvPills();
  await loadTools();
  toast(data.whiteboardReady ? "Đã lưu đường dẫn, Whiteboard sẵn sàng." : "Đã lưu đường dẫn.", "success");
}

async function loadAiSettingsInner() {
  const res = await fetch("/api/ai/settings");
  if (!res.ok) throw new Error("Không đọc được ai settings");
  aiState = await res.json();
  $("aiProvider").innerHTML = `<option value="">— chọn provider —</option><option value="demo">Demo (offline, không cần key)</option>` +
    aiState.providers.map((p) => `<option value="${esc(p.id)}">${esc(p.label)}</option>`).join("");
  const dp = aiState.providers.find((p) => p.id === aiState.defaultProvider);
  $("aiProvider").value = dp && dp.hasKey && dp.model ? dp.id : (aiState.defaultProvider === "demo" ? "demo" : "");  // không tự chọn provider chưa cấu hình
  $("aiSkill").innerHTML = aiState.skills.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
  $("aiSkill").value = aiState.defaultSkill || "";
  renderAiSettings();
  loadAiFiles();
  loadTools();
}

// Ô model là <select>: lúc đầu chỉ có giá trị đã lưu, sau khi tải danh sách thì chỉ còn model miễn phí để chọn.
function modelSelectHtml(current, models, placeholder) {
  const list = models === null ? [current].filter(Boolean) : models;
  const head = `<option value="">${esc(placeholder)}</option>`;
  const stale = models !== null && current && !models.includes(current)
    ? `<option value="" selected hidden>(model cũ “${esc(current)}” không còn)</option>` : "";
  return head + stale + list.map((m) => `<option value="${esc(m)}" ${m === current ? "selected" : ""}>${esc(m)}</option>`).join("");
}

function readModel(row, cls) {
  return row.querySelector("." + cls).value.trim();
}

function fillModelPickers(row, chat, image) {
  const cur = readModel(row, "ai-model"), curImg = readModel(row, "ai-image-model");
  row.querySelector(".ai-model").innerHTML = modelSelectHtml(cur, chat, "— chọn model miễn phí —");
  const imgSel = row.querySelector(".ai-image-model");
  imgSel.innerHTML = modelSelectHtml(curImg, image, image.length ? "— không dùng ảnh AI —" : "— provider này không có model ảnh —");
  imgSel.disabled = !image.length;
  return { chatStale: !!cur && !chat.includes(cur), imageStale: !!curImg && !image.includes(curImg) };
}

function providerRow(p) {
  const row = document.createElement("div");
  row.className = "provider-row";
  row.dataset.id = p.id;
  row.innerHTML = `
    <input class="ai-id" placeholder="id" value="${esc(p.id)}" aria-label="ID provider">
    <input class="ai-label" placeholder="Tên hiển thị" value="${esc(p.label)}" aria-label="Tên hiển thị">
    <input class="ai-base" placeholder="baseUrl (OpenAI-compatible)" value="${esc(p.baseUrl)}" aria-label="Base URL">
    <label class="ai-field">Model chat (chỉ model miễn phí)
      <select class="ai-model">${modelSelectHtml(p.model, null, "— bấm “Tải danh sách model” rồi chọn —")}</select></label>
    <label class="ai-field">Model tạo ảnh (tùy chọn, thường tính phí; dùng cho bước Hình ảnh)
      <select class="ai-image-model">${modelSelectHtml(p.imageModel || "", null, "— không dùng ảnh AI —")}</select></label>
    <input class="ai-key" type="password" autocomplete="off" aria-label="API key"
      placeholder="${p.hasKey ? "Đã lưu key (ẩn) — để trống để giữ nguyên" : "API key / token"}">
    <div class="ai-actions">
      <button class="ghost ai-fetch" type="button">⟳ Tải danh sách model</button>
      <button class="ghost ai-test" type="button">Kiểm tra kết nối</button>
      <button class="ghost ai-del" type="button">Xóa</button>
    </div>
    <p class="ai-status" role="status" hidden></p>`;
  const body = (extra) => ({
    id: row.querySelector(".ai-id").value.trim(), label: row.querySelector(".ai-label").value,
    baseUrl: row.querySelector(".ai-base").value.trim(), apiKey: row.querySelector(".ai-key").value, ...extra,
  });
  const status = (text, ok) => {
    const el = row.querySelector(".ai-status");
    el.hidden = !text; el.textContent = text || ""; el.className = "ai-status " + (ok ? "is-ok" : "is-error");
  };
  const post = async (url, payload) => {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    return data;
  };
  row.querySelector(".ai-fetch").addEventListener("click", (ev) => withBusy(ev.currentTarget, async () => {
    try {
      status("Đang tải danh sách model miễn phí… (OpenRouter có thể mất đến 1 phút nếu mạng chậm)", true);
      const data = await post("/api/ai/models", body({}));
      const stale = fillModelPickers(row, data.models, data.imageModels || []);
      const notes = [`Đã tải ${data.models.length} model chat miễn phí`];
      notes.push(data.imageModels.length ? `${data.imageModels.length} model ảnh (có thể tính phí)` : "không có model ảnh");
      if (stale.chatStale) notes.push("model chat đã lưu không còn trong danh sách, hãy chọn lại");
      if (stale.imageStale) notes.push("model ảnh đã lưu không còn, hãy chọn lại");
      status(notes.join(" · ") + ". Chọn model rồi bấm Lưu settings.", !stale.chatStale && !stale.imageStale);
      toast(`Đã tải ${data.models.length} model miễn phí từ ${row.querySelector(".ai-label").value || "provider"}.`, "success");
    } catch (e) { status("✗ Không tải được danh sách model: " + e.message, false); toast("Không tải được model: " + e.message, "error"); }
  }));
  row.querySelector(".ai-test").addEventListener("click", (ev) => withBusy(ev.currentTarget, async () => {
    status("Đang gọi thử AI…", true);
    try {
      const r = await post("/api/ai/test", body({ model: readModel(row, "ai-model") }));
      if (r.ok) {
        status(`✓ AI chạy được · ${r.latencyMs} ms · model ${r.model} trả lời: “${r.reply}”`, true);
        toast("Kết nối AI thành công (" + r.latencyMs + " ms).", "success");
      } else { status("✗ " + r.message, false); toast("AI chưa chạy được: " + r.message, "error"); }
    } catch (e) { status("✗ " + e.message, false); toast("Không kiểm tra được: " + e.message, "error"); }
  }));
  row.querySelector(".ai-del").addEventListener("click", () => row.remove());
  return row;
}

function skillRow(s) {
  const row = document.createElement("div");
  row.className = "skill-row";
  row.dataset.id = s.id;
  row.dataset.source = s.source || "";
  row.innerHTML = `
    <input class="ai-skill-id" placeholder="id" value="${esc(s.id)}" aria-label="ID skill">
    <input class="ai-skill-name" placeholder="Tên skill" value="${esc(s.name)}" aria-label="Tên skill">
    <textarea class="ai-skill-content" rows="3" placeholder="Nội dung system prompt">${esc(s.content)}</textarea>
    ${s.source ? `<span class="tag" title="File gốc trong .studio-data/settings/uploads/skills">📎 ${esc(s.source)}</span>` : "<span></span>"}
    <button class="ghost ai-del" type="button">Xóa</button>`;
  row.querySelector(".ai-del").addEventListener("click", () => row.remove());
  return row;
}

function renderAiSettings() {
  $("aiProviders").replaceChildren(...aiState.providers.map(providerRow));
  $("aiSkills").replaceChildren(...aiState.skills.map(skillRow));
}

function refreshSkillSelect() {
  const keep = $("aiSkill").value;
  const rows = [...document.querySelectorAll(".skill-row")];
  $("aiSkill").innerHTML = rows.map((r) =>
    `<option value="${esc(r.querySelector(".ai-skill-id").value)}">${esc(r.querySelector(".ai-skill-name").value)}</option>`).join("");
  $("aiSkill").value = keep;
}

async function saveAiSettings() {
  const providers = [...document.querySelectorAll(".provider-row")].map((row) => ({
    id: row.querySelector(".ai-id").value,
    label: row.querySelector(".ai-label").value,
    baseUrl: row.querySelector(".ai-base").value,
    model: readModel(row, "ai-model"),
    imageModel: readModel(row, "ai-image-model"),
    apiKey: row.querySelector(".ai-key").value,
  }));
  const skills = [...document.querySelectorAll(".skill-row")].map((row) => ({
    id: row.querySelector(".ai-skill-id").value,
    name: row.querySelector(".ai-skill-name").value,
    content: row.querySelector(".ai-skill-content").value,
    source: row.dataset.source || "",
  }));
  const res = await fetch("/api/ai/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      providers, skills,
      defaultProvider: $("aiProvider").value,
      defaultSkill: $("aiSkill").value,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  await loadAiSettings();
}

// ── Tệp đã upload (skill) ──
function fmtSize(bytes) { return bytes < 1024 ? bytes + " B" : (bytes / 1024).toFixed(1) + " KB"; }

async function loadAiFiles() {
  const box = $("aiFiles");
  try {
    const res = await fetch("/api/files");
    if (!res.ok) throw new Error(res.statusText);
    const { files, totalBytes } = await res.json();
    if (!files.length) { box.innerHTML = `<p class="empty-note">Chưa có file nào. Dùng “Tải skill lên” để thêm.</p>`; return; }
    box.innerHTML = `<ul class="file-list">` + files.map((f) => `
      <li data-kind="${esc(f.kind)}" data-name="${esc(f.name)}">
        <span class="file-name">📎 ${esc(f.name)}</span>
        <span class="file-meta">${fmtSize(f.size)} · ${esc(f.modified)}</span>
        <span class="file-use">${f.usedBy.length ? "Skill: " + esc(f.usedBy.join(", ")) : "Không có skill nào dùng"}</span>
        <button class="ghost file-del" type="button">Xóa</button>
      </li>`).join("") + `</ul><p class="empty-note">Tổng ${fmtSize(totalBytes)} · lưu tại <code>.studio-data/settings/uploads/</code> trên máy chạy tool.</p>`;
    box.querySelectorAll(".file-del").forEach((btn) => btn.addEventListener("click", () => deleteUpload(btn)));
  } catch (e) { box.innerHTML = `<p class="empty-note is-error">Không đọc được danh sách file: ${esc(e.message)}</p>`; }
}

function deleteUpload(btn) {
  const li = btn.closest("li"), name = li.dataset.name;
  const using = li.querySelector(".file-use").textContent.startsWith("Skill:");
  const ask = using ? `Xóa file "${name}"? Skill dùng file này cũng sẽ bị gỡ khỏi Settings.` : `Xóa file "${name}"?`;
  if (!confirm(ask)) return;
  withBusy(btn, async () => {
    try {
      const res = await fetch(`/api/files/${li.dataset.kind}/${encodeURIComponent(name)}`, { method: "DELETE" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      document.querySelectorAll(".skill-row").forEach((r) => { if (r.dataset.source === name) r.remove(); });
      aiState.skills = aiState.skills.filter((s) => s.source !== name);
      refreshSkillSelect();
      toast(`Đã xóa ${name}` + (data.removedSkills.length ? ` và gỡ ${data.removedSkills.length} skill.` : "."), "success");
      await loadAiFiles();
    } catch (e) { toast("Không xóa được file: " + e.message, "error"); }
  });
}

async function uploadSkillFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/skills/upload", { method: "POST", body: fd });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}
window.uploadSkillFile = uploadSkillFile;

async function generateScript() {
  return withBusy($("aiGenerate"), generateScriptInner);
}

async function generateScriptInner() {
  $("status").textContent = "AI đang viết kịch bản...";
  toast("AI đang viết kịch bản, có thể mất vài chục giây...", "info", 3500);
  try {
    const res = await fetch("/api/ai/generate-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: $("aiTopic").value,
        language: $("language").value,
        providerId: $("aiProvider").value,
        skillId: $("aiSkill").value,
        minutes: Number($("aiMinutes").value) || 3,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    renderAiReview(data.scenes);
    $("aiRender").hidden = false;
    $("status").textContent = `Kịch bản xong: ${data.scenes.length} scene. Duyệt/sửa rồi bấm "Tạo video".`;
    toast(`AI đã viết xong kịch bản: ${data.scenes.length} scene. Duyệt/sửa rồi bấm "Tạo video từ kịch bản".`, "success");
  } catch (err) {
    $("status").textContent = "Lỗi: " + err.message;
    toast("Không sinh được kịch bản: " + err.message, "error");
  }
}

function doodleOptions(selected) {
  return aiState.doodles.map((d) =>
    `<option value="${esc(d)}" ${d === selected ? "selected" : ""}>${esc(d)}</option>`).join("");
}

function renderAiReview(scenes) {
  $("aiReview").innerHTML = scenes.map((scene) => `
    <div class="ai-scene">
      <input class="ai-scene-title" value="${esc(scene.title)}">
      ${scene.cues.map((cue) => `
        <div class="cue-row">
          <select class="ai-cue-doodle">${doodleOptions(cue.doodle)}</select>
          <input class="ai-cue-label" placeholder="Nhãn dưới hình" value="${esc(cue.label)}">
          <textarea class="ai-cue-text grow" rows="2">${esc(cue.text)}</textarea>
        </div>`).join("")}
    </div>`).join("");
}

function collectAiScenes() {
  return [...document.querySelectorAll(".ai-scene")].map((scene) => ({
    title: scene.querySelector(".ai-scene-title").value,
    cues: [...scene.querySelectorAll(".cue-row")].map((row) => ({
      doodle: row.querySelector(".ai-cue-doodle").value,
      label: row.querySelector(".ai-cue-label").value,
      text: row.querySelector(".ai-cue-text").value,
    })),
  })).filter((s) => s.cues.length);
}

function aiBuildForm() {
  const scenes = collectAiScenes();
  if (!scenes.length) { $("status").textContent = "Chưa có kịch bản để render."; return null; }
  const fd = new FormData();
  fd.append("mode", "ai-script");
  fd.append("renderer", "whiteboard");
  fd.append("fps", $("fps").value);
  fd.append("hfQuality", $("hfQuality").value);
  fd.append("wbLongEdge", $("wbLongEdge").value);
  fd.append("language", $("language").value);
  fd.append("format", $("format").value);
  fd.append("formatMode", $("formatMode").value);
  fd.append("scenes", JSON.stringify(scenes));
  fd.append("makeVoiceover", "true");
  fd.append("voTtsMode", $("voTtsMode").value);
  fd.append("voDry", $("voDry").checked);
  fd.append("speakers", speakersJson());
  fd.append("autoMerge", true);
  const ref = $("voRef").files[0];
  if (ref) fd.append("voRef", ref);
  return fd;
}

function initAi() {
  $("aiGenerate").addEventListener("click", generateScript);
  $("aiRender").addEventListener("click", submitJob);
  $("aiSettingsSave").addEventListener("click", () => withBusy($("aiSettingsSave"), async () => {
    try {
      await saveAiSettings();
      toast("Đã lưu settings AI.", "success");
    } catch (e) {
      toast("Không lưu được settings: " + e.message, "error");
    }
  }));
  $("aiAddProvider").addEventListener("click", () => {
    $("aiProviders").appendChild(providerRow({ id: "custom-" + Date.now().toString(36), label: "", baseUrl: "", model: "", imageModel: "", hasKey: false }));
  });
  $("aiAddSkill").addEventListener("click", () => {
    $("aiSkills").appendChild(skillRow({ id: "skill-" + Date.now().toString(36), name: "", content: "", source: "" }));
  });
  $("toolSave").addEventListener("click", (ev) => withBusy(ev.currentTarget, saveTools));
  $("aiUploadSkill").addEventListener("click", () => $("aiSkillFile").click());
  $("aiSkillFile").addEventListener("change", (ev) => {
    const files = [...ev.target.files];
    ev.target.value = "";
    if (!files.length) return;
    withBusy($("aiUploadSkill"), async () => {
      for (const file of files) {
        try {
          const skill = await uploadSkillFile(file);
          aiState.skills.push(skill);
          $("aiSkills").appendChild(skillRow(skill));
          toast(`Đã tải skill “${skill.name}” lên và lưu local.`, "success");
        } catch (e) { toast(`Không tải được ${file.name}: ${e.message}`, "error"); }
      }
      refreshSkillSelect();
      await loadAiFiles();
    });
  });
  loadAiSettings().catch((e) => { $("status").textContent = "Lỗi settings: " + e.message; toast("Không đọc được settings: " + e.message, "error"); });
}

init();
initAi();
