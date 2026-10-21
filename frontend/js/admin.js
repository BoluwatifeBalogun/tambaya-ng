(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const root = document.documentElement;
  try { root.dataset.theme = JSON.parse(localStorage.getItem("tambaya.theme")) || "light"; } catch { /* ignore */ }

  let token = "";
  try { token = sessionStorage.getItem("tambaya.admin") || ""; } catch { /* ignore */ }
  $("#token").value = token;
  let documents = [];
  let entries = [];

  async function api(path, opts = {}) {
    const res = await fetch(`/api/admin${path}`, { ...opts, headers: { "content-type": "application/json", "x-admin-token": token, ...(opts.headers || {}) } });
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || `Request failed (${res.status})`); }
    return res.json();
  }

  async function loadAll() {
    const [stats, docs] = await Promise.all([api("/stats"), api("/documents")]);
    documents = docs;
    $("#stats").innerHTML = [
      ["entries_total", "Knowledge entries"], ["entries_pending", "Pending review"], ["conversations", "Conversations"],
      ["answers", "Answers given"], ["fallback_rate", "Fallback rate"], ["avg_latency_ms", "Average latency (ms)"],
    ].map(([k, label]) => `<div class="stat"><b>${k === "fallback_rate" ? Math.round(stats[k] * 100) + "%" : stats[k]}</b><span>${label}</span></div>`).join("")
      + `<div class="stat"><b class="langs">${["en", "ha", "yo", "ig"].map((l) => `<span>${esc({ en: "English", ha: "Hausa", yo: "Yorùbá", ig: "Igbo" }[l])} <em>${stats.entries_by_language[l] ?? 0}</em></span>`).join("")}</b><span>Entries by language</span></div>`;
    const opts = docs.map((d) => `<option value="${esc(d.slug)}">${esc(d.title)}</option>`).join("");
    $("#refresh-doc").innerHTML = opts; $("#editor-doc").innerHTML = opts;
    await loadEntries();
  }

  async function loadEntries() {
    const p = new URLSearchParams();
    if ($("#q").value) p.set("q", $("#q").value);
    if ($("#f-lang").value) p.set("language", $("#f-lang").value);
    if ($("#f-status").value) p.set("status", $("#f-status").value);
    entries = await api(`/entries?${p}`);
    const tb = $("#entries tbody");
    tb.innerHTML = entries.map((e) => `
      <tr data-id="${e.entry_id}">
        <td class="key">${esc(e.entry_key)}</td><td>${esc(e.language_code)}</td>
        <td class="q"><b>${esc(e.question_text)}</b><br><span style="color:var(--muted)">${esc(e.answer_text.slice(0, 120))}${e.answer_text.length > 120 ? "…" : ""}</span></td>
        <td>${esc(e.document_slug)}</td>
        <td><span class="status ${esc(e.review_status)}">${esc(e.review_status)}</span>${e.is_active ? "" : '<br><span class="status">inactive</span>'}</td>
        <td style="color:var(--muted);font-size:var(--fs-xs)">${esc(e.embedding_model || "none")}</td>
        <td><div class="row-actions">
          <button class="ghost-btn" data-act="edit">Edit</button>
          ${e.review_status !== "approved" || !e.is_active ? '<button class="ghost-btn" data-act="approve">Approve</button>' : ""}
          ${e.is_active ? '<button class="ghost-btn" data-act="deactivate">Deactivate</button>' : ""}
        </div></td>
      </tr>`).join("");
    $("#empty").hidden = entries.length > 0;
  }

  $("#connect").addEventListener("click", async () => {
    token = $("#token").value.trim();
    try { sessionStorage.setItem("tambaya.admin", token); } catch { /* ignore */ }
    try { await loadAll(); } catch (e) { $("#stats").innerHTML = `<p class="result err">${esc(e.message)}</p>`; }
  });
  if (token) $("#connect").click();

  let t;
  ["#q", "#f-lang", "#f-status"].forEach((s) => $(s).addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => loadEntries().catch(() => {}), 250); }));

  /* ----- editor ----- */
  const dlg = $("#editor"), form = $("#editor-form");
  let editing = null;
  function openEditor(entry) {
    editing = entry;
    $("#editor-title").textContent = entry ? `Edit ${entry.entry_key} (${entry.language_code})` : "Add entry";
    form.reset();
    $("#editor-error").textContent = "";
    if (entry) {
      for (const k of ["entry_key", "language_code", "document_slug", "section_title", "question_text", "answer_text", "page_reference", "review_status"]) form.elements[k].value = entry[k] ?? "";
      form.elements.alt_questions.value = (entry.alt_questions || []).join("\n");
      form.elements.is_active.checked = entry.is_active;
    }
    dlg.showModal();
  }
  $("#new-entry").addEventListener("click", () => openEditor(null));
  $("#editor-cancel").addEventListener("click", () => dlg.close());
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const body = Object.fromEntries(fd.entries());
    body.alt_questions = String(body.alt_questions || "").split("\n").map((s) => s.trim()).filter(Boolean);
    body.is_active = form.elements.is_active.checked;
    $("#editor-save").disabled = true;
    try {
      if (editing) await api(`/entries/${editing.entry_id}`, { method: "PUT", body: JSON.stringify(body) });
      else await api("/entries", { method: "POST", body: JSON.stringify(body) });
      dlg.close(); await loadAll();
    } catch (err) { $("#editor-error").textContent = err.message; $("#editor-error").className = "result err"; }
    finally { $("#editor-save").disabled = false; }
  });

  $("#entries").addEventListener("click", async (e) => {
    const b = e.target.closest("button[data-act]"); if (!b) return;
    const id = b.closest("tr").dataset.id; const entry = entries.find((x) => x.entry_id === id);
    try {
      if (b.dataset.act === "edit") openEditor(entry);
      else if (b.dataset.act === "approve") { await api(`/entries/${id}/approve`, { method: "POST" }); await loadAll(); }
      else if (b.dataset.act === "deactivate") { if (confirm(`Deactivate "${entry.entry_key}" (${entry.language_code})? It stays in the database but is no longer used in answers.`)) { await api(`/entries/${id}`, { method: "DELETE" }); await loadAll(); } }
    } catch (err) { alert(err.message); }
  });

  /* ----- refresh / reingest ----- */
  $("#refresh-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const out = $("#refresh-result"); out.className = "result"; out.textContent = "Scraping and staging…";
    try {
      const r = await api("/refresh", { method: "POST", body: JSON.stringify({ document_slug: $("#refresh-doc").value, url: $("#refresh-url").value || null, language_code: $("#refresh-lang").value }) });
      out.textContent = `Staged ${r.chunks_staged} pending chunks from ${r.characters} characters for ${r.document}. Review them under "Pending review".`;
      await loadAll();
    } catch (err) { out.className = "result err"; out.textContent = err.message; }
  });
  $("#reingest").addEventListener("click", async () => {
    const out = $("#refresh-result"); out.className = "result"; out.textContent = "Re-ingesting…";
    try { const r = await api("/reingest", { method: "POST" }); out.textContent = `Re-ingested: ${r.entries.created} created, ${r.entries.updated} updated, ${r.entries.embedded} re-embedded.`; await loadAll(); }
    catch (err) { out.className = "result err"; out.textContent = err.message; }
  });
})();
