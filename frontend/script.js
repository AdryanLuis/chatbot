document.addEventListener('DOMContentLoaded', async () => {
    console.log("DOM completamente carregado - inicializando chatbot");

    const sendButton = document.getElementById('send-button');
    const userInput = document.getElementById('user-input');
    const chatLog = document.getElementById('chat-log');
    const newChatButton = document.getElementById('new-chat-button');
    const chatHistoryList = document.querySelector('.chat-history-list');
    const chatInputArea = document.getElementById('chat-input-area');

    let currentChatId = null;


    async function askToDeleteChat(chatId, chatTitle, liElement) {
        const isConfirmed = confirm(`Tem certeza que deseja excluir o chat "${chatTitle}"? \nEsta ação não pode ser desfeita.`);

        if (!isConfirmed) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:3000/api/chat/${chatId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Falha ao excluir chat');
            }

            liElement.remove();

            if (currentChatId === chatId) {
                console.log("Chat atual foi excluído. Iniciando um novo chat.");
                iniciarNovoChat();
            }

        } catch (error) {
            console.error("Erro ao excluir chat:", error);
            alert("Não foi possível excluir o chat. Tente novamente.");
        }
    }

    const themeToggle = document.getElementById('theme-toggle');

    function setTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
            themeToggle.textContent = '☀️';
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-mode');
            themeToggle.textContent = '🌙'; // Ícone de lua
            localStorage.setItem('theme', 'light');
        }
    }

    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme');
        if (currentTheme === 'dark') {
            setTheme('light');
        } else {
            setTheme('dark');
        }
    });



    async function loadChatList() {
        console.log("Carregando lista de chats...");
        try {
            const response = await fetch('http://localhost:3000/api/chats');
            if (!response.ok) throw new Error('Falha ao carregar chats');
            const chats = await response.json();

            chatHistoryList.innerHTML = '';
            chats.forEach(chat => {
                const li = document.createElement('li');

                const a = createChatLink(chat.id, chat.title);

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-chat-btn';
                deleteBtn.textContent = '🗑️';
                deleteBtn.title = 'Excluir chat';

                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    askToDeleteChat(chat.id, chat.title, li);
                });

                li.appendChild(a);
                li.appendChild(deleteBtn);

                chatHistoryList.appendChild(li);
            });
            console.log("Lista de chats carregada.");
        } catch (error) {
            console.error('Erro ao carregar lista de chats:', error);
        }
    }

    function createChatLink(id, title) {
        const a = document.createElement('a');
        a.href = 'javascript:void(0)';
        a.textContent = title || "Chat sem título";
        a.setAttribute('data-chat-id', id);
        a.addEventListener('click', (e) => {
            console.log('Clicou no chat:', id);
            e.preventDefault();
            e.stopPropagation();
            document.querySelectorAll('.chat-history-list a').forEach(el => el.classList.remove('active'));
            a.classList.add('active');
            loadChatHistory(id);
        });
        return a;
    }

    async function loadChatHistory(chatId) {
        console.log(`Carregando histórico do chat: ${chatId}`);
        currentChatId = chatId;
        chatLog.innerHTML = '<div class="message bot-message"><p>Carregando histórico...</p></div>';

        try {
            const response = await fetch(`http://localhost:3000/api/chat/${chatId}`);
            if (!response.ok) throw new Error('Falha ao carregar histórico');
            const messages = await response.json();

            chatLog.innerHTML = '';
            if (messages.length === 0) {
                adicionarMensagem("bot", "Este chat está vazio. Comece a conversa!");
            } else {
                messages.forEach(msg => {
                    const autor = (msg.role === 'human') ? 'user' : 'bot';
                    adicionarMensagem(autor, msg.content);
                });
            }
        } catch (error) {
            console.error('Erro ao carregar histórico do chat:', error);
            chatLog.innerHTML = '<div class="message bot-message"><p>Erro ao carregar chat.</p></div>';
        }
    }

    function iniciarNovoChat(e) {
        console.log("Iniciando novo chat...");
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        currentChatId = null;
        chatLog.innerHTML = '';
        adicionarMensagem("bot", "Olá! Eu sou o Chatbot. Como posso ajudar você hoje?");
        document.querySelectorAll('.chat-history-list a').forEach(el => el.classList.remove('active'));
    }

    async function enviarMensagem() {
        console.log("=== ENVIAR MENSAGEM INICIADO ===");

        const mensagem = userInput.value.trim();
        if (mensagem === '') return;

        adicionarMensagem("user", mensagem);
        userInput.value = '';

        const botMessageElement = adicionarMensagem("bot", "", "streaming");
        const pElement = botMessageElement.querySelector('p');

        if (!pElement) {
            console.error("Falha ao criar elemento <p> para o bot.");
            return;
        }

        try {
            console.log("Fazendo requisição (stream) para o backend...");
            const response = await fetch('http://localhost:3000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: mensagem,
                    chatId: currentChatId
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Erro HTTP: ${response.status}`);
            }

            const newChatId = response.headers.get('X-Chat-Id');
            const newChatTitle = response.headers.get('X-Chat-Title');

            if (newChatId && newChatTitle && !currentChatId) {
                currentChatId = newChatId;

                const li = document.createElement('li');

                const a = createChatLink(newChatId, newChatTitle);
                a.classList.add('active');

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-chat-btn';
                deleteBtn.textContent = '🗑️';
                deleteBtn.title = 'Excluir chat';

                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    askToDeleteChat(newChatId, newChatTitle, li);
                });

                li.appendChild(a);
                li.appendChild(deleteBtn);

                document.querySelectorAll('.chat-history-list a').forEach(el => el.classList.remove('active'));

                chatHistoryList.prepend(li);
            }


            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullResponseText = "";

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    console.log("Stream finalizado.");
                    break;
                }

                const textChunk = decoder.decode(value, { stream: true });
                fullResponseText += textChunk;

                pElement.textContent = fullResponseText;

                chatLog.scrollTop = chatLog.scrollHeight;
            }
            pElement.remove();

            const finalHtml = formatarMensagemBot(fullResponseText);
            botMessageElement.innerHTML = finalHtml;

            chatLog.scrollTop = chatLog.scrollHeight;



        } catch (error) {
            console.error("ERRO ao enviar mensagem (stream):", error);
            botMessageElement.innerHTML = `<p>Desculpe, algo deu errado: ${error.message}</p>`;
        }
    }

    function formatarMensagemBot(texto) {
        if (!texto) return "<p>(Resposta vazia)</p>";

        const html = marked.parse(texto);

        return html;
    }

    function adicionarMensagem(autor, texto, tipo = "normal") {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        if (autor === 'user' || autor === 'human') {
            messageDiv.classList.add('user-message');
            messageDiv.innerHTML = `<p>${texto || "Mensagem vazia"}</p>`;
        } else {
            messageDiv.classList.add('bot-message');

            if (tipo === "typing") {
                messageDiv.classList.add('typing-indicator');
                messageDiv.innerHTML = `<span></span><span></span><span></span>`;

            } else if (tipo === "streaming") {
                messageDiv.innerHTML = `<p></p>`;

            } else {
                messageDiv.innerHTML = formatarMensagemBot(texto);
            }
        }

        chatLog.appendChild(messageDiv);
        chatLog.scrollTop = chatLog.scrollHeight;
        return messageDiv;
    }


    chatInputArea.addEventListener('submit', function (e) {
        console.log('Submit do formulário detectado e prevenido.');


        e.preventDefault();


        enviarMensagem();
    });

    newChatButton.addEventListener('click', function (e) {
        console.log('Clique no novo chat');
        e.preventDefault();
        e.stopPropagation();
        iniciarNovoChat(e);
    });


    console.log("Iniciando carregamento...");
    await loadChatList();

    const primeiroChat = document.querySelector('.chat-history-list a');
    if (primeiroChat) {
        console.log("Carregando primeiro chat da lista");
        primeiroChat.click();
    } else {
        console.log("Nenhum chat encontrado - iniciando novo");
        iniciarNovoChat();
    }

    console.log("Chatbot inicializado com sucesso!");
});


window.addEventListener('beforeunload', function (e) {
    console.log('Tentativa de recarregar página detectada');
});