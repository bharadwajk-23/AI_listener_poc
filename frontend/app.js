const CHAT_ENDPOINT = "http://localhost:8000/chat";
const SUMMARY_ENDPOINT = "http://localhost:8000/summary";
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const summaryCard = document.getElementById("summary-card");

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

function buildConversationPayload() {
  return conversationHistory.map((item) => ({
    role: item.role,
    content: item.content,
  }));
}

async function sendChat(userText) {
  // Send only the current message; backend manages conversation history
  const payload = {
    message: userText,
    conversation_history: []  // Backend now stores the full history
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
  return data.reply;
}

async function requestSummary() {
  // Backend now manages conversation history, so send empty array
  const payload = {
    conversation_history: []
  };

  const response = await fetch(SUMMARY_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Unable to reach the summary service.");
  }

  return response.json();
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
    const assistantReply = await sendChat(userText);
    appendMessage("assistant", assistantReply);
    conversationHistory.push({ role: "assistant", content: assistantReply });

    // Check for chat_ended signal from backend (if backend detects end phrases)
    // For now, also check local termination keywords as fallback    conversationHistory.push({ role: "assistant", content: assistantReply });

    const normalized = userText.toLowerCase();
    if (terminationKeywords.includes(normalized)) {
      const summary = await requestSummary();
      renderSummary(summary);
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
