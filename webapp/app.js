// ═══════════ TELEGRAM INIT ═══════════
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
    try {
        tg.setHeaderColor('#14061a');
        tg.setBackgroundColor('#14061a');
    } catch (e) { /* старые клиенты */ }
}

// ═══════════ DOM ═══════════
const $ = (sel) => document.querySelector(sel);
const loader       = $('#loader');
const screenMenu   = $('#screen-menu');
const screenPov    = $('#screen-pov');
const screenStory  = $('#screen-story');
const storiesList  = $('#stories-list');
const storyImage   = $('#story-image');
const storyText    = $('#story-text');
const choicesBox   = $('#choices');

// ═══════════ STATE ═══════════
let STORIES = {};        // загрузим из stories.json
let currentStoryKey = null;
let currentPov = 'first';
let currentNodeId = null;

// ═══════════ HAPTIC ═══════════
function haptic(type = 'light') {
    if (!tg?.HapticFeedback) return;
    try {
        if (type === 'light')   tg.HapticFeedback.impactOccurred('light');
        if (type === 'medium')  tg.HapticFeedback.impactOccurred('medium');
        if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
    } catch (e) {}
}

// ═══════════ SCREENS ═══════════
function showScreen(screen) {
    [screenMenu, screenPov, screenStory].forEach(s => s.classList.add('hidden'));
    screen.classList.remove('hidden');
    screen.scrollTop = 0;
}

// ═══════════ LOAD DATA ═══════════
async function loadStories() {
    try {
        const res = await fetch('stories.json');
        STORIES = await res.json();
    } catch (e) {
        console.error('Не удалось загрузить stories.json', e);
        STORIES = {};
    }
}

// ═══════════ MENU ═══════════
function renderMenu() {
    storiesList.innerHTML = '';

    Object.entries(STORIES).forEach(([key, story], i) => {
        const card = document.createElement('div');
        card.className = 'story-card';
        card.style.animationDelay = `${i * 0.1}s`;

        const isDev = story.status === 'in_development';
        const badge = isDev
            ? '<span class="card-badge dev">🚧 В разработке</span>'
            : '<span class="card-badge">💗 Доступна</span>';

        card.innerHTML = `
            <h3>${story.title}</h3>
            <div class="card-sub">${story.heroes.map(h => h.name).join(' · ')}</div>
            ${badge}
        `;

        card.onclick = () => {
            haptic('light');
            if (isDev) {
                alert('🚧 Эта история ещё в разработке. Заходи позже!');
                return;
            }
            openPovScreen(key);
        };

        storiesList.appendChild(card);
    });

    showScreen(screenMenu);
}

// ═══════════ POV ═══════════
function openPovScreen(storyKey) {
    currentStoryKey = storyKey;
    const story = STORIES[storyKey];

    $('#pov-title').textContent = story.title;
    $('#pov-setting').textContent = story.setting;

    showScreen(screenPov);
}

$('#pov-first').onclick = () => {
    haptic('medium');
    startStory(currentStoryKey, 'first');
};

$('#pov-third').onclick = () => {
    haptic('medium');
    startStory(currentStoryKey, 'third');
};

$('#pov-back').onclick = () => {
    haptic('light');
    renderMenu();
};

// ═══════════ STORY ═══════════
function startStory(storyKey, pov) {
    currentPov = pov;
    const story = STORIES[storyKey];
    renderNode(storyKey, story.start, pov, false);
}

function renderNode(storyKey, nodeId, pov, animate = true) {
    const story = STORIES[storyKey];
    const node = story.nodes[nodeId];
    if (!node) return;

    currentNodeId = nodeId;

    const text = pov === 'first' ? node.text_first : node.text_third;

    // Смена картинки с плавным переходом
    if (animate) {
        storyImage.classList.add('loading');
    }

    storyImage.onload = () => storyImage.classList.remove('loading');
    storyImage.src = node.image || '';

    setTimeout(() => {
        storyText.textContent = text || '';
    }, animate ? 200 : 0);

    // Кнопки выбора
    choicesBox.innerHTML = '';
    const choices = node.choices || [];

    if (choices.length === 0) {
        // Концовка
        const btn = document.createElement('button');
        btn.className = 'btn btn-primary';
        btn.innerHTML = `
            <span class="btn-emoji">🩷</span>
            <span class="btn-label">Пройти заново</span>
        `;
        btn.onclick = () => {
            haptic('success');
            openPovScreen(storyKey);
        };
        choicesBox.appendChild(btn);
    } else {
        choices.forEach(([label, next], i) => {
            const btn = document.createElement('button');
            btn.className = 'choice-btn';
            btn.textContent = label;
            btn.style.animationDelay = `${i * 0.08}s`;
            btn.onclick = () => {
                haptic('medium');
                renderNode(storyKey, next, pov, true);
            };
            choicesBox.appendChild(btn);
        });
    }

    // Кнопка «К историям» внизу
    $('#story-menu').onclick = () => {
        haptic('light');
        renderMenu();
    };

    if (animate) showScreen(screenStory);
}

// ═══════════ BOOT ═══════════
window.addEventListener('load', async () => {
    await loadStories();
    setTimeout(() => {
        loader.classList.add('hidden');
        renderMenu();
    }, 700);
});