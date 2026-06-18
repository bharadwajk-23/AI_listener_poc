const CHAT_ENDPOINT = "http://localhost:8004/ptmantra/chat";
const SUMMARY_ENDPOINT = "http://localhost:8004/ptmantra/summary";
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const summaryCard = document.getElementById("summary-card");

let sessionId = null;
const conversationHistory = [];
const terminationKeywords = ["done", "finish", "end conversation"];

function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendChat(userText) {
  const payload = {
    message: userText,
    ...(sessionId && { session_id: sessionId }),
  };

  const response = await fetch(CHAT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Unable to reach the chat service.");
  }

  const data = await response.json();
  // Store session_id returned by backend for subsequent messages
  sessionId = data.session_id;
  return data;
}

function renderSummary(summary) {
  summaryCard.classList.remove("hidden");
  summaryCard.innerHTML = `
    <h2>Patient Summary</h2>
    <div class="summary-grid">
      <div><strong>Progress</strong><pre>${summary.patient_progress}</pre></div>
      <div><strong>Pain level</strong><pre>${summary.pain_level}</pre></div>
      <div><strong>Functional status</strong><pre>${summary.functional_status}</pre></div>
      <div><strong>Exercise adherence</strong><pre>${summary.exercise_adherence}</pre></div>
      <div><strong>Medication concerns</strong><pre>${summary.medication_concerns}</pre></div>
      <div><strong>Current symptoms</strong><pre>${summary.current_symptoms.join(", ")}</pre></div>
      <div><strong>New symptoms</strong><pre>${summary.new_symptoms.join(", ")}</pre></div>
      <div><strong>Patient concerns</strong><pre>${summary.patient_concerns.join(", ")}</pre></div>
      <div style="grid-column: 1 / -1;"><strong>Clinical summary</strong><pre>${summary.clinical_summary}</pre></div>
    </div>
  `;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const userText = chatInput.value.trim();
  if (!userText) return;

  // Frontend still keeps local UI history for display, but backend stores persistent history
  conversationHistory.push({ role: "user", content: userText });
  chatInput.value = "";

  try {
    const { reply, chat_ended } = await sendChat(userText);
    appendMessage("assistant", reply);
    conversationHistory.push({ role: "assistant", content: reply });

    if (chat_ended) {
      // Session is done — backend auto-triggers summary; reset for next consultation
      sessionId = null;
    }
  } catch (error) {
    appendMessage("assistant", "Sorry, I could not process your request. Please try again.");
    console.error(error);
  }
});

window.addEventListener("load", () => {
  const greeting = "Hello, how have you been feeling since your last check-in?";
  appendMessage("assistant", greeting);
  conversationHistory.push({ role: "assistant", content: greeting });
});
