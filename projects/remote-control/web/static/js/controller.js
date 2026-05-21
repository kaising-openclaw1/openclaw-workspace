/**
 * RemoteEye v3.0 Pro 主控端 — 对标 TeamViewer/向日葵/AnyDesk
 * 功能: 设备管理 · 连接码 · 差分渲染 · 文件传输 · 剪贴板 · 远程Shell
 *       · 质量监控 · 录制回放 · 拖拽上传 · 快捷按键 · 截屏保存 · 远程光标
 */
class RemoteController {
    constructor() {
        // 连接
        this.ws = null;
        this.sessionId = null;
        this.currentDevice = null;
        this.isConnected = false;
        this.devices = [];

        // 连接码
        this.myConnId = null;
        this.myConnPass = null;

        // 屏幕
        this.canvas = document.getElementById('screen-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.placeholder = document.getElementById('placeholder');
        this.fullFrame = null;
        this.screenScaleX = 1;
        this.screenScaleY = 1;
        this.showRemoteCursor = true;

        // 质量监控
        this.quality = {
            fpsCounter: 0, fpsLastTime: Date.now(), fps: 0,
            latencies: [], totalBytesReceived: 0, bytesWindow: 0, lastBandwidthCheck: Date.now()
        };

        // 文件浏览
        this.fileBrowser = { currentPath: '/', reqCounter: 0 };
        this.selectedFiles = [];

        // Shell
        this.shellActive = false;

        // 显示器
        this.monitors = [];
        this.currentMonitor = 0;

        // 录制回放
        this.recordingPlayer = null;

        // 拖拽
        this.dragCounter = 0;

        this.init();
    }

    init() {
        this.bindTabs();
        this.bindConnectForm();
        this.bindCanvasEvents();
        this.bindToolbar();
        this.bindSliders();
        this.bindFileBrowser();
        this.bindClipboard();
        this.bindShell();
        this.bindSpecialKeys();
        this.bindKeyboardShortcuts();
        this.bindDragDrop();
        this.bindChat();  // 💬 聊天绑定
        this.connect();
    }

    /* ===================== WebSocket ===================== */

    connect() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${proto}//${location.host}/ws/controller`);
        this.ws.onopen = () => this.setStatus('online', '已连接');
        this.ws.onclose = () => {
            this.isConnected = false; this.sessionId = null;
            this.setStatus('offline', '未连接'); this.showPlaceholder();
            setTimeout(() => this.connect(), 5000);
        };
        this.ws.onerror = () => this.updateStatus('连接错误');
        this.ws.onmessage = e => { try { this.handleMessage(JSON.parse(e.data)); } catch(_) {} };
    }

    send(data) {
        if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(data));
    }

    handleMessage(msg) {
        const handler = this[`on_${msg.type}`];
        if (handler) handler.call(this, msg);
    }

    /* ===================== Tabs ===================== */

    bindTabs() {
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
            });
        });
    }

    /* ===================== 设备列表 ===================== */

    on_device_list(msg) {
        this.devices = msg.devices || [];
        const el = document.getElementById('device-list');
        if (!this.devices.length) { el.innerHTML = '<div class="empty-state">暂无在线设备</div>'; return; }
        el.innerHTML = this.devices.map(d => `
            <div class="device-card fade-in ${d.is_controlled ? 'controlled' : ''}" data-id="${d.device_id}">
                <div class="device-header">
                    <span class="device-name"><span class="device-status"></span>${d.name}</span>
                    <span class="device-badge">${d.platform}</span>
                </div>
                <div class="device-info">
                    <div>📺 ${d.resolution}</div>
                    ${d.monitors?.length > 1 ? `<div>🖥️ ${d.monitors.length} 显示器</div>` : ''}
                    <div>${d.is_controlled ? '🔴 控制中' : '🟢 可用'}</div>
                </div>
            </div>
        `).join('');
        el.querySelectorAll('.device-card:not(.controlled)').forEach(el => {
            el.addEventListener('click', () => this.connectToDevice(el.dataset.id));
        });
    }

    connectToDevice(deviceId) {
        if (this.sessionId) this.disconnect();
        const device = this.devices.find(d => d.device_id === deviceId);
        if (!device) return;
        this.currentDevice = device;
        this.send({ type: 'connect_device', device_id: deviceId,
            quality: +document.getElementById('quality-slider').value,
            fps: +document.getElementById('fps-slider').value });
        this.updateStatus(`正在连接 ${device.name}...`);
    }

    /* ===================== 连接码 ===================== */

    on_connection_card(msg) {
        this.myConnId = msg.connection_id; this.myConnPass = msg.connection_password;
        const card = document.getElementById('my-conn-card');
        card.style.display = 'block';
        document.getElementById('my-conn-id').textContent = msg.connection_id;
        document.getElementById('my-conn-pass').textContent = msg.connection_password;
        if (msg.expires_in) document.getElementById('conn-expires').textContent = `${Math.floor(msg.expires_in / 60)} 分钟后过期`;
    }

    bindConnectForm() {
        document.getElementById('btn-connect-code').addEventListener('click', () => {
            const id = document.getElementById('conn-id-input').value.trim();
            const pass = document.getElementById('conn-pass-input').value.trim();
            const mode = document.getElementById('conn-mode').value;
            if (!id || !pass) { this.updateStatus('请输入连接 ID 和密码'); return; }
            if (id.length !== 9 || pass.length !== 6) { this.updateStatus('ID 为 9 位，密码为 6 位'); return; }
            this.send({ type: 'connect_by_code', code: id, password: pass, mode });
        });
        document.getElementById('btn-refresh-code')?.addEventListener('click', () => {
            this.send({ type: 'refresh_connection_card' });
        });
        document.getElementById('btn-copy-code')?.addEventListener('click', () => {
            const text = `ID: ${this.myConnId}  密码: ${this.myConnPass}`;
            navigator.clipboard.writeText(text).then(() => this.toast('✅ 已复制到剪贴板'));
        });
    }

    /* ===================== 连接/断开 ===================== */

    on_connected(msg) {
        this.sessionId = msg.session_id; this.isConnected = true;
        this.currentDevice = { name: msg.device_name };
        this.monitors = msg.monitors || [];
        this.placeholder.style.display = 'none'; this.canvas.style.display = 'block';
        document.getElementById('toolbar').style.display = 'flex';
        document.getElementById('session-device').textContent = msg.device_name;
        if (msg.system_info) {
            const si = msg.system_info;
            if (si.cpu) this.updateStatus(`✅ ${msg.device_name} · ${si.os} · CPU ${si.cpu.usage}% · 内存 ${si.memory?.percent}%`);
        } else this.updateStatus(`✅ 已连接到 ${msg.device_name}`);
    }

    on_disconnected() {
        this.isConnected = false; this.sessionId = null; this.currentDevice = null;
        this.fullFrame = null; this.shellActive = false; this.selectedFiles = [];
        this.showPlaceholder(); document.getElementById('toolbar').style.display = 'none';
        document.getElementById('quality-overlay').classList.remove('visible');
        document.getElementById('quality-panel')?.style && (document.getElementById('quality-panel').style.display = 'none');
        this.updateStatus('已断开'); this.disableShell();
        if (this.recordingPlayer) this.stopPlayer();
    }

    showPlaceholder() {
        this.placeholder.style.display = 'flex'; this.canvas.style.display = 'none';
    }

    disconnect() {
        if (this.shellActive) this.toggleShell();
        this.send({ type: 'disconnect' }); this.on_disconnected();
    }

    /* ===================== 截屏渲染（差分） ===================== */

    on_screenshot(msg) {
        const t0 = performance.now();
        const data = msg.data;
        if (data.type === 'full') {
            const img = new Image();
            img.onload = () => {
                this.canvas.width = img.width; this.canvas.height = img.height;
                this.ctx.drawImage(img, 0, 0); this.fullFrame = img;
                this._updateScale();
            };
            img.src = `data:image/jpeg;base64,${data.data}`;
        } else if (data.type === 'diff' && data.blocks) {
            let pending = data.blocks.length;
            if (pending === 0) return;
            data.blocks.forEach(b => {
                const img = new Image();
                img.onload = () => {
                    this.ctx.drawImage(img, b.x, b.y, b.w, b.h);
                    if (--pending === 0) this._updateScale();
                };
                img.src = `data:image/jpeg;base64,${b.data}`;
            });
        } else if (data.type === 'skip') return;

        this.quality.fpsCounter++;
        const now = Date.now();
        const msgSize = JSON.stringify(msg).length;
        this.quality.totalBytesReceived += msgSize;
        this.quality.bytesWindow += msgSize;
        this.quality.latencies.push(performance.now() - t0);
        if (this.quality.latencies.length > 30) this.quality.latencies.shift();
        if (now - this.quality.fpsLastTime >= 1000) {
            this.quality.fps = this.quality.fpsCounter;
            this.quality.fpsCounter = 0; this.quality.fpsLastTime = now;
            document.getElementById('fps-badge').textContent = `${this.quality.fps} fps`;
        }
    }

    _updateScale() {
        const r = this.canvas.getBoundingClientRect();
        this.screenScaleX = this.canvas.width / r.width;
        this.screenScaleY = this.canvas.height / r.height;
    }

    /* ===================== 输入控制 ===================== */

    sendInput(action, data = {}) {
        if (!this.sessionId) return;
        this.send({ type: 'input', session_id: this.sessionId, action, ...data });
    }

    _canvasCoords(e) {
        const r = this.canvas.getBoundingClientRect();
        return {
            x: Math.round((e.clientX - r.left) * this.screenScaleX),
            y: Math.round((e.clientY - r.top) * this.screenScaleY)
        };
    }

    bindCanvasEvents() {
        // 鼠标移动 + 远程光标
        this.canvas.addEventListener('mousemove', e => {
            const { x, y } = this._canvasCoords(e);
            this.sendInput('mouse_move', { x, y });
            this._moveCursor(e);
        });

        // 鼠标点击
        this.canvas.addEventListener('mousedown', e => {
            e.preventDefault();
            const { x, y } = this._canvasCoords(e);
            const button = e.button === 2 ? 'right' : e.button === 1 ? 'middle' : 'left';
            this.sendInput('mouse_click', { x, y, button });
        });

        this.canvas.addEventListener('contextmenu', e => e.preventDefault());

        // 滚轮
        this.canvas.addEventListener('wheel', e => {
            e.preventDefault();
            this.sendInput('mouse_scroll', { delta: -Math.round(e.deltaY / 10) });
        }, { passive: false });

        // 触摸支持（移动端）
        let lastTouch = null;
        this.canvas.addEventListener('touchstart', e => {
            e.preventDefault();
            if (e.touches.length === 1) {
                const t = e.touches[0];
                const { x, y } = this._canvasCoords(t);
                this.sendInput('mouse_click', { x, y, button: 'left' });
                lastTouch = { x: t.clientX, y: t.clientY };
            }
        }, { passive: false });

        this.canvas.addEventListener('touchmove', e => {
            e.preventDefault();
            if (e.touches.length === 1 && lastTouch) {
                const t = e.touches[0];
                const { x, y } = this._canvasCoords(t);
                this.sendInput('mouse_move', { x, y });
                lastTouch = { x: t.clientX, y: t.clientY };
            }
        }, { passive: false });

        // 键盘（排除输入框）
        document.addEventListener('keydown', e => {
            if (!this.sessionId || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
            // Ctrl+S → 截屏
            if (e.ctrlKey && e.key === 's') { e.preventDefault(); this.takeScreenshot(); return; }
            // Ctrl+W → 断开
            if (e.ctrlKey && e.key === 'w') { e.preventDefault(); this.disconnect(); return; }
            // Ctrl+Q → 质量面板
            if (e.ctrlKey && e.key === 'q') {
                e.preventDefault();
                document.getElementById('quality-overlay').classList.toggle('visible');
                return;
            }
            this.sendInput('key_press', { key: e.key });
        });
        document.addEventListener('keyup', e => {
            if (!this.sessionId || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
            this.sendInput('key_release', { key: e.key });
        });
    }

    /* ===================== 远程光标 ===================== */

    _moveCursor(e) {
        if (!this.showRemoteCursor) return;
        const cursor = document.getElementById('remote-cursor');
        if (!cursor || cursor.style.display === 'none') return;
        const rect = document.getElementById('remote-screen').getBoundingClientRect();
        cursor.style.left = (e.clientX - rect.left - 2) + 'px';
        cursor.style.top = (e.clientY - rect.top - 2) + 'px';
    }

    /* ===================== 工具栏 ===================== */

    bindToolbar() {
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
            document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
        });
        document.getElementById('btn-monitor')?.addEventListener('click', () => {
            if (this.monitors.length <= 1) { this.toast('只有一个显示器'); return; }
            this.currentMonitor = (this.currentMonitor + 1) % this.monitors.length;
            this.send({ type: 'switch_monitor', session_id: this.sessionId,
                monitor: this.monitors[this.currentMonitor].index || this.currentMonitor });
        });
        document.getElementById('btn-cursor-toggle')?.addEventListener('click', () => {
            this.showRemoteCursor = !this.showRemoteCursor;
            const cursor = document.getElementById('remote-cursor');
            cursor.style.display = this.showRemoteCursor ? 'block' : 'none';
            this.toast(this.showRemoteCursor ? '远程光标已开启' : '远程光标已关闭');
        });
        document.getElementById('btn-quality-toggle')?.addEventListener('click', () => {
            document.getElementById('quality-overlay').classList.toggle('visible');
        });
        document.getElementById('btn-screenshot')?.addEventListener('click', () => this.takeScreenshot());
        document.getElementById('btn-disconnect')?.addEventListener('click', () => this.disconnect());
    }

    /* ===================== 截屏保存 ===================== */

    takeScreenshot() {
        if (!this.canvas || !this.canvas.width) { this.toast('没有可截屏的画面'); return; }
        try {
            this.canvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const ts = new Date().toISOString().replace(/[:.]/g, '-');
                a.href = url; a.download = `RemoteEye_${ts}.png`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                URL.revokeObjectURL(url);
                this.toast('📸 截屏已保存');
            }, 'image/png');
        } catch(_) { this.toast('截屏失败'); }
    }

    /* ===================== 滑块 ===================== */

    bindSliders() {
        const q = document.getElementById('quality-slider');
        const qv = document.getElementById('quality-val');
        q?.addEventListener('input', () => { if (qv) qv.textContent = q.value; });
        const f = document.getElementById('fps-slider');
        const fv = document.getElementById('fps-val');
        f?.addEventListener('input', () => { if (fv) fv.textContent = f.value; });
    }

    /* ===================== 快捷按键 ===================== */

    bindSpecialKeys() {
        document.querySelectorAll('.special-key-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const combo = btn.dataset.key;
                if (!combo || !this.sessionId) return;
                const keys = combo.split('+');
                // 按下所有键
                keys.forEach(k => this.sendInput('key_press', { key: this._mapSpecialKey(k) }));
                // 短暂延迟后释放（逆序）
                setTimeout(() => {
                    [...keys].reverse().forEach(k => this.sendInput('key_release', { key: this._mapSpecialKey(k) }));
                }, 150);
                this.toast(`⌨️ 已发送 ${combo.toUpperCase()}`);
            });
        });
    }

    _mapSpecialKey(k) {
        const map = { ctrl: 'Control', alt: 'Alt', win: 'Meta', del: 'Delete', esc: 'Escape' };
        return map[k.toLowerCase()] || k;
    }

    /* ===================== 键盘快捷键 ===================== */

    bindKeyboardShortcuts() {
        // F11 → 全屏
        document.addEventListener('keydown', e => {
            if (e.key === 'F11' && !this.sessionId) {
                e.preventDefault();
                document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
            }
        });
    }

    /* ===================== 文件浏览器 ===================== */

    bindFileBrowser() {
        document.getElementById('btn-file-refresh')?.addEventListener('click', () => this.browseFiles());
        document.getElementById('btn-file-mkdir')?.addEventListener('click', () => {
            const name = prompt('文件夹名称:');
            if (!name) return;
            const path = this.fileBrowser.currentPath === '/' ? `/${name}` : `${this.fileBrowser.currentPath}/${name}`;
            this.send({ type: 'file_mkdir', path, session_id: this.sessionId });
        });
        document.getElementById('btn-file-upload')?.addEventListener('click', () => {
            document.getElementById('file-upload-input')?.click();
        });
        document.getElementById('file-upload-input')?.addEventListener('change', e => {
            Array.from(e.target.files).forEach(f => this.uploadFile(f));
            e.target.value = '';
        });
    }

    browseFiles(path = null) {
        if (!this.sessionId) return;
        this.send({ type: 'file_list', path: path || this.fileBrowser.currentPath, session_id: this.sessionId });
    }

    on_file_list_result(msg) {
        if (msg.error) { this.updateStatus(`❌ ${msg.error}`); return; }
        this.fileBrowser.currentPath = msg.path;
        this.selectedFiles = [];
        document.getElementById('file-path-bar').textContent = msg.path || '/';
        const listEl = document.getElementById('file-list');
        if (!msg.items?.length) { listEl.innerHTML = '<li class="empty-state">空目录</li>'; return; }

        // 父目录导航
        const items = msg.path !== '/' ? [{ name: '..', type: 'directory', path: msg.path.replace(/\/[^/]+$/, '') || '/' }] : [];
        items.push(...msg.items);

        listEl.innerHTML = items.map(item => `
            <li class="file-item" data-path="${item.path}" data-type="${item.type}" data-name="${item.name}">
                <span class="file-icon">${item.type === 'directory' ? (item.name === '..' ? '⬆️' : '📁') : this.fileIcon(item.name)}</span>
                <span class="file-name">${item.name}</span>
                <span class="file-size">${item.size != null ? this.formatSize(item.size) : ''}</span>
            </li>
        `).join('');

        listEl.querySelectorAll('.file-item').forEach(el => {
            // 双击进入/下载
            el.addEventListener('dblclick', () => {
                if (el.dataset.type === 'directory') this.browseFiles(el.dataset.path);
                else this.downloadFile(el.dataset.path);
            });
            // 单击选择
            el.addEventListener('click', () => {
                listEl.querySelectorAll('.file-item').forEach(i => i.classList.remove('selected'));
                el.classList.add('selected');
                this.selectedFiles = [el.dataset.path];
            });
            // 右键菜单
            el.addEventListener('contextmenu', e => {
                e.preventDefault();
                if (el.dataset.type !== 'directory') this._showFileContextMenu(e, el.dataset.path, el.dataset.name);
            });
        });
    }

    _showFileContextMenu(e, path, name) {
        // 简单 toast 操作提示
        const action = confirm(`对 "${name}" 执行操作？\n\n确定 = 下载\n取消 = 删除`);
        if (action) this.downloadFile(path);
        else if (confirm(`确定删除 "${name}"？`)) {
            this.send({ type: 'file_delete', path, session_id: this.sessionId });
        }
    }

    on_file_download_result(msg) {
        if (msg.error) { this.toast(`❌ 下载失败: ${msg.error}`); return; }
        try {
            const raw = atob(msg.data);
            const bytes = new Uint8Array([...raw].map(c => c.charCodeAt(0)));
            const blob = new Blob([bytes]);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = msg.name;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(url);
            this.toast(`✅ 下载完成: ${msg.name}`);
        } catch(_) { this.toast('❌ 下载失败'); }
    }

    on_file_upload_result(msg) {
        this.toast(msg.error ? `❌ 上传失败: ${msg.error}` : '✅ 上传成功');
        if (!msg.error) this.browseFiles();
    }

    on_file_delete_result(msg) {
        this.toast(msg.error ? '❌ 删除失败' : '✅ 已删除');
        if (!msg.error) this.browseFiles();
    }

    on_file_mkdir_result(msg) {
        this.toast(msg.error ? '❌ 创建失败' : '✅ 已创建');
        if (!msg.error) this.browseFiles();
    }

    downloadFile(path) {
        if (!this.sessionId) return;
        this.send({ type: 'file_download', path, session_id: this.sessionId });
        this.updateStatus('⬇️ 正在下载...');
    }

    uploadFile(file) {
        if (!this.sessionId) return;
        const reader = new FileReader();
        reader.onload = e => {
            const path = (this.fileBrowser.currentPath === '/' ? '' : this.fileBrowser.currentPath) + '/' + file.name;
            this.send({ type: 'file_upload', path, data: e.target.result.split(',')[1], session_id: this.sessionId });
            this.updateStatus(`⬆️ 正在上传: ${file.name}`);
        };
        reader.readAsDataURL(file);
    }

    fileIcon(name) {
        const ext = name.split('.').pop()?.toLowerCase();
        const map = { jpg:'🖼️',jpeg:'🖼️',png:'🖼️',gif:'🖼️',bmp:'🖼️',webp:'🖼️',mp4:'🎬',avi:'🎬',mkv:'🎬',mp3:'🎵',wav:'🎵',flac:'🎵',pdf:'📄',doc:'📄',docx:'📄',txt:'📄',xls:'📊',xlsx:'📊',ppt:'📑',zip:'📦',rar:'📦','7z':'📦',tar:'📦',gz:'📦',py:'🐍',js:'📜',ts:'📜',html:'🌐',css:'🎨',json:'📋',md:'📝',exe:'⚙️',dmg:'💿',deb:'📦',sh:'🔧' };
        return map[ext] || '📄';
    }

    formatSize(b) {
        if (b == null) return '';
        if (b < 1024) return b + ' B';
        if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
        if (b < 1073741824) return (b / 1048576).toFixed(1) + ' MB';
        return (b / 1073741824).toFixed(2) + ' GB';
    }

    /* ===================== 拖拽上传 ===================== */

    bindDragDrop() {
        const screen = document.getElementById('remote-screen');
        if (!screen) return;
        const dropZone = document.getElementById('drop-zone');

        screen.addEventListener('dragenter', e => { e.preventDefault(); this.dragCounter++; dropZone?.classList.add('visible'); });
        screen.addEventListener('dragleave', e => { e.preventDefault(); this.dragCounter--; if (this.dragCounter <= 0) { this.dragCounter = 0; dropZone?.classList.remove('visible'); } });
        screen.addEventListener('dragover', e => e.preventDefault());
        screen.addEventListener('drop', e => {
            e.preventDefault(); this.dragCounter = 0;
            dropZone?.classList.remove('visible');
            if (!this.sessionId) { this.toast('请先连接设备'); return; }
            const files = e.dataTransfer.files;
            if (files.length) {
                Array.from(files).forEach(f => this.uploadFile(f));
                this.toast(`📁 正在上传 ${files.length} 个文件`);
            }
        });
    }

    /* ===================== 剪贴板 ===================== */

    bindClipboard() {
        document.getElementById('btn-clip-send')?.addEventListener('click', () => {
            navigator.clipboard.readText().then(t => {
                if (t && this.sessionId) {
                    this.send({ type: 'clipboard_set', text: t, session_id: this.sessionId });
                    this.toast('📋 已发送到远程');
                }
            }).catch(() => {});
        });
        document.getElementById('btn-clip-get')?.addEventListener('click', () => {
            if (this.sessionId) this.send({ type: 'clipboard_get', session_id: this.sessionId });
        });
    }

    on_clipboard_changed(msg) {
        if (msg.source === 'agent') {
            const d = document.getElementById('clipboard-display');
            if (d) d.textContent = msg.text.substring(0, 200) + (msg.text.length > 200 ? '...' : '');
        }
    }

    on_clipboard_get_result(msg) {
        if (msg.text) {
            navigator.clipboard.writeText(msg.text).then(() => this.toast('📋 已获取远程剪贴板'));
        }
    }

    /* ===================== 远程 Shell ===================== */

    bindShell() {
        document.getElementById('btn-shell-toggle')?.addEventListener('click', () => this.toggleShell());
        document.getElementById('shell-input')?.addEventListener('keydown', e => {
            if (e.key === 'Enter' && this.shellActive) {
                this.send({ type: 'shell_input', input: e.target.value, session_id: this.sessionId });
                e.target.value = '';
            }
        });
    }

    toggleShell() {
        if (this.shellActive) { this.send({ type: 'shell_stop', session_id: this.sessionId }); this.disableShell(); }
        else { this.send({ type: 'shell_start', session_id: this.sessionId }); }
    }

    on_shell_started() {
        this.shellActive = true;
        document.getElementById('shell-output').style.display = 'block';
        document.getElementById('shell-output').textContent = '';
        document.getElementById('shell-input-row').style.display = 'flex';
        document.getElementById('btn-shell-toggle').textContent = '停止';
        document.getElementById('shell-input')?.focus();
    }

    on_shell_stopped() { this.disableShell(); }

    on_shell_output(msg) {
        const el = document.getElementById('shell-output');
        if (el) { el.textContent += msg.data; el.scrollTop = el.scrollHeight; }
    }

    disableShell() {
        this.shellActive = false;
        document.getElementById('shell-output').style.display = 'none';
        document.getElementById('shell-input-row').style.display = 'none';
        document.getElementById('btn-shell-toggle').textContent = '启动';
    }

    /* ===================== 录制回放 ===================== */

    on_recording_list(msg) {
        const el = document.getElementById('recording-list');
        if (!el) return;
        if (!msg.recordings?.length) { el.innerHTML = '<div class="empty-state">暂无录制</div>'; return; }
        el.innerHTML = msg.recordings.map(r => `
            <div class="recording-item fade-in" data-filename="${r.filename}" data-path="${r.path}">
                <div class="recording-name">${r.name || r.filename}</div>
                <div class="recording-meta">📅 ${r.date || '未知'} · 💾 ${r.size ? this.formatSize(r.size) : '未知'}</div>
            </div>
        `).join('');
        el.querySelectorAll('.recording-item').forEach(el => {
            el.addEventListener('click', () => this.loadRecording(el.dataset.path, el.dataset.filename));
        });
    }

    loadRecording(path, filename) {
        this.send({ type: 'recording_load', path, session_id: this.sessionId });
        this.updateStatus(`🎬 正在加载录制: ${filename}`);
    }

    on_recording_loaded(msg) {
        if (msg.error) { this.toast(`❌ 加载失败: ${msg.error}`); return; }
        this.recordingPlayer = {
            frames: msg.frames || [],
            fps: msg.fps || 10,
            currentFrame: 0,
            playing: false,
            speed: 1,
            interval: null,
            canvas: document.getElementById('player-canvas'),
            ctx: null
        };
        const rp = this.recordingPlayer;
        rp.ctx = rp.canvas.getContext('2d');

        // 设置画布
        if (msg.frames?.[0]?.width) {
            rp.canvas.width = msg.frames[0].width;
            rp.canvas.height = msg.frames[0].height;
        }

        // 显示播放器
        document.getElementById('recording-player').style.display = 'block';
        document.getElementById('player-title').textContent = msg.name || '录制回放';
        this._updatePlayerProgress();
        this.toast(`🎬 已加载 ${msg.frames?.length || 0} 帧`);

        // 绘制第一帧
        this._drawPlayerFrame(0);
    }

    _drawPlayerFrame(idx) {
        const rp = this.recordingPlayer;
        if (!rp || !rp.frames[idx]) return;
        const frame = rp.frames[idx];
        if (frame.type === 'full' || frame.data) {
            const img = new Image();
            img.onload = () => { rp.ctx.drawImage(img, 0, 0, rp.canvas.width, rp.canvas.height); };
            img.src = `data:image/jpeg;base64,${frame.data || frame.jpeg}`;
        }
    }

    _updatePlayerProgress() {
        const rp = this.recordingPlayer;
        if (!rp) return;
        const total = rp.frames.length;
        const pct = total > 0 ? (rp.currentFrame / total * 100) : 0;
        document.getElementById('player-fill').style.width = pct + '%';
        const curSec = Math.floor(rp.currentFrame / rp.fps);
        const totSec = Math.floor(total / rp.fps);
        document.getElementById('player-time').textContent = `${this._fmtTime(curSec)} / ${this._fmtTime(totSec)}`;
    }

    _fmtTime(s) { return `${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`; }

    togglePlayerPlay() {
        const rp = this.recordingPlayer;
        if (!rp) return;
        if (rp.playing) this.pausePlayer();
        else this.playPlayer();
    }

    playPlayer() {
        const rp = this.recordingPlayer;
        if (!rp) return;
        rp.playing = true;
        document.getElementById('btn-player-play').textContent = '⏸';
        rp.interval = setInterval(() => {
            rp.currentFrame++;
            if (rp.currentFrame >= rp.frames.length) { rp.currentFrame = 0; } // loop
            this._drawPlayerFrame(rp.currentFrame);
            this._updatePlayerProgress();
        }, (1000 / rp.fps) / rp.speed);
    }

    pausePlayer() {
        const rp = this.recordingPlayer;
        if (!rp) return;
        rp.playing = false;
        document.getElementById('btn-player-play').textContent = '▶';
        clearInterval(rp.interval);
        rp.interval = null;
    }

    stopPlayer() {
        if (this.recordingPlayer?.interval) clearInterval(this.recordingPlayer.interval);
        this.recordingPlayer = null;
        document.getElementById('recording-player').style.display = 'none';
        document.getElementById('btn-player-play').textContent = '▶';
    }

    _bindPlayerControls() {
        document.getElementById('btn-player-play')?.addEventListener('click', () => this.togglePlayerPlay());
        document.getElementById('btn-player-close')?.addEventListener('click', () => this.stopPlayer());

        // 进度条点击
        document.getElementById('player-progress')?.addEventListener('click', e => {
            const rp = this.recordingPlayer;
            if (!rp) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            rp.currentFrame = Math.floor(pct * rp.frames.length);
            this._drawPlayerFrame(rp.currentFrame);
            this._updatePlayerProgress();
        });

        // 速度切换
        const speeds = [1, 1.5, 2, 0.5, 4];
        let speedIdx = 0;
        document.getElementById('player-speed')?.addEventListener('click', () => {
            speedIdx = (speedIdx + 1) % speeds.length;
            const rp = this.recordingPlayer;
            if (rp) {
                rp.speed = speeds[speedIdx];
                if (rp.playing) { this.pausePlayer(); this.playPlayer(); }
            }
            document.getElementById('player-speed').textContent = speeds[speedIdx] + 'x';
        });
    }

    /* ===================== 质量监控 ===================== */

    startQualityMonitor() {
        setInterval(() => {
            if (!this.isConnected) return;
            const latencies = this.quality.latencies;
            const avgLat = latencies.length ? Math.round(latencies.reduce((a,b)=>a+b,0) / latencies.length) : 0;
            const elapsed = (Date.now() - this.quality.lastBandwidthCheck) / 1000;
            const bw = elapsed > 0 ? (this.quality.bytesWindow / (1024*1024)) / elapsed : 0;
            this.quality.bytesWindow = 0; this.quality.lastBandwidthCheck = Date.now();

            let score = 0;
            if (avgLat < 50) score += 30; else if (avgLat < 100) score += 20; else if (avgLat < 200) score += 10;
            if (this.quality.fps > 20) score += 30; else if (this.quality.fps > 10) score += 20; else if (this.quality.fps > 5) score += 10;
            if (bw > 0) score += 20;
            if (latencies.length > 0 && Math.max(...latencies) - avgLat < 50) score += 20;

            const label = score >= 80 ? '优秀' : score >= 60 ? '良好' : score >= 40 ? '一般' : '较差';
            const color = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--danger)';

            const set = (id, val, cls) => { const el = document.getElementById(id); if (el) { el.textContent = val; el.className = 'quality-value' + (cls ? ' '+cls : ''); } };
            const sd = document.getElementById('q-score-display');
            if (sd) { sd.textContent = `${score} ${label}`; sd.style.color = color; }
            set('q-latency2', `${avgLat}ms`, avgLat<100?'good':avgLat<300?'warn':'bad');
            set('q-fps2', `${this.quality.fps} fps`);
            set('q-bandwidth2', `${bw.toFixed(1)} MB/s`);

            const sp = document.getElementById('quality-score');
            if (sp) { sp.textContent = `${score} ${label}`; sp.style.color = color; }
            set('q-latency', `${avgLat}ms`, avgLat<100?'good':'warn');
            set('q-latency-p95', latencies.length ? `${Math.round([...latencies].sort((a,b)=>a-b)[Math.floor(latencies.length*0.95)]||0)}ms` : '-');
            set('q-fps', `${this.quality.fps} fps`);
            set('q-bandwidth', `${bw.toFixed(1)} MB/s`);
            set('q-loss', '0%');
        }, 1000);
    }

    /* ===================== 💬 聊天 ===================== */

    bindChat() {
        document.getElementById('btn-chat-toggle')?.addEventListener('click', () => this.toggleChat());
        document.getElementById('btn-chat-close')?.addEventListener('click', () => this.toggleChat());
        document.getElementById('btn-chat-send')?.addEventListener('click', () => this.sendChat());
        document.getElementById('chat-input')?.addEventListener('keydown', e => {
            if (e.key === 'Enter') this.sendChat();
        });
    }

    toggleChat() {
        const panel = document.getElementById('chat-panel');
        if (!panel) return;
        const visible = panel.style.display !== 'none';
        panel.style.display = visible ? 'none' : 'block';
        if (!visible) document.getElementById('chat-input')?.focus();
    }

    sendChat() {
        const input = document.getElementById('chat-input');
        if (!input || !input.value.trim() || !this.sessionId) return;
        const msg = input.value.trim();
        this.send({ type: 'chat', message: msg, session_id: this.sessionId, sender: 'controller' });
        this.addChatMessage(msg, 'sent');
        input.value = '';
    }

    on_chat(msg) {
        // 收到聊天消息（可能是 agent 回复或其他控制器）
        const from = msg.sender === 'controller' ? '对方' : 'Agent';
        this.addChatMessage(msg.message, 'received', from);
    }

    addChatMessage(text, type, from = '') {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        const div = document.createElement('div');
        div.className = `chat-msg ${type}`;
        div.innerHTML = `<div>${this.escapeHtml(text)}</div><div class="chat-time">${from ? from + ' · ' : ''}${time}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /* ===================== Toast ===================== */

    toast(msg, duration = 2500) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const t = document.createElement('div');
        t.className = 'toast'; t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), duration);
    }

    /* ===================== 状态 ===================== */

    setStatus(status, text) {
        const dot = document.getElementById('conn-dot');
        const txt = document.getElementById('conn-text');
        if (dot) dot.className = `status-dot ${status}`;
        if (txt) txt.textContent = text;
    }

    updateStatus(text) {
        const el = document.getElementById('status-text');
        if (el) el.textContent = text;
    }
}

/* ===================== 初始化 ===================== */

document.addEventListener('DOMContentLoaded', () => {
    window.controller = new RemoteController();
    window.controller.startQualityMonitor();
    // 延迟绑定播放器控件（DOM 渲染后）
    setTimeout(() => window.controller._bindPlayerControls(), 100);
});
