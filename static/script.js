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

// Global functions for interactive form
window.summerPref = true;
window.toggleSummer = function(val) {
    window.summerPref = val;
    document.getElementById('summer-yes').classList.toggle('active', val);
    document.getElementById('summer-no').classList.toggle('active', !val);
};

window.submitInteractiveForm = function(btnElement) {
    const bubbleElement = btnElement.parentElement;
    
    const failedStr = document.getElementById('failed-input').value;
    const failed = failedStr ? failedStr.split(',').map(s => s.trim().toUpperCase()) : [];
    const sem = document.getElementById('sem-select').value;
    const cgpa = document.getElementById('cgpa-input').value || 3.0;
    const degree = document.getElementById('degree-select').value;
    
    const payload = {
        failed: failed,
        passed: [],
        sem: sem,
        cgpa: parseFloat(cgpa),
        degree: degree,
        summer: window.summerPref
    };
    
    const queryStr = "[PLAN_INPUT] " + JSON.stringify(payload);
    
    // Disable the form instead of deleting it
    bubbleElement.querySelectorAll('input, select, button').forEach(el => el.disabled = true);
    bubbleElement.querySelectorAll('.chip').forEach(el => el.style.pointerEvents = 'none');
    btnElement.innerHTML = "⏳ Calculating Plan...";
    btnElement.style.opacity = 0.7;
    
    // Execute the hidden query
    processQuery(queryStr, `Planning my ${degree} - Sem: ${sem}, CGPA: ${cgpa}, Summer: ${window.summerPref ? 'Yes' : 'No'}, Failed: ${failed.join(', ') || 'None'}`);
};

function renderInteractiveForm(bubble) {
    switchTab('planner');
    bubble.innerHTML = `
        <div class="interactive-form">
            <h3 style="color: var(--primary); margin-bottom: 4px; font-size: 16px;">🎓 Let's build your perfect degree plan!</h3>
            <p style="margin-bottom: 16px; font-size: 13px; color: var(--text-muted);">Answer the questions below. I will check university policies, prerequisites, and scheduling rules before generating your complete roadmap.</p>
            
            <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px;">📘 Degree Program</label>
                <select id="degree-select" class="modern-input" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    <option value="BSCS">BS Computer Science (BSCS)</option>
                    <option value="BSAI">BS Artificial Intelligence (BSAI)</option>
                    <option value="BSDS">BS Data Science (BSDS)</option>
                    <option value="BSSE">BS Software Engineering (BSSE)</option>
                    <option value="BSCE">BS Computer Engineering (BSCE)</option>
                </select>
            </div>

            <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px;">📅 Which semester did you just COMPLETE? (including the one with the failed course)</label>
                <div style="display: flex; gap: 12px;">
                    <select id="sem-select" class="modern-input" style="flex: 1; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                        <option value="1">Semester 1</option>
                        <option value="2">Semester 2</option>
                        <option value="3">Semester 3</option>
                        <option value="4">Semester 4</option>
                        <option value="5">Semester 5</option>
                        <option value="6">Semester 6</option>
                        <option value="7">Semester 7</option>
                    </select>
                    <input type="number" id="cgpa-input" step="0.01" min="0" max="4" class="modern-input" placeholder="Current CGPA (0.0–4.0)" style="flex: 1; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                </div>
                <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">⚠️ If CGPA &lt; 2.0, Academic Probation rules apply (max 12 CH/sem)</p>
            </div>
            
            <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px;">❌ Which courses did you fail? (comma-separated course codes)</label>
                <input type="text" id="failed-input" class="modern-input" placeholder="e.g., CS112, MT202" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Leave blank if you just want to re-plan from your current semester forward</p>
            </div>
            
            <div class="form-group chips-group" style="margin-bottom: 24px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; font-size: 13px;">☀️ Are you willing to take Summer classes to catch up?</label>
                <div class="chips" style="display: flex; gap: 8px;">
                    <div class="chip active" id="summer-yes" onclick="toggleSummer(true)" style="padding: 8px 16px; border-radius: 20px; border: 1px solid var(--primary); cursor: pointer; font-size: 13px; transition: all 0.2s;">✅ Yes — Catch-up Plan</div>
                    <div class="chip" id="summer-no" onclick="toggleSummer(false)" style="padding: 8px 16px; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; font-size: 13px; transition: all 0.2s;">🚫 No — Relaxed Plan</div>
                </div>
            </div>
            
            <button class="btn-primary" onclick="submitInteractiveForm(this)" style="width: 100%; padding: 12px; font-weight: 600; font-size: 15px;">🚀 Generate My Smart Degree Plan</button>
        </div>
    `;
}

async function processQuery(query, displayText) {
    if (!query) return;

    if (displayText) {
        appendMessage('user', displayText);
    } else {
        appendMessage('user', query);
    }
    
    // Clear sources and traces UI
    updateSources([]);
    traceContainer.innerHTML = '';
    nodeMap.clear();
    nodeCounts.clear();
    
    const botMsg = document.createElement('div');
    botMsg.className = 'message bot';
    botMsg.innerHTML = '<div class="bubble"><em>Agent is thinking...</em></div>';
    chatMessages.appendChild(botMsg);
    const bubble = botMsg.querySelector('.bubble');

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
                            if (bubble.innerHTML.includes('thinking')) {
                                bubble.innerHTML = `<em class="thinking">${data.content}</em>`;
                            } else {
                                bubble.innerHTML = `<em class="thinking">${data.content}</em>`;
                            }
                        } else if (data.type === 'sources') {
                            updateSources(data.content);
                        } else if (data.type === 'answer') {
                            if (data.content.includes("[INTERACTIVE_FORM_TRIGGER]")) {
                                renderInteractiveForm(bubble);
                            } else {
                                bubble.innerHTML = marked.parse(data.content);
                            }
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

async function handleSend() {
    const query = userInput.value.trim();
    userInput.value = '';
    await processQuery(query, null);
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

// Dynamic styling for chips
document.head.insertAdjacentHTML("beforeend", `<style>
.chip.active { background: var(--primary-light); color: var(--primary); border-color: var(--primary); }
</style>`);

window.switchTab = function(tabId) {
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to the selected tab
    const target = document.getElementById('nav-' + tabId);
    if (target) {
        target.classList.add('active');
    }
};
