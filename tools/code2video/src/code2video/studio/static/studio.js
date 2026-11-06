const $ = (id) => document.getElementById(id);
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
  fill("fps", (config.fpsOptions || [24, 30, 60]).map(String), String(config.defaultFps || 60));
  const workerOpts = Array.from({ length: config.maxWorkers || 4 }, (_, i) => String(i + 1));
  fill("workers", workerOpts, String(config.workers || 3));
  $("workers").addEventListener("change", async (e) => {
    const body = new FormData();
    body.append("workers", e.target.value);
    await fetch("/api/settings", { method: "POST", body });
    $("status").textContent = `Chạy song song: ${e.target.value} luồng.`;
  });
  $("env").innerHTML =
    `<span>HyperFrames <b>${config.hyperframesReady ? "sẵn sàng" : "thiếu node/npx/ffprobe"}</b></span>` +
    `<span>Whiteboard <b>${config.whiteboardReady ? "sẵn sàng" : "chưa cấu hình"}</b></span>`;
  $("renderer").addEventListener("change", applyMode);
  $("voTtsMode").addEventListener("change", () => renderSpeakers(currentSpeakers));
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
      $("mode").value = tab.dataset.mode;
      applyMode();
    });
  });
  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((b) => b.classList.toggle("is-active", b === btn));
      $("runMode").value = btn.dataset.run;
      updateHints();
    });
  });
  $("compScript").addEventListener("change", onScriptInput);
  $("addScene").addEventListener("click", () => addWhiteboardScene());
  $("wbPreview").addEventListener("click", previewFirstScene);
  $("wbBrowse").addEventListener("click", () => {
    const explorer = $("fsExplorer");
    explorer.hidden = !explorer.hidden;
    if (!explorer.hidden) browseFs($("wbLocalFolder").value.trim());
  });
  $("fsUp").addEventListener("click", () => browseFs(fsState.parent));
  $("fsPick").addEventListener("click", () => {
    if (!fsState.path) { $("status").textContent = "Vào một thư mục rồi chọn."; return; }
    $("wbLocalFolder").value = fsState.path;
    $("fsExplorer").hidden = true;
    $("status").textContent = `Đã chọn folder: ${fsState.path}`;
  });
  $("wbFolder").addEventListener("change", onWhiteboardFolder);
  document.querySelectorAll(".wtab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".wtab").forEach((b) => b.classList.toggle("is-active", b === btn));
      $("wbTab").value = btn.dataset.wbtab;
      document.querySelectorAll("[data-wbpanel]").forEach((p) => { p.hidden = p.dataset.wbpanel !== btn.dataset.wbtab; });
    });
  });
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
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab.dataset.mode === mode));
  }
  $("mode").value = mode;
  document.querySelector(".tabs").hidden = whiteboard;
  document.querySelector(".runmode").hidden = whiteboard;
  document.querySelectorAll(".mode-panel").forEach((p) => { p.hidden = p.dataset.panel !== (whiteboard ? "whiteboard" : mode); });
  $("standaloneScriptInput").hidden = whiteboard;
  $("uploadNote").innerHTML = whiteboard
    ? 'Mỗi folder là một cảnh: một ảnh <b>PNG</b>, annotation cùng tên và một file <b>script.srt</b>. Render xong nhiều cảnh thì chọn chúng trong hàng đợi và bấm Ghép cảnh.'
    : 'Chọn folder chứa <b>index.html</b> + <b>assets/</b> + <b>script.srt</b>. App render thẳng.';
  $("run").textContent = whiteboard ? "Render các scene" : RUN_LABEL[mode] || "Chạy";
  updateHints();
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
  fd.append("language", $("language").value);
  fd.append("format", $("format").value);
  fd.append("formatMode", $("formatMode").value);

  if (mode === "whiteboard-scenes") {
    if ($("wbTab").value === "folder") {
      const localPath = $("wbLocalFolder").value.trim();
      if (localPath) {
        fd.set("mode", "whiteboard-folder");
        fd.append("localFolder", localPath);
        appendVoice(fd);
        return fd;
      }
      const folderFiles = [...$("wbFolder").files];
      if (!folderFiles.length) {
        $("status").textContent = "Chọn folder tải lên hoặc nhập đường dẫn folder trên máy.";
        return null;
      }
      fd.set("mode", "whiteboard-folder");
      for (const f of folderFiles) fd.append("files", f, f.webkitRelativePath || f.name);
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
  $("run").disabled = true;
  $("status").textContent = "Đang gửi job...";
  try {
    const res = await fetch("/api/jobs", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    const ids = data.jobIds || (data.jobId ? [data.jobId] : []);
    if (!ids.length) throw new Error("Không nhận được job.");
    follow(ids[0]);
    if (ids.length > 1) $("status").textContent = `Đã thêm ${ids.length} job vào hàng đợi.`;
    refreshQueue();
  } catch (err) {
    $("status").textContent = "Lỗi: " + err.message;
  } finally {
    $("run").disabled = false;
  }
}

async function submitJob() {
  const form = buildForm();
  if (!form) return;
  await sendForm(form);
}

let fsState = { path: "", parent: null };

async function browseFs(path) {
  const res = await fetch("/api/fs/browse?path=" + encodeURIComponent(path || ""));
  if (!res.ok) {
    $("status").textContent = "Lỗi: " + ((await res.json()).detail || res.statusText);
    return;
  }
  const data = await res.json();
  fsState = { path: data.path, parent: data.parent };
  $("fsPath").textContent = data.path || "(chọn ổ đĩa)";
  $("fsDirs").innerHTML = data.dirs.map((d) => {
    const name = d.split(/[\\/]/).filter(Boolean).pop();
    return `<button class="ghost fs-dir" data-path="${d}" type="button">📁 ${name}</button>`;
  }).join("");
  document.querySelectorAll(".fs-dir").forEach((b) =>
    b.addEventListener("click", () => browseFs(b.dataset.path)));
  $("fsUp").disabled = data.parent === null;
}

function previewFirstScene() {  const entry = $("whiteboardScenes").children[0];
  if (!entry) { $("status").textContent = "Thêm ít nhất một scene."; return; }
  const image = entry.querySelector("[data-scene-image]").files[0];
  const annotation = entry.querySelector("[data-scene-annotation]").files[0];
  if (!image || !annotation) {
    $("status").textContent = "Scene đầu tiên cần đủ PNG + annotation để xem trước.";
    return;
  }
  const fd = new FormData();
  fd.append("mode", "preview-whiteboard");
  fd.append("renderer", "whiteboard");
  fd.append("sceneImages", image, image.name);
  fd.append("sceneAnnotations", annotation, annotation.name);
  sendForm(fd);
}

function follow(jobId) {
  if (source) source.close();
  following = jobId;
  $("barFill").style.width = "0%";
  $("progPct").textContent = "0%";
  $("status").textContent = "Đang theo dõi job " + jobId + "...";
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
    renderResult(d);
    source.close();
    refreshQueue();
  });
  source.addEventListener("error", (e) => {
    let msg = "Job lỗi hoặc mất kết nối.";
    try { msg = JSON.parse(e.data).message; } catch (_) {}
    $("status").textContent = "Lỗi: " + msg;
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
  window.location.assign(`/api/whiteboard/download?jobIds=${encodeURIComponent(JSON.stringify(ids))}`);
}

async function clearHistory() {
  if (source) { source.close(); source = null; }
  following = null;
  selectedScenes.clear();
  await fetch("/api/jobs", { method: "DELETE" });
  $("barFill").style.width = "0%";
  $("progPct").textContent = "0%";
  $("status").textContent = "Đã xóa lịch sử.";
  $("summary").innerHTML = "";
  $("links").innerHTML = "";
  const audio = $("audioOut"); audio.hidden = true; audio.removeAttribute("src");
  const video = $("videoOut"); video.hidden = true; video.removeAttribute("src");
  refreshQueue();
}

init();
