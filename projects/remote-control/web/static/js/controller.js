/**
 * RemoteEye 主控端 - 远程控制逻辑
 */
class RemoteController {
    constructor() {
        this.ws = null;
        this.devices = [];
        this.currentDevice = null;
        this.sessionId = null;
        this.canvas = document.getElementById('screen-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.fpsCounter = { frames: 0, lastTime: Date.now() };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.connect();
    }
    
    // 连接信令服务器
    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${location.host}/ws/controller`;
        
        this.setStatus('connecting', '正在连接...');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.setStatus('online', '已连接');
            this.updateStatus('已连接到服务器');
        };
        
        this.ws.onclose = () => {
            this.setStatus('offline', '未连接');
            this.updateStatus('连接已断开，5秒后重连...');
            setTimeout(() => this.connect(), 5000);
        };
        
        this.ws.onerror = (err) => {
            console.error('WebSocket 错误:', err);
            this.updateStatus('连接错误');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this.handleMessage(msg);
            } catch (e) {
                console.error('消息解析失败:', e);
            }
        };
    }
    
    // 处理服务器消息
    handleMessage(msg) {
        switch (msg.type) {
            case 'device_list':
                this.updateDeviceList(msg.devices);
                break;
            case 'connected':
                this.onDeviceConnected(msg);
                break;
            case 'disconnected':
                this.onDeviceDisconnected();
                break;
            case 'screenshot':
                this.renderScreenshot(msg.data);
                break;
            case 'error':
                alert(`错误: ${msg.message}`);
                break;
            default:
                console.log('未知消息类型:', msg.type);
        }
    }
    
    // 更新设备列表
    updateDeviceList(devices) {
        this.devices = devices;
        const listEl = document.getElementById('device-list');
        
        if (devices.length === 0) {
            listEl.innerHTML = '<li class="empty-state">暂无在线设备</li>';
            return;
        }
        
        listEl.innerHTML = devices.map(d => `
            <li class="device-item ${d.is_controlled ? 'controlled' : ''}" data-id="${d.device_id}">
                <div class="device-name">
                    <span class="device-status"></span>
                    ${d.name}
                </div>
                <div class="device-info">
                    ${d.platform} · ${d.resolution}
                    ${d.is_controlled ? ' · <span style="color:var(--warning)">控制中</span>' : ''}
                </div>
            </li>
        `).join('');
        
        // 绑定点击事件
        listEl.querySelectorAll('.device-item:not(.controlled)').forEach(el => {
            el.addEventListener('click', () => this.connectToDevice(el.dataset.id));
        });
    }
    
    // 连接设备
    connectToDevice(deviceId) {
        if (this.sessionId) {
            this.disconnect();
        }
        
        this.currentDevice = this.devices.find(d => d.device_id === deviceId);
        if (!this.currentDevice) return;
        
        this.ws.send(JSON.stringify({
            type: 'connect_device',
            device_id: deviceId,
            quality: 75,
            fps: 15
        }));
        
        this.updateStatus(`正在连接 ${this.currentDevice.name}...`);
    }
    
    // 设备连接成功
    onDeviceConnected(msg) {
        this.sessionId = msg.session_id;
        document.getElementById('current-device').textContent = msg.device_name;
        document.getElementById('control-bar').style.display = 'flex';
        document.getElementById('remote-screen').style.display = 'none';
        this.canvas.style.display = 'block';
        this.updateStatus(`已连接到 ${msg.device_name}`);
        
        // 高亮当前设备
        document.querySelectorAll('.device-item').forEach(el => {
            el.classList.toggle('active', el.dataset.id === this.currentDevice?.device_id);
        });
    }
    
    // 设备断开
    onDeviceDisconnected() {
        this.sessionId = null;
        this.currentDevice = null;
        document.getElementById('control-bar').style.display = 'none';
        document.getElementById('remote-screen').style.display = 'flex';
        this.canvas.style.display = 'none';
        this.updateStatus('已断开连接');
        
        document.querySelectorAll('.device-item').forEach(el => {
            el.classList.remove('active');
        });
    }
    
    // 渲染截屏
    renderScreenshot(base64Data) {
        const img = new Image();
        img.onload = () => {
            this.canvas.width = img.width;
            this.canvas.height = img.height;
            this.ctx.drawImage(img, 0, 0);
            
            // FPS 计算
            this.fpsCounter.frames++;
            const now = Date.now();
            if (now - this.fpsCounter.lastTime >= 1000) {
                const fps = this.fpsCounter.frames;
                this.fpsCounter.frames = 0;
                this.fpsCounter.lastTime = now;
                document.getElementById('fps-display').textContent = `${fps} fps`;
            }
        };
        img.src = `data:image/jpeg;base64,${base64Data}`;
    }
    
    // 发送输入事件
    sendInput(action, data = {}) {
        if (!this.sessionId || !this.ws) return;
        
        this.ws.send(JSON.stringify({
            type: 'input',
            session_id: this.sessionId,
            action,
            ...data
        }));
    }
    
    // 断开连接
    disconnect() {
        if (this.sessionId) {
            this.ws.send(JSON.stringify({
                type: 'disconnect',
                session_id: this.sessionId
            }));
        }
        this.onDeviceDisconnected();
    }
    
    // 绑定事件
    bindEvents() {
        // 刷新按钮
        document.getElementById('btn-refresh').addEventListener('click', () => {
            this.updateStatus('刷新设备列表...');
        });
        
        // 全屏按钮
        document.getElementById('btn-fullscreen').addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                this.canvas.requestFullscreen();
            }
        });
        
        // 断开按钮
        document.getElementById('btn-disconnect').addEventListener('click', () => {
            this.disconnect();
        });
        
        // Canvas 鼠标事件
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (this.canvas.width / rect.width);
            const y = (e.clientY - rect.top) * (this.canvas.height / rect.height);
            this.sendInput('mouse_move', { x: Math.round(x), y: Math.round(y) });
        });
        
        this.canvas.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const rect = this.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (this.canvas.width / rect.width);
            const y = (e.clientY - rect.top) * (this.canvas.height / rect.height);
            
            let button = 'left';
            if (e.button === 2) button = 'right';
            if (e.button === 1) button = 'middle';
            
            this.sendInput('mouse_click', { 
                x: Math.round(x), 
                y: Math.round(y), 
                button 
            });
        });
        
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.sendInput('mouse_scroll', { delta: -Math.round(e.deltaY / 10) });
        });
        
        // Canvas 键盘事件
        document.addEventListener('keydown', (e) => {
            if (!this.sessionId) return;
            this.sendInput('key_press', { key: e.key });
        });
        
        document.addEventListener('keyup', (e) => {
            if (!this.sessionId) return;
            this.sendInput('key_release', { key: e.key });
        });
    }
    
    // 更新连接状态
    setStatus(status, text) {
        const dot = document.getElementById('connection-status');
        const txt = document.getElementById('connection-text');
        dot.className = `status-dot ${status}`;
        txt.textContent = text;
    }
    
    // 更新状态栏
    updateStatus(text) {
        document.getElementById('status-text').textContent = text;
    }
}

// 启动
document.addEventListener('DOMContentLoaded', () => {
    window.controller = new RemoteController();
});
