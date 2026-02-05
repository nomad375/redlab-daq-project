from flask import Flask, render_template_string, request, jsonify
import sys
import glob
import time

# Подключаем MSCL
mscl_path = '/usr/lib/python3.12/dist-packages'
if mscl_path not in sys.path: 
    sys.path.append(mscl_path)

import MSCL as mscl

app = Flask(__name__)

# Глобальные переменные
BASE_STATION = None
BAUDRATE = 3000000 

RATE_MAP = {
    106: "1 Hz", 107: "2 Hz", 108: "4 Hz", 109: "8 Hz",
    110: "16 Hz", 111: "32 Hz", 112: "64 Hz", 113: "128 Hz",
    114: "256 Hz", 115: "512 Hz", 116: "1 kHz", 117: "2 kHz"
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TC-Link-200 Configurator</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #f8f9fa; font-family: sans-serif; }
        .card { margin-bottom: 20px; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-radius: 10px; }
        .status-ok { color: #2ecc71; font-weight: bold; }
        .status-err { color: #e74c3c; font-weight: bold; }
        .diag-text { font-size: 0.85rem; color: #6c757d; }
    </style>
</head>
<body>
<div class="container" style="max-width: 800px;">
    <div class="card p-3 shadow-sm bg-primary text-white d-flex flex-row justify-content-between align-items-center">
        <h4 class="m-0">📡 Конфигуратор TC-Link-200</h4>
        <button onclick="connectBase()" class="btn btn-light btn-sm fw-bold">🔌 ПРОВЕРИТЬ USB</button>
    </div>

    <div class="card p-4 shadow-sm">
        <div class="row g-3 align-items-center">
            <div class="col-md-4">
                <div class="input-group">
                    <span class="input-group-text">Node ID</span>
                    <input type="number" id="nodeId" class="form-control" value="16907">
                </div>
            </div>
            <div class="col-md-8">
                <button id="btnRead" onclick="readConfig()" class="btn btn-success w-100 fw-bold">🔍 СЧИТАТЬ НАСТРОЙКИ</button>
            </div>
        </div>
        <div id="readStatus" class="mt-2 text-center fw-bold small"></div>
    </div>

    <div id="configCard" style="display:none;">
        <div class="card p-4 shadow-sm">
            <div class="row mb-4">
                <div class="col-md-6">
                    <label class="form-label fw-bold">Частота (Sample Rate)</label>
                    <select id="sampleRate" class="form-select"></select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-bold">Мощность радио</label>
                    <select id="txPower" class="form-select">
                        <option value="20">20 dBm (Max)</option>
                        <option value="16">16 dBm</option>
                        <option value="10">10 dBm</option>
                        <option value="5">5 dBm</option>
                        <option value="0">0 dBm (Min)</option>
                    </select>
                </div>
            </div>

            <label class="form-label fw-bold text-primary">Активные каналы (Raw Mode):</label>
            <div id="channelsArea" class="mb-4"></div>

            <div id="diagArea" class="diag-text mb-4 p-2 bg-light rounded"></div>

            <button id="btnWrite" onclick="applyConfig()" class="btn btn-primary w-100 fw-bold py-2">💾 ЗАПИСАТЬ В EEPROM</button>
            <div id="writeStatus" class="mt-3 text-center fw-bold"></div>
        </div>
    </div>
</div>

<script>
    async function connectBase() {
        try {
            const res = await fetch('/api/connect', {method:'POST'});
            const data = await res.json();
            alert(data.success ? "USB База готова на порту " + data.port : "База не найдена");
        } catch (e) { }
    }

    async function readConfig() {
        const id = document.getElementById('nodeId').value;
        const statusDiv = document.getElementById('readStatus');
        const btn = document.getElementById('btnRead');
        
        btn.disabled = true;
        statusDiv.className = "mt-2 text-center text-primary";
        statusDiv.innerHTML = "⌛ Чтение... Если ошибка 46/94, подождите 3 сек и нажмите еще раз.";
        document.getElementById('configCard').style.display = "none";
        
        try {
            const res = await fetch(`/api/read/${id}`);
            const data = await res.json();
            if(data.success) {
                statusDiv.className = "mt-2 text-center status-ok";
                statusDiv.innerHTML = "✅ Настройки получены";
                document.getElementById('configCard').style.display = "block";
                
                document.getElementById('txPower').value = data.current_power;
                document.getElementById('diagArea').innerHTML = `Model: ${data.model} | FW: ${data.fw} | S/N: ${data.sn} | Battery: ${data.battery}V`;

                const sel = document.getElementById('sampleRate');
                sel.innerHTML = "";
                data.supported_rates.forEach(r => {
                    let opt = document.createElement('option');
                    opt.value = r.enum_val; opt.text = r.str_val;
                    if(r.enum_val == data.current_rate) opt.selected = true;
                    sel.add(opt);
                });

                const chArea = document.getElementById('channelsArea');
                chArea.innerHTML = "";
                data.channels.forEach(ch => {
                    let checked = ch.enabled ? "checked" : "";
                    chArea.innerHTML += `
                        <div class="border rounded p-2 mb-2 bg-white d-flex justify-content-between align-items-center">
                            <div class="form-check form-switch m-0">
                                <input class="form-check-input ch-enable" type="checkbox" id="ch_${ch.id}" ${checked}>
                                <label class="form-check-label fw-bold">Канал ${ch.id}</label>
                            </div>
                        </div>`;
                });
            } else {
                statusDiv.className = "mt-2 text-center status-err";
                statusDiv.innerHTML = "❌ Ошибка: " + data.error;
            }
        } finally { btn.disabled = false; }
    }

    async function applyConfig() {
        const id = document.getElementById('nodeId').value;
        const rate = document.getElementById('sampleRate').value;
        const power = document.getElementById('txPower').value;
        const statusDiv = document.getElementById('writeStatus');
        
        let activeChs = [];
        document.querySelectorAll('.ch-enable').forEach(cb => {
            if(cb.checked) { activeChs.push(parseInt(cb.id.replace('ch_', ''))); }
        });
        
        statusDiv.className = "mt-3 text-center text-primary";
        statusDiv.innerHTML = "⏳ Сохранение...";
        try {
            const res = await fetch('/api/write', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ node_id: id, sample_rate: parseInt(rate), tx_power: parseInt(power), channels: activeChs })
            });
            const data = await res.json();
            statusDiv.innerHTML = data.success ? "<span class='status-ok'>✅ УСПЕШНО СОХРАНЕНО</span>" : `<span class='status-err'>❌ ${data.error}</span>`;
        } catch (e) { }
    }
</script>
</body>
</html>
"""

def find_port():
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    return ports[0] if ports else None

def internal_connect():
    global BASE_STATION
    if BASE_STATION: return True, "Connected"
    port = find_port()
    if not port: return False, "No Port"
    try:
        conn = mscl.Connection.Serial(port, BAUDRATE)
        station = mscl.BaseStation(conn)
        station.readWriteRetries(10)
        if station.ping():
            BASE_STATION = station
            BASE_STATION.enableBeacon()
            return True, port
        return False, "Ping failed"
    except Exception as e: return False, str(e)

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/connect', methods=['POST'])
def api_connect():
    s, p = internal_connect()
    return jsonify(success=s, port=p)

@app.route('/api/read/<int:node_id>')
def api_read(node_id):
    global BASE_STATION, RATE_MAP
    internal_connect()
    try:
        node = mscl.WirelessNode(node_id, BASE_STATION)
        node.readWriteRetries(15)
        
        # 1. Принудительная остановка
        status = node.setToIdle()
        time.sleep(1.5) # Ждем чуть дольше

        # 2. ЧИТАЕМ ТОЛЬКО КРИТИЧЕСКИЕ ДАННЫЕ
        current_rate = int(node.getSampleRate())
        active_mask = node.getActiveChannels()
        
        # 3. ВСЕ ОСТАЛЬНОЕ - В TRY-EXCEPT (чтобы не падало при ошибке 94/46)
        try: model = node.model()
        except: model = "TC-Link-200"
        
        try: sn = str(node.nodeAddress())
        except: sn = "N/A"
        
        try: fw = str(node.firmwareVersion())
        except: fw = "N/A"
        
        try: 
            p_raw = int(node.getTransmitPower())
            p_map = {0: 20, 1: 16, 2: 10, 3: 5, 4: 0}
            current_power = p_map.get(p_raw, 20)
        except: 
            current_power = 20 # Дефолт при ошибке 94
            
        try: battery = round(node.getCurBatteryVoltage(), 2)
        except: battery = 0.0

        # Частоты
        features = node.features()
        supported_rates = []
        try:
            rates = features.sampleRates(mscl.WirelessTypes.samplingMode_sync, 1, 0)
            for r in rates:
                rid = int(r)
                supported_rates.append({"enum_val": rid, "str_val": RATE_MAP.get(rid, str(rid) + " Hz")})
        except:
            supported_rates.append({"enum_val": current_rate, "str_val": str(current_rate)})
            
        channels = []
        for i in range(1, 3):
            channels.append({"id": i, "enabled": active_mask.enabled(i)})
        
        return jsonify(
            success=True, model=model, sn=sn, fw=fw, battery=battery,
            current_rate=current_rate, current_power=current_power,
            supported_rates=supported_rates, channels=channels
        )
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/api/write', methods=['POST'])
def api_write():
    global BASE_STATION
    data = request.json
    try:
        node = mscl.WirelessNode(int(data['node_id']), BASE_STATION)
        node.setToIdle()
        time.sleep(1)
        config = mscl.WirelessNodeConfig()
        config.samplingMode(mscl.WirelessTypes.samplingMode_sync)
        config.sampleRate(int(data['sample_rate']))
        p_map = {20: 0, 16: 1, 10: 2, 5: 3, 0: 4}
        config.transmitPower(p_map.get(data['tx_power'], 0))
        full_mask = mscl.ChannelMask()
        for ch_id in data['channels']:
            full_mask.enable(ch_id)
        config.activeChannels(full_mask)
        node.applyConfig(config)
        return jsonify(success=True)
    except Exception as e: return jsonify(success=False, error=str(e))

def run_config_server():
    app.run(host='0.0.0.0', port=5000)