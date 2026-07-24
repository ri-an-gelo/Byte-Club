if (chatWithId) {
    const messagesContainer = document.getElementById('messages-container');
    const messageInput = document.getElementById('message-input');
    
    let isScrolledToBottom = true;

    messagesContainer.addEventListener('scroll', () => {
        isScrolledToBottom = messagesContainer.scrollHeight - messagesContainer.clientHeight <= messagesContainer.scrollTop + 5;
    });

    function fetchMessages() {
        fetch(`/api/messages/${chatWithId}`)
            .then(res => res.json())
            .then(messages => {
                messagesContainer.innerHTML = '';
                messages.forEach(msg => {
                    const div = document.createElement('div');
                    const isMe = msg.sender_name === currentUsername;
                    div.className = `message-bubble ${isMe ? 'me' : 'them'}`;
                    
                    let html = `<strong>${msg.sender_name}</strong><br>${msg.text}`;
                    
                    if(msg.severity === 'flagged' || msg.severity === 'high') {
                         html += `<div class="system-msg">⚠️ Message flagged: ${msg.reason}</div>`;
                    }
                    
                    div.innerHTML = html;
                    messagesContainer.appendChild(div);
                });
                
                if (isScrolledToBottom) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            });
    }

    function sendMessage(chatId) {
        const text = messageInput.value.trim();
        if (!text) return;
        
        messageInput.disabled = true;

        fetch(`/api/messages/${chatId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        })
        .then(res => res.json())
        .then(data => {
            messageInput.disabled = false;
            if(data.status === 'ok') {
                messageInput.value = '';
                fetchMessages();
                setTimeout(() => messageInput.focus(), 0);
            }
        }).catch(() => {
            messageInput.disabled = false;
        });
    }

    messageInput.addEventListener('keypress', function(e) {
        if(e.key === 'Enter') {
            sendMessage(chatWithId);
        }
    });

    // Poll every 3 seconds
    fetchMessages();
    setInterval(fetchMessages, 3000);
}
