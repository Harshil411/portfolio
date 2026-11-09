// Notebook runtime: run-on-scroll, the live model, J/K + Shift+Enter, the Code switch, theme, copy, Blacksburg time.
// All of it is enhancement. The server renders every output, so the page reads fine without this file.
(() => {
    const root = document.documentElement;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const queued = root.classList.contains('nb-io');
    const cells = [...document.querySelectorAll('.cell')];
    const code = cells.filter((c) => c.classList.contains('code'));
    const kernel = document.querySelector('.kernel');
    const kStates = document.querySelectorAll('.k-state');
    // Jupyter-style execution counter: server-rendered cells already read 1..n, so re-runs continue from n.
    let count = queued ? 0 : code.length, busy = 0;

    const setBusy = (d) => {
        busy = Math.max(0, busy + d);
        kernel.dataset.busy = busy > 0;
        kStates.forEach((s) => { s.textContent = busy > 0 ? 'busy' : 'idle'; });
    };
    const setN = (cell, v) => cell.querySelectorAll('.n').forEach((n) => { n.textContent = v; });
    const finish = (cell) => {
        cell.dataset.state = 'done';
        setN(cell, ++count);
        cell.classList.remove('ran'); void cell.offsetWidth; cell.classList.add('ran');
    };
    const run = (cell, then) => {
        cell.dataset.state = 'running'; setN(cell, '*'); setBusy(1);
        setTimeout(() => { finish(cell); setBusy(-1); if (then) then(); }, reduce ? 0 : 260);
    };

    // Cells execute as they scroll into view, one at a time, in reading order.
    if (queued) {
        const queue = [];
        let pumping = false;
        const pump = () => {
            const next = queue.shift();
            pumping = Boolean(next);
            if (next) run(next, pump);
        };
        code.forEach((c) => { c.dataset.state = 'queued'; setN(c, ' '); });
        const io = new IntersectionObserver((entries) => {
            entries.filter((e) => e.isIntersecting).map((e) => e.target)
                .sort((a, b) => code.indexOf(a) - code.indexOf(b))
                .forEach((c) => { io.unobserve(c); queue.push(c); });
            if (!pumping) pump();
        }, { rootMargin: '0px 0px -12% 0px', threshold: 0.15 });
        code.forEach((c) => io.observe(c));
    }

    // Live cell: a real POST /predict, debounced, with stale requests aborted.
    const form = document.getElementById('reading');
    const live = document.getElementById('model-cell');
    let predict = null;
    if (form) {
        const risk = live.querySelector('.risk');
        const ms = risk.querySelector('.ms');
        const sr = document.getElementById('risk-sr');
        const chips = form.querySelectorAll('.chip');
        const slider = (name) => form.querySelector(`input[type=range][data-for="${name}"]`);
        const decimals = (el) => (el.step.split('.')[1] || '').length;
        const show = (box) => { live.querySelector(`[data-v="${box.name}"]`).textContent = Number(box.value).toFixed(decimals(box)); };
        const fail = (message) => {
            live.dataset.state = 'error'; setN(live, '!');
            ms.textContent = `✗ ${message}`;
            sr.textContent = message;
        };
        let timer, ctrl;
        predict = async () => {
            clearTimeout(timer);
            if (ctrl) ctrl.abort();
            const invalid = [...form.querySelectorAll('input[type=number]')].find((box) => !box.checkValidity());
            if (invalid) {
                const label = form.querySelector(`label[for="${invalid.id}"]`).textContent;
                return fail(`${label} must be between ${invalid.min} and ${invalid.max} ${invalid.nextElementSibling.textContent}`);
            }
            ctrl = new AbortController();
            live.dataset.state = 'running'; setN(live, '*'); setBusy(1);
            const t0 = performance.now();
            try {
                const res = await fetch('/predict', { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' }, signal: ctrl.signal });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const d = await res.json();
                const p = d.probability.defect, bad = d.prediction === 1;
                risk.dataset.verdict = bad ? 'bad' : 'ok';
                risk.querySelector('.risk-p').textContent = `${(p * 100).toFixed(1)}%`;
                risk.querySelector('.verdict-t').textContent = bad ? 'Defect likely' : 'No defect expected';
                risk.querySelector('.fill').style.setProperty('--p', p);
                ms.textContent = `✓ answered in ${Math.round(performance.now() - t0)} ms`;
                sr.textContent = `Defect probability ${(p * 100).toFixed(1)} percent: ${bad ? 'defect likely' : 'no defect'}.`;
                finish(live);
            } catch (err) {
                if (err.name !== 'AbortError') fail(`${err.message}: model unavailable, try again`);
            } finally { setBusy(-1); }
        };
        form.addEventListener('input', (e) => {
            const el = e.target;
            const box = el.type === 'range' ? form.elements[el.dataset.for] : el;
            if (el.type === 'range') box.value = el.value;
            else if (box.checkValidity()) slider(box.name).value = box.value;
            show(box);
            chips.forEach((b) => b.setAttribute('aria-pressed', 'false'));
            clearTimeout(timer); timer = setTimeout(predict, 180);
        });
        form.addEventListener('submit', (e) => { e.preventDefault(); predict(); });
        chips.forEach((btn) => btn.addEventListener('click', () => {
            Object.entries(JSON.parse(btn.dataset.preset)).forEach(([name, v]) => {
                form.elements[name].value = v; slider(name).value = v; show(form.elements[name]);
            });
            chips.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
            predict();
        }));
    }

    // Keyboard: J / K select cells, Shift+Enter re-runs the selected one.
    let active = -1;
    const select = (i, scroll = true) => {
        active = Math.max(0, Math.min(cells.length - 1, i));
        cells.forEach((c, j) => c.classList.toggle('is-active', j === active));
        if (scroll) cells[active].scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
    };
    document.addEventListener('keydown', (e) => {
        if (e.metaKey || e.ctrlKey || e.altKey || !(e.target === document.body || e.target.id === 'nb')) return;
        const k = e.key.toLowerCase();
        if (k === 'j') select(active + 1);
        else if (k === 'k') select(active - 1);
        else if (e.key === 'Enter' && e.shiftKey && active >= 0) {
            e.preventDefault();
            const c = cells[active];
            if (c === live && predict) predict();
            else if (code.includes(c)) run(c);
        }
    });
    cells.forEach((c, i) => c.addEventListener('mousedown', () => select(i, false)));

    // Code switch: hide inputs, keep outputs (like Voilà or nbconvert --no-input). The head script applied the saved choice.
    const codeBtn = document.querySelector('.btn-code');
    const syncCode = () => codeBtn.setAttribute('aria-pressed', !root.classList.contains('code-off'));
    document.querySelectorAll('.btn-code, [data-code-toggle]').forEach((b) => b.addEventListener('click', () => {
        root.classList.toggle('code-off');
        try { localStorage.setItem('code', root.classList.contains('code-off') ? 'off' : 'on'); } catch (e) {}
        syncCode();
    }));
    syncCode();

    // Theme: system by default, the toggle's choice is remembered.
    const toggle = document.querySelector('.theme-toggle');
    const prefersDark = matchMedia('(prefers-color-scheme: dark)');
    const isDark = () => (root.dataset.theme || (prefersDark.matches ? 'dark' : 'light')) === 'dark';
    const syncTheme = () => toggle.setAttribute('aria-pressed', isDark());
    syncTheme(); prefersDark.addEventListener('change', syncTheme);
    toggle.addEventListener('click', () => {
        root.dataset.theme = isDark() ? 'light' : 'dark';
        try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
        syncTheme();
    });

    // Copy buttons; without a clipboard, a data-fallback link (mailto:) opens instead.
    const copyStatus = document.getElementById('copy-status');
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-copy]');
        if (!btn) return;
        const label = btn.dataset.label || (btn.dataset.label = btn.textContent);
        try {
            await navigator.clipboard.writeText(btn.dataset.copy);
            btn.textContent = 'Copied'; copyStatus.textContent = 'Copied to clipboard';
        } catch (err) {
            if (btn.dataset.fallback) return void window.open(btn.dataset.fallback, '_self');
            btn.textContent = 'Copy unavailable';
        }
        setTimeout(() => { btn.textContent = label; copyStatus.textContent = ''; }, 2000);
    });

    const clock = document.getElementById('bb-time');
    if (clock) {
        const fmt = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit' });
        const tick = () => { clock.textContent = fmt.format(new Date()); };
        tick(); setInterval(tick, 30000);
    }
})();
