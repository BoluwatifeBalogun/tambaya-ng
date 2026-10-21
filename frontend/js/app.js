/* Tambaya NG front end: plain JavaScript, no build step. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = matchMedia("(pointer: fine)").matches;

  const state = {
    language: "auto",
    conversationId: null,
    userId: null,
    busy: false,
    inChat: false,
  };

  /* ---------- Persistence (per-viewer conveniences only) ---------- */
  const store = {
    get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode etc. */ } },
    del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
  };

  /* ---------- Theme ---------- */
  const root = document.documentElement;
  const themeBtn = $("#theme-toggle");
  function applyTheme(theme) {
    root.dataset.theme = theme;
    themeBtn.setAttribute("aria-pressed", String(theme === "light"));
    themeBtn.setAttribute("aria-label", theme === "light" ? "Switch to dark mode" : "Switch to light mode");
    $('meta[name="theme-color"]').setAttribute("content", theme === "light" ? "#FFFFFF" : "#0D1210");
  }
  applyTheme(store.get("tambaya.theme") || "light");
  themeBtn.addEventListener("click", () => {
    const next = root.dataset.theme === "light" ? "dark" : "light";
    applyTheme(next);
    store.set("tambaya.theme", next);
  });

  /* ---------- Language switch ---------- */
  const langSwitch = $("#lang-switch");
  state.language = store.get("tambaya.lang") || "auto";
  function paintLang() {
    $$("button", langSwitch).forEach((b) => b.setAttribute("aria-checked", String(b.dataset.lang === state.language)));
  }
  paintLang();
  langSwitch.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-lang]");
    if (!b) return;
    state.language = b.dataset.lang;
    store.set("tambaya.lang", state.language);
    paintLang();
    localiseExamples();
  });
  langSwitch.addEventListener("keydown", (e) => {
    const btns = $$("button", langSwitch);
    const i = btns.findIndex((b) => b.dataset.lang === state.language);
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const n = (i + (e.key === "ArrowRight" ? 1 : -1) + btns.length) % btns.length;
      btns[n].click(); btns[n].focus();
    }
  });

  /* ---------- Example questions follow the chosen language ---------- */
  const LANG_NAMES = { en: "English", pcm: "Pidgin", ha: "Hausa", yo: "Yorùbá", ig: "Igbo" };
  const EXAMPLES = {
    en: {
      chips: [["NIN documents", "What documents do I need to enrol for a NIN?"], ["Passport fees", "How much does a Nigerian passport cost?"],
              ["Renew my licence", "How do I renew my driver's licence?"], ["Lost passport", "I lost my passport, what do I do?"],
              ["Register a birth", "How do I register my baby's birth?"]],
      cards: { nin: "How do I enrol for a NIN and what does it cost?", passport: "How do I apply for a Nigerian passport and how much is it?",
               licence: "How do I get a driver's licence and how much does it cost?", birth: "How do I register my child's birth and get a birth certificate?" },
      followup: "Ask a follow-up or a new question",
    },
    pcm: {
      chips: [["How I go get NIN?", "Abeg how I go take get NIN?"], ["How much be passport?", "How much be passport now?"],
              ["Licence don expire", "My driver licence don expire, how I go renew am?"], ["Passport don loss", "My passport don loss, wetin I go do?"],
              ["Birth certificate na free?", "Birth certificate na free?"]],
      cards: { nin: "Abeg how I go take get NIN?", passport: "How I go apply for passport?", licence: "How I go take get driver licence?",
               birth: "How I go register my pikin birth?" },
      followup: "Ask another question for Pidgin",
    },
    ha: {
      chips: [["Rijistar NIN", "Ta yaya zan yi rajistar NIN?"], ["Kuɗin fasfo", "Nawa ne kuɗin fasfo?"],
              ["Sabunta lasisi", "Ta yaya zan sabunta lasisin tuƙi?"], ["Fasfo ya ɓace", "Fasfona ya ɓace, me zan yi?"],
              ["Rajistar haihuwa", "Ta yaya zan yi rajistar haihuwar jariri?"]],
      cards: { nin: "Ta yaya zan yi rajistar NIN?", passport: "Ta yaya zan nemi fasfo?", licence: "Ta yaya zan sami lasisin tuƙi?",
               birth: "Ta yaya zan yi rajistar haihuwar yaro?" },
      followup: "Yi wata tambaya",
    },
    yo: {
      chips: [["Gba NIN", "Báwo ni mo ṣe lè gba NIN?"], ["Owó pásípọ̀ọ̀tù", "Èló ni pásípọ̀ọ̀tù?"], ["Owó ìwé-àṣẹ awakọ̀", "Èló ni ìwé-àṣẹ awakọ̀?"],
              ["Pásípọ̀ọ̀tù sọnù", "Pásípọ̀ọ̀tù mi sọnù, kí ni kí n ṣe?"], ["Ìforúkọsílẹ̀ ìbí", "Báwo ni mo ṣe lè forúkọ ìbí ọmọ mi sílẹ̀?"]],
      cards: { nin: "Báwo ni mo ṣe lè gba NIN?", passport: "Báwo ni mo ṣe lè gba pásípọ̀ọ̀tù?", licence: "Báwo ni mo ṣe lè gba ìwé-àṣẹ awakọ̀?",
               birth: "Báwo ni mo ṣe lè forúkọ ìbí ọmọ mi sílẹ̀?" },
      followup: "Béèrè ìbéèrè mìíràn",
    },
    ig: {
      chips: [["Nweta NIN", "Kedu ka m ga-esi nweta NIN?"], ["Ụgwọ paspọtụ", "Ego ole ka paspọtụ na-efu?"],
              ["Megharịa ikike", "Kedu ka m ga-esi megharịa ikike ịnya ụgbọala m?"], ["Paspọtụ furu efu", "Paspọtụ m furu efu, gịnị ka m ga-eme?"],
              ["Ndebanye ọmụmụ", "Kedu ka m ga-esi debanye aha ọmụmụ nwa m?"]],
      cards: { nin: "Kedu ka m ga-esi nweta NIN?", passport: "Kedu ka m ga-esi nweta paspọtụ?", licence: "Kedu ka m ga-esi nweta ikike ịnya ụgbọala?",
               birth: "Kedu ka m ga-esi debanye aha ọmụmụ nwa m?" },
      followup: "Jụọ ajụjụ ọzọ",
    },
  };
  const chipsBox = $("#hero-chips");
  const autoChips = chipsBox ? chipsBox.innerHTML : "";
  function localiseExamples() {
    const ex = EXAMPLES[state.language];
    if (chipsBox) {
      if (!ex) chipsBox.innerHTML = autoChips;
      else {
        chipsBox.textContent = "";
        for (const [label, q] of ex.chips) {
          const b = document.createElement("button");
          b.type = "button"; b.className = "chip"; b.dataset.q = q; b.textContent = label;
          chipsBox.append(b);
        }
      }
    }
    $$("article[data-card]").forEach((a) => {
      a.dataset.q = (ex || EXAMPLES.en).cards[a.dataset.card];
    });
    const ci = $("#chat-input");
    if (ci) ci.placeholder = (ex || EXAMPLES.en).followup;
  }
  localiseExamples();

  /* ---------- Hero headline reveal (one orchestrated load moment) ---------- */
  const title = $("[data-reveal]");
  if (title && !reduceMotion) {
    const words = title.textContent.trim().split(/\s+/);
    title.textContent = "";
    words.forEach((w, i) => {
      const s = document.createElement("span");
      s.className = "w"; s.textContent = w; s.style.setProperty("--i", i);
      title.append(s, " ");
    });
    title.classList.add("reveal");
  }

  /* ---------- Rotating multilingual placeholder ---------- */
  const heroInput = $("#composer-input");
  const placeholders = [
    "How do I get my NIN?",
    "Abeg how much be passport now?",
    "Nawa ne kuɗin fasfo?",
    "Èló ni ìwé-àṣẹ awakọ̀?",
    "Kedu ka m ga-esi nweta akwụkwọ ọmụmụ?",
    "I lost my driver's licence, what do I do?",
    "Ta yaya zan gyara ranar haihuwa a NIN?",
  ];
  let phIndex = 0;
  if (!reduceMotion) {
    setInterval(() => {
      if (document.activeElement === heroInput || heroInput.value) return;
      heroInput.classList.add("swap");
      setTimeout(() => {
        phIndex = (phIndex + 1) % placeholders.length;
        heroInput.placeholder = placeholders[phIndex];
        heroInput.classList.remove("swap");
      }, 300);
    }, 3800);
  }

  /* ---------- Spotlight cards: one listener on the grid ---------- */
  const grid = $("#service-cards");
  if (grid && finePointer && !reduceMotion) {
    grid.addEventListener("pointermove", (e) => {
      for (const card of grid.children) {
        const r = card.getBoundingClientRect();
        card.style.setProperty("--x", `${e.clientX - r.left}px`);
        card.style.setProperty("--y", `${e.clientY - r.top}px`);
      }
    }, { passive: true });
    grid.addEventListener("pointerleave", () => {
      for (const c of grid.children) { c.style.setProperty("--x", "-300px"); c.style.setProperty("--y", "-300px"); }
    });
  }

  /* ---------- Textareas grow with content; Enter sends, Shift+Enter breaks ---------- */
  function autoGrow(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 240) + "px";
  }
  $$(".composer-input").forEach((el) => {
    el.addEventListener("input", () => autoGrow(el));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        el.form.requestSubmit();
      }
    });
  });

  /* ---------- Chat view ---------- */
  const landing = $("#landing");
  const chat = $("#chat");
  const messages = $("#messages");
  const chatScroll = $("#chat-scroll");
  const chatInput = $("#chat-input");
  const tplUser = $("#tpl-user");
  const tplBot = $("#tpl-bot");

  function enterChat() {
    if (state.inChat) return;
    state.inChat = true;
    landing.hidden = true;
    chat.hidden = false;
    document.body.classList.add("in-chat");
    window.scrollTo(0, 0);
  }

  function leaveChatToNew() {
    state.conversationId = null;
    store.del("tambaya.conversation");
    messages.innerHTML = "";
    chatInput.value = "";
    autoGrow(chatInput);
    chatInput.focus();
  }

  function scrollToBottom() {
    chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: reduceMotion ? "auto" : "smooth" });
  }

  function addUser(text) {
    const li = tplUser.content.firstElementChild.cloneNode(true);
    $(".bubble", li).textContent = text;
    messages.append(li);
    scrollToBottom();
    return li;
  }

  function addBotPending() {
    const li = tplBot.content.firstElementChild.cloneNode(true);
    messages.append(li);
    scrollToBottom();
    return li;
  }

  const ICON_LINK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>';
  const ICON_FLAG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></svg>';

  /* Safe rich text: everything is escaped first, then only a small markdown subset is re-introduced
     (**bold**, paragraphs, "1." / "1)" numbered steps, "-" bullets) plus citation links. Model output can
     never inject markup. */
  function formatAnswer(text, sources) {
    let t = escapeHTML(String(text || "").trim()).replace(/\r/g, "");
    // Inline steps such as "To enrol: 1) Go ... 2) Fill ..." become one step per line.
    if (/(^|\s)1\)\s/.test(t) && /\s2\)\s/.test(t)) t = t.replace(/\s+(?=\d{1,2}\)\s)/g, "\n");
    const blocks = t.split(/\n{2,}/).map((block) => {
      const out = [];
      let list = null, type = null;
      const flush = () => { if (list) out.push(`<${type}>${list.map((li) => `<li>${li}</li>`).join("")}</${type}>`); list = null; };
      for (const line of block.split("\n")) {
        const ol = line.match(/^\s*\d{1,2}[.)]\s+(.*)$/);
        const ul = line.match(/^\s*[-•*]\s+(.*)$/);
        if (ol || ul) {
          const want = ol ? "ol" : "ul";
          if (type !== want) flush();
          type = want;
          (list = list || []).push((ol || ul)[1]);
        } else if (line.trim()) {
          flush();
          out.push(`<p>${line.trim()}</p>`);
        }
      }
      flush();
      return out.join("");
    });
    return blocks.join("")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[(\d+)\]/g, (m, n) => {
        const src = sources.find((s) => String(s.n) === n);
        if (!src) return "";
        return `<a class="cite" href="${escapeHTML(src.source_url)}" target="_blank" rel="noopener" title="${escapeHTML(src.title)}">${n}</a>`;
      });
  }

  /* Progressive reveal of the finished answer (reads as streaming, keeps citations intact). */
  function revealAnswer(bubble, text, sources, done) {
    const html = formatAnswer(text, sources);
    const finish = () => { bubble.classList.add("rich"); bubble.innerHTML = html; };
    if (reduceMotion) { finish(); done(); return; }
    const tokens = text.replace(/\*\*/g, "").split(/(\s+)/);
    let i = 0;
    bubble.classList.add("caret");
    bubble.textContent = "";
    const step = () => {
      const chunk = tokens.slice(i, i + 3).join("");
      i += 3;
      bubble.textContent += chunk;
      if (i % 12 === 0) scrollToBottom();
      if (i < tokens.length) {
        setTimeout(step, 18 + Math.random() * 22);
      } else {
        bubble.classList.remove("caret");
        finish();
        scrollToBottom();
        done();
      }
    };
    step();
  }

  function renderMeta(meta, data) {
    const parts = [];
    if (data.sources.length) {
      parts.push(`<div class="sources" aria-label="Sources">${data.sources.map((s) => `
        <a class="src-card" href="${s.source_url}" target="_blank" rel="noopener">
          <span class="src-n" aria-hidden="true">${s.n}</span>
          <span><b>${escapeHTML(s.agency || s.title)}</b><span>${escapeHTML(s.section_title || s.title)}${s.last_verified ? ` · verified ${s.last_verified}` : ""}</span><span class="src-url">${escapeHTML(s.source_url.replace(/^https?:\/\//, ""))}</span></span>
        </a>`).join("")}</div>`);
    }
    if (data.needs_official_action && data.official_channel) {
      parts.push(`<div class="official">${ICON_FLAG}<div><b>${data.fallback ? "Try the official channel" : "To take this step, use the official channel"}</b><span>${escapeHTML(data.official_channel)}</span></div></div>`);
    }
    const langName = LANG_NAMES[data.language] || data.language;
    const modeLabel = { llm: "Groq, grounded", extractive: "verified entry, verbatim", fallback: "no verified match", chat: "quick reply" }[data.mode] || data.mode;
    const checks = data.checks || [];
    const failed = checks.filter((c) => c.startsWith("FAILED:"));
    const passedCount = checks.filter((c) => !c.startsWith("FAILED:") && !c.startsWith("retrieval:") && c !== "model_declared_insufficient").length;
    let verify = "";
    if (data.mode === "llm" && passedCount) verify = `<span title="${escapeHTML(checks.join(", "))}">${passedCount} checks passed</span>`;
    else if (failed.length) verify = `<span title="${escapeHTML(failed.join(", "))}">generated answer failed verification, verified entry served</span>`;
    parts.push(`<div class="trace"><span>${langName}</span><span>${modeLabel}</span>${verify}<span>${data.timings.total_ms} ms</span></div>`);
    meta.innerHTML = parts.join("");
  }

  function escapeHTML(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function ask(text, fromForm) {
    text = (text || "").trim();
    if (!text || state.busy) return;
    state.busy = true;
    enterChat();
    $$(".send-btn").forEach((b) => (b.disabled = true));
    fromForm.classList.add("busy");
    $("#chat-form").classList.add("busy");
    $(".error-banner")?.remove();

    addUser(text);
    const pending = addBotPending();
    const bubble = $(".bubble", pending);
    const meta = $(".meta", pending);
    chatInput.value = "";
    autoGrow(chatInput);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: text, language: state.language, conversation_id: state.conversationId, user_id: state.userId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `The service answered with status ${res.status}.`);
      }
      const data = await res.json();
      state.conversationId = data.conversation_id;
      state.userId = data.user_id;
      store.set("tambaya.user", state.userId);
      store.set("tambaya.conversation", state.conversationId);
      if (data.fallback) pending.classList.add("fallback");
      if (data.mode === "chat") pending.classList.add("chat");
      revealAnswer(bubble, data.answer, data.sources, () => { renderMeta(meta, data); requestAnimationFrame(scrollToBottom); setTimeout(scrollToBottom, 350); });
    } catch (e) {
      bubble.innerHTML = "";
      bubble.textContent = e.name === "TypeError"
        ? "Tambaya could not reach the answer service. Check your connection and try again."
        : e.message;
      pending.classList.add("fallback");
      meta.innerHTML = `<div class="trace"><span class="err">Nothing was answered for this question.</span></div>`;
    } finally {
      state.busy = false;
      $$(".send-btn").forEach((b) => (b.disabled = false));
      fromForm.classList.remove("busy");
      $("#chat-form").classList.remove("busy");
      chatInput.focus({ preventScroll: true });
    }
  }

  $("#hero-form").addEventListener("submit", (e) => { e.preventDefault(); ask(heroInput.value, e.currentTarget); });
  $("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); ask(chatInput.value, e.currentTarget); });
  $("#new-chat").addEventListener("click", leaveChatToNew);

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-q]");
    if (!trigger) return;
    ask(trigger.dataset.q, $("#hero-form"));
  });
  document.addEventListener("keydown", (e) => {
    const trigger = e.target.closest?.("article[data-q]");
    if (trigger && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); ask(trigger.dataset.q, $("#hero-form")); }
  });
  $$("article[data-q]").forEach((a) => { a.tabIndex = 0; a.setAttribute("role", "button"); });

  /* ---------- Resume a previous conversation on this device ---------- */
  state.userId = store.get("tambaya.user");
  const savedConversation = store.get("tambaya.conversation");
  if (state.userId && savedConversation && location.hash === "#chat") {
    fetch(`/api/conversations/${savedConversation}?user_id=${state.userId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((c) => {
        if (!c || !c.messages.length) return;
        state.conversationId = savedConversation;
        enterChat();
        for (const m of c.messages) {
          if (m.role === "user") addUser(m.text);
          else {
            const li = tplBot.content.firstElementChild.cloneNode(true);
            const b = $(".bubble", li);
            b.classList.add("rich");
            b.innerHTML = formatAnswer(m.text.replace(/\[\d+\]/g, ""), []);
            $(".meta", li).innerHTML = `<div class="trace"><span>${escapeHTML(LANG_NAMES[m.language] || m.language)}</span><span>earlier in this conversation</span></div>`;
            if (m.fallback) li.classList.add("fallback");
            messages.append(li);
          }
        }
        scrollToBottom();
      })
      .catch(() => {});
  }
})();
