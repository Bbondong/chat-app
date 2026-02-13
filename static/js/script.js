// Fonction pour envoyer un message à ChatGPT
async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    
    if (!message) {
        alert('Veuillez entrer un message');
        return;
    }
    
    // Ajouter le message de l'utilisateur au chat
    addMessage(message, 'user');
    userInput.value = '';
    
    // Afficher un indicateur de chargement
    const loadingId = addLoadingMessage();
    
    try {
        // Envoyer la requête à l'API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Supprimer le message de chargement
        removeLoadingMessage(loadingId);
        
        if (response.ok) {
            addMessage(data.response, 'bot');
        } else {
            addMessage(`Erreur: ${data.error}`, 'bot');
        }
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage(`Erreur de connexion: ${error.message}`, 'bot');
    }
}

// Fonction pour ajouter un message au chat
function addMessage(text, sender) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `<strong>${sender === 'user' ? 'Vous' : 'IA'}:</strong> ${escapeHtml(text)}`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Fonction pour ajouter un message de chargement
function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    const loadingId = 'loading-' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.className = 'message bot';
    loadingDiv.innerHTML = '<strong>IA:</strong> <i class="fas fa-spinner fa-spin"></i> Réflexion en cours...';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return loadingId;
}

// Fonction pour supprimer le message de chargement
function removeLoadingMessage(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Fonction pour échapper le HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Tester le VPN
async function testVPN() {
    const ipElement = document.getElementById('current-ip');
    const statusElement = document.getElementById('vpn-status');
    
    ipElement.textContent = 'Test en cours...';
    statusElement.textContent = 'Test en cours';
    statusElement.className = 'status-offline';
    
    try {
        const response = await fetch('/api/vpn-test');
        const data = await response.json();
        
        if (data.success) {
            ipElement.textContent = data.ip;
            statusElement.textContent = `Connecté (${data.method})`;
            statusElement.className = 'status-online';
            
            if (data.method.includes('VPN')) {
                showNotification('VPN actif avec IP: ' + data.ip);
            }
        } else {
            ipElement.textContent = 'Erreur';
            statusElement.textContent = 'Échec du test';
            statusElement.className = 'status-offline';
        }
    } catch (error) {
        ipElement.textContent = 'Erreur de connexion';
        statusElement.textContent = 'Hors ligne';
        statusElement.className = 'status-offline';
    }
}

// Obtenir la liste des proxies
async function getProxies() {
    const proxiesList = document.getElementById('proxies-list');
    const proxiesContent = document.getElementById('proxies-content');
    
    if (proxiesList.style.display === 'none') {
        proxiesContent.innerHTML = '<div class="proxy-item">Chargement...</div>';
        proxiesList.style.display = 'block';
        
        try {
            const response = await fetch('/api/get-proxies');
            const data = await response.json();
            
            if (data.success) {
                proxiesContent.innerHTML = '';
                data.proxies.forEach(proxy => {
                    const proxyDiv = document.createElement('div');
                    proxyDiv.className = 'proxy-item';
                    proxyDiv.textContent = proxy;
                    proxiesContent.appendChild(proxyDiv);
                });
                
                if (data.count > 10) {
                    const moreDiv = document.createElement('div');
                    moreDiv.className = 'proxy-item';
                    moreDiv.style.textAlign = 'center';
                    moreDiv.textContent = `... et ${data.count - 10} autres`;
                    proxiesContent.appendChild(moreDiv);
                }
            } else {
                proxiesContent.innerHTML = `<div class="proxy-item">Erreur: ${data.error}</div>`;
            }
        } catch (error) {
            proxiesContent.innerHTML = '<div class="proxy-item">Erreur de chargement</div>';
        }
    } else {
        proxiesList.style.display = 'none';
    }
}

// Afficher une notification
function showNotification(message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Application IA', { body: message });
    } else {
        // Fallback à une alerte
        alert(message);
    }
}

// Permettre d'envoyer le message avec Entrée (sans Shift)
document.getElementById('user-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Tester l'IP au chargement
window.onload = function() {
    testVPN();
    
    // Demander la permission pour les notifications
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
};