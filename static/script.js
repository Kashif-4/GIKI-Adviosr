const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const traceContainer = document.getElementById('trace-container');

function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    // Use marked for bot messages
    const content = role === 'bot' ? marked.parse(text) : text;
    msgDiv.innerHTML = `<div class="bubble">${content}</div>`;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
}

const nodeMap = new Map();
const nodeCounts = new Map();

function addTrace(text, node) {
    if (nodeMap.has(node)) {
        const existingItem = nodeMap.get(node);
        const count = (nodeCounts.get(node) || 1) + 1;
        nodeCounts.set(node, count);
        
        // Show retry count if it's a loop
        const retryText = count > 1 ? ` <span style="font-size:10px; color:var(--primary); font-weight:600;">(RE-TRYING #${count-1})</span>` : '';
        existingItem.innerHTML = `<strong>></strong> ${text}${retryText}`;
        return;
    }
    
    const item = document.createElement('div');
    item.className = 'trace-item';
    item.innerHTML = `<strong>></strong> ${text}`;
    traceContainer.appendChild(item);
    traceContainer.scrollTop = traceContainer.scrollHeight;
    
    nodeMap.set(node, item);
    nodeCounts.set(node, 1);
}

function updateSources(sources) {
    const sourcesList = document.getElementById('sources-list');
    sourcesList.innerHTML = '';
    if (sources && sources.length > 0) {
        sources.forEach(src => {
            const item = document.createElement('div');
            item.className = 'source-card';
            item.innerHTML = `
                <p class="source-name">📄 ${src.source}</p>
                <p class="source-preview">${src.content}...</p>
            `;
            sourcesList.appendChild(item);
        });
    } else {
        sourcesList.innerHTML = '<p class="empty-sources">No documents retrieved yet.</p>';
    }
}

async function handleSend() {
    const query = userInput.value.trim();
    if (!query) return;

    userInput.value = '';
    appendMessage('user', query);
    
    // Clear sources and traces UI
    updateSources([]);
    traceContainer.innerHTML = '';
    nodeMap.clear();
    nodeCounts.clear();
    const botMsg = document.createElement('div');
    botMsg.className = 'message bot';
    botMsg.innerHTML = '<div class="bubble"><em>Agent is initializing...</em></div>';
    chatMessages.appendChild(botMsg);
    const bubble = botMsg.querySelector('.bubble');
    
    // Clear traces
    traceContainer.innerHTML = '';

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        
                        if (data.type === 'trace') {
                            addTrace(data.content, data.node);
                            // Remove initializing text on first trace
                            if (bubble.innerHTML.includes('initializing')) {
                                bubble.innerHTML = `<em class="thinking">${data.content}</em>`;
                            } else {
                                bubble.innerHTML = `<em class="thinking">${data.content}</em>`;
                            }
                        } else if (data.type === 'sources') {
                            updateSources(data.content);
                        } else if (data.type === 'answer') {
                            bubble.innerHTML = marked.parse(data.content);
                        } else if (data.type === 'error') {
                            bubble.innerHTML = `<span style="color:red">Error: ${data.content}</span>`;
                        }
                    } catch (e) {
                        // Incomplete JSON chunk, skip
                    }
                }
            }
        }
        
    } catch (error) {
        bubble.innerHTML = 'Sorry, I encountered a connection error.';
        console.error(error);
    }
}

sendBtn.addEventListener('click', handleSend);
// Sidebar Resizer
const resizer = document.getElementById('resizer');
const sidePanel = document.querySelector('.side-panel');

let isResizing = false;

resizer.addEventListener('mousedown', (e) => {
    e.preventDefault(); // Prevent text selection
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    document.body.classList.add('resizing');
});

document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    
    // Calculate new width from right side
    const width = window.innerWidth - e.clientX;
    
    // Constraints: 300px to 800px
    if (width >= 300 && width <= 800) {
        sidePanel.style.width = `${width}px`;
        sidePanel.style.flex = 'none'; // Lock the flex width
    }
});

document.addEventListener('mouseup', () => {
    isResizing = false;
    document.body.style.cursor = 'default';
    document.body.classList.remove('resizing');
});
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});
