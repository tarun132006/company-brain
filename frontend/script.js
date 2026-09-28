const API_URL = "http://127.0.0.1:8000";

const REQUEST_TIMEOUT_MS = 60000;

// ===============================
// AGENT CONFIG
// ===============================

const AGENTS = {
    support: {
        endpoint: "/api/chat",
        customer: "Acme",
        label: "Company Brain",
        title: "How can I help?",
        text: "Ask Support about customer issues, incidents, and previous solutions."
    },

    engineering: {
        endpoint: "/api/engineering",
        customer: "Engineering",
        label: "Engineering Agent",
        title: "Engineering memory",
        text: "Ask Engineering about known technical limitations and planned work."
    },

    sales: {
        endpoint: "/api/sales",
        customer: "Sales",
        label: "Sales Agent",
        title: "Sales intelligence",
        text: "Ask Sales before making customer commitments."
    },

    arbiter: {
        endpoint: "/api/arbiter",
        customer: "Sales",
        label: "Arbiter",
        title: "Conflict Arbiter",
        text: "Check a proposed commitment against organizational memory."
    }
};

const AGENT_ORDER = [
    "support",
    "engineering",
    "sales",
    "arbiter"
];

let currentAgent = "support";
let isSending = false;

const agentButtons = document.querySelectorAll(".agent");
const chatMessages = document.querySelector(".messages");
const input = document.getElementById("message");
const sendButton = document.getElementById("sendButton");


// ===============================
// SAFETY CHECK
// ===============================

if (!chatMessages || !input || !sendButton) {
    console.error(
        "Company Brain: missing .messages, #message or #sendButton."
    );
}


// ===============================
// AGENT SELECTION
// ===============================

agentButtons.forEach((button, index) => {

    button.addEventListener("click", function () {

        if (isSending) return;

        agentButtons.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        const key =
            button.dataset.agent ||
            AGENT_ORDER[index];

        if (AGENTS[key]) {
            currentAgent = key;
        }

        // Start a clean conversation for each agent
        clearChat();

        updateWelcomeMessage();
    });
});


// ===============================
// WELCOME MESSAGE
// ===============================

function updateWelcomeMessage() {

    const welcome = document.querySelector(".welcome");

    if (!welcome) return;

    const title = welcome.querySelector("h1");
    const paragraph = welcome.querySelector("p");

    const agent = AGENTS[currentAgent];

    if (title) {
        title.textContent = agent.title;
    }

    if (paragraph) {
        paragraph.textContent = agent.text;
    }

    welcome.style.display = "";
}


function hideWelcomeMessage() {

    const welcome = document.querySelector(".welcome");

    if (welcome) {
        welcome.style.display = "none";
    }
}


// ===============================
// CLEAR CHAT
// ===============================

function clearChat() {

    if (!chatMessages) return;

    chatMessages.innerHTML = "";
}


// ===============================
// SEND MESSAGE
// ===============================

async function sendMessage() {

    if (isSending) return;

    const message = input.value.trim();

    if (message === "") return;

    const agentKey = currentAgent;
    const agent = AGENTS[agentKey];

    isSending = true;

    sendButton.disabled = true;

    hideWelcomeMessage();

    addUserMessage(message);

    input.value = "";

    showLoading(agent.label);

    const url = API_URL + agent.endpoint;

    console.log("Sending request to:", url);

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, REQUEST_TIMEOUT_MS);


    try {

        const response = await fetch(url, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                customer: agent.customer,
                message: message
            }),

            signal: controller.signal
        });


        console.log("HTTP status:", response.status);


        if (!response.ok) {

            const errorText = await response.text();

            throw new Error(
                "Server returned " +
                response.status +
                ": " +
                errorText
            );
        }


        const data = await response.json();

        console.log(
            "Company Brain response:",
            data
        );


        removeLoading();

        addAssistantMessage(
            data,
            agentKey
        );


    } catch (error) {

        console.error(
            "Company Brain error:",
            error
        );

        removeLoading();

        const reason =
            error.name === "AbortError"
                ? "The request timed out."
                : error.message;


        addAssistantMessage(
            {
                answer:
                    "Error connecting to Company Brain: " +
                    reason
            },
            agentKey
        );


    } finally {

        clearTimeout(timeoutId);

        isSending = false;

        sendButton.disabled = false;

        input.focus();
    }
}


// ===============================
// USER MESSAGE
// ===============================

function addUserMessage(message) {

    const messageElement =
        document.createElement("div");

    messageElement.className =
        "message user-message";


    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.textContent = message;


    messageElement.appendChild(content);

    chatMessages.appendChild(
        messageElement
    );

    scrollToBottom();
}


// ===============================
// ASSISTANT MESSAGE
// ===============================

function addAssistantMessage(
    data,
    agentKey = currentAgent
) {

    data = data || {};

    const messageElement =
        document.createElement("div");

    messageElement.className =
        "message assistant-message";


    const header =
        document.createElement("div");

    header.className =
        "message-header";

    header.textContent =
        AGENTS[agentKey]?.label ||
        "Company Brain";


    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.innerHTML =
        formatAnswer(
            String(data.answer || "")
        );


    messageElement.appendChild(header);

    messageElement.appendChild(content);


    // ===============================
    // HINDSIGHT MEMORIES
    // ===============================

    if (
        Array.isArray(data.memories_used) &&
        data.memories_used.length > 0
    ) {

        const details =
            document.createElement("details");

        details.className =
            "memory-details";


        const summary =
            document.createElement("summary");

        summary.textContent =
            data.memories_used.length +
            " memories used";


        const memoryList =
            document.createElement("div");

        memoryList.className =
            "memory-list";


        data.memories_used.forEach(
            memory => {

                const item =
                    document.createElement("div");

                item.className =
                    "memory-item";


                item.textContent =
                    typeof memory === "string"
                        ? memory
                        : (
                            memory.text ||
                            memory.content ||
                            JSON.stringify(memory)
                        );


                memoryList.appendChild(item);
            }
        );


        details.appendChild(summary);

        details.appendChild(memoryList);

        messageElement.appendChild(details);
    }


    // ===============================
    // ARBITER CONFLICT
    // ===============================

    if (
        agentKey === "arbiter" &&
        data.conflict === true
    ) {

        const warning =
            document.createElement("div");

        warning.className =
            "conflict-warning";

        warning.textContent =
            "⚠ Conflict detected";


        messageElement.appendChild(
            warning
        );
    }


    chatMessages.appendChild(
        messageElement
    );

    scrollToBottom();
}


// ===============================
// LOADING
// ===============================

function showLoading(
    label = "Company Brain"
) {

    const loading =
        document.createElement("div");

    loading.className =
        "message assistant-message loading-message";

    loading.id =
        "loading-message";


    const header =
        document.createElement("div");

    header.className =
        "message-header";

    header.textContent =
        label;


    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.textContent =
        "Thinking...";


    loading.appendChild(header);

    loading.appendChild(content);

    chatMessages.appendChild(
        loading
    );

    scrollToBottom();
}


function removeLoading() {

    const loading =
        document.getElementById(
            "loading-message"
        );

    if (loading) {
        loading.remove();
    }
}


// ===============================
// FORMAT ANSWER
// ===============================

function formatAnswer(text) {

    return escapeHtml(text)
        .replace(
            /\*\*(.+?)\*\*/g,
            "<strong>$1</strong>"
        )
        .replace(
            /\r?\n/g,
            "<br>"
        );
}


// ===============================
// ESCAPE HTML
// ===============================

function escapeHtml(text) {

    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}


// ===============================
// SCROLL
// ===============================

function scrollToBottom() {

    if (!chatMessages) return;

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


// ===============================
// EVENTS
// ===============================

sendButton.addEventListener(
    "click",
    sendMessage
);


input.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.isComposing
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


// ===============================
// START
// ===============================

updateWelcomeMessage();