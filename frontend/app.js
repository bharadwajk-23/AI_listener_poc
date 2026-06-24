// const CHAT_ENDPOINT    = "https://ailabs.youngsoft.com/ptmantra/chat";
// const SUMMARY_ENDPOINT = "https://ailabs.youngsoft.com/ptmantra/summary";

const CHAT_ENDPOINT    = "http://localhost:8004/ptmantra/chat";
const SUMMARY_ENDPOINT = "http://localhost:8004/ptmantra/summary";

const chatWindow     = document.getElementById("chat-window");
const chatForm       = document.getElementById("chat-form");
const chatInput      = document.getElementById("chat-input");
const micBtn         = document.getElementById("mic-btn");
const micStatus      = document.getElementById("mic-status");
const sessionBadge   = document.getElementById("session-badge");
const summaryOverlay = document.getElementById("summary-overlay");
const summaryCard    = document.getElementById("summary-card");
const summaryClose   = document.getElementById("summary-close");
const ttsToggle      = document.getElementById("tts-toggle");

let sessionId = null;
let ttsEnabled = true;
const conversationHistory = [];

// ── TTS toggle ────────────────────────────────────────────────────────────────
ttsToggle.addEventListener("click", () => {
  ttsEnabled = !ttsEnabled;
  ttsToggle.classList.toggle("active", ttsEnabled);
  ttsToggle.classList.toggle("muted", !ttsEnabled);
  if (!ttsEnabled) window.speechSynthesis?.cancel();
});

// ── Summary modal ─────────────────────────────────────────────────────────────
summaryClose.addEventListener("click", () => summaryOverlay.classList.add("hidden"));
summaryOverlay.addEventListener("click", (e) => {
  if (e.target === summaryOverlay) summaryOverlay.classList.add("hidden");
});

// ── Speech Recognition ────────────────────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening  = false;

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    micStatus.textContent = "Listening…";
    micStatus.classList.remove("hidden");
  };

  recognition.onresult = (e) => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join("");
    chatInput.value = transcript;
    if (e.results[e.results.length - 1].isFinal) {
      stopListening();
      if (transcript.trim()) chatForm.requestSubmit();
    }
  };

  recognition.onerror = (e) => { console.error("Speech:", e.error); stopListening(); };
  recognition.onend   = () => stopListening();
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition not supported";
}

function startListening() {
  if (!recognition || isListening) return;
  chatInput.value = "";
  recognition.start();
}

function stopListening() {
  isListening = false;
  micBtn.classList.remove("listening");
  micStatus.classList.add("hidden");
  try { recognition?.stop(); } catch (_) {}
}

micBtn.addEventListener("click", () => isListening ? stopListening() : startListening());

// ── TTS ───────────────────────────────────────────────────────────────────────
function speak(text) {
  if (!ttsEnabled || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = "en-US";
  utt.rate = 1;
  window.speechSynthesis.speak(utt);
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function timeStr() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function appendMessage(role, text) {
  const isUser = role === "user";

  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  // Avatar
  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = isUser ? "👤" : "🏥";

  // Body (bubble + time)
  const body = document.createElement("div");
  body.className = "msg-body";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const time = document.createElement("div");
  time.className = "msg-time";
  time.textContent = timeStr();

  body.appendChild(bubble);
  body.appendChild(time);

  wrapper.appendChild(avatar);
  wrapper.appendChild(body);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return wrapper;
}

function showTyping() {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";
  wrapper.innerHTML = `
    <div class="msg-avatar">🏥</div>
    <div class="msg-body">
      <div class="bubble typing-indicator"><span></span><span></span><span></span></div>
    </div>`;
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return wrapper;
}

function updateSessionBadge() {
  if (sessionId) {
    sessionBadge.textContent = sessionId;
    sessionBadge.classList.remove("hidden");
    document.querySelector(".info-dot")?.classList.add("active");
  } else {
    sessionBadge.classList.add("hidden");
    document.querySelector(".info-dot")?.classList.remove("active");
  }
}

function renderSummary(summary) {
  const val = (v) => v || "—";
  const list = (a) => Array.isArray(a) && a.length ? a.join(", ") : "—";

  summaryCard.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item"><strong>Patient Progress</strong><p>${val(summary.patient_progress)}</p></div>
      <div class="summary-item"><strong>Pain Level</strong><p>${val(summary.pain_level)}</p></div>
      <div class="summary-item"><strong>Functional Status</strong><p>${val(summary.functional_status)}</p></div>
      <div class="summary-item"><strong>Exercise Adherence</strong><p>${val(summary.exercise_adherence)}</p></div>
      <div class="summary-item"><strong>Medication Concerns</strong><p>${val(summary.medication_concerns)}</p></div>
      <div class="summary-item"><strong>Current Symptoms</strong><p>${list(summary.current_symptoms)}</p></div>
      <div class="summary-item"><strong>New Symptoms</strong><p>${list(summary.new_symptoms)}</p></div>
      <div class="summary-item"><strong>Patient Concerns</strong><p>${list(summary.patient_concerns)}</p></div>
      <div class="summary-item wide"><strong>Clinical Summary</strong><p>${val(summary.clinical_summary)}</p></div>
    </div>`;

  summaryOverlay.classList.remove("hidden");
}

// ── API ───────────────────────────────────────────────────────────────────────
async function sendChat(userText) {
  const response = await fetch(CHAT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: userText,
      ...(sessionId && { session_id: sessionId }),
    }),
  });

  if (!response.ok) throw new Error("Unable to reach the chat service.");

  const data = await response.json();
  sessionId = data.session_id;
  updateSessionBadge();
  return data;
}

// ── Submit ────────────────────────────────────────────────────────────────────
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const userText = chatInput.value.trim();
  if (!userText) return;

  chatInput.value = "";
  conversationHistory.push({ role: "user", content: userText });
  appendMessage("user", userText);

  const typingEl = showTyping();

  try {
    const { reply, chat_ended } = await sendChat(userText);
    typingEl.remove();
    appendMessage("assistant", reply);
    conversationHistory.push({ role: "assistant", content: reply });
    speak(reply);

    if (chat_ended) {
      sessionId = null;
      updateSessionBadge();
    }
  } catch (err) {
    typingEl.remove();
    appendMessage("assistant", "Sorry, I couldn't reach the server. Please try again.");
    console.error(err);
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", () => {
  // Date divider
  const divider = document.createElement("div");
  divider.className = "date-divider";
  divider.textContent = new Date().toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
  chatWindow.appendChild(divider);

  const greeting = "Hello! How have you been feeling since your last check-in?";
  appendMessage("assistant", greeting);
  conversationHistory.push({ role: "assistant", content: greeting });
});
