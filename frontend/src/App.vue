<template>
  <div class="dashboard-container">
    <div id="map-container" class="map-layer"></div>

    <header class="header">
      <h1 class="gradient-text">智巡速诊: 道路病害的快速发现及精准诊断系统</h1>
      <div class="subtitle">态势感知预警 | 空地协同调度 | 病害精细化识别</div>
    </header>

    <aside class="panel left-panel">
      <h2>交通流五维态势异动监测</h2>
      <div class="metric-box">
        <div class="metric">速度预测偏差 <span :class="{'alert-text': dataScore >= 85}">{{ Math.round(speedDev) }}%</span></div>
        <div class="metric">速度骤降率 <span :class="{'alert-text': dataScore >= 85}">{{ Math.round(speedDrop) }}%</span></div>
        <div class="metric">车流变异系数 <span :class="{'alert-text': dataScore >= 85}">{{ Math.round(variation) }}%</span></div>
        <div class="metric">空间一致性 <span :class="{'alert-text': dataScore >= 85}">{{ Math.round(spatial) }}%</span></div>
        <div class="metric">交通态势熵 <span :class="{'alert-text': dataScore >= 85}">{{ Math.round(entropy) }}</span></div>
      </div>
      
      <div class="score-container">
        <h3>异常综合风险指数</h3>
        <div class="score-circle" :class="{'danger': dataScore >= 85}">
          {{ Math.round(dataScore) }}
        </div>
        <p v-if="dataScore >= 85" class="alert-msg">⚠️ 突破危险阈值，多处疑似重大病害！</p>
      </div>

      <div class="dispatch-status-box" v-if="dataScore >= 85">
        <div class="divider"></div>
        <p>当前状态: <span class="highlight">{{ dispatchStatus }}</span></p>
        <p v-if="reportGenerated" class="tip-text">👆 请点击地图上的事故点查看详细报告</p>
      </div>
    </aside>

    <div class="demo-controls">
      <button @click="triggerAnomaly" :disabled="dataScore >= 85" class="btn-primary">1. 触发路网风险热力爆变</button>
      <button @click="startDispatch" :disabled="dataScore < 85 || isDispatching" class="btn-primary">2. 启动空地协同调度 (3机 3骑)</button>
      <button @click="generateReport" :disabled="dispatchStatus !== '空地智能体已抵达各目标空域' || reportGenerated" class="btn-primary">3. 激活病害精细化识别</button>
      <label class="btn-upload">
        4. 上传自定义图片检测
        <input type="file" accept="image/*" @change="handleFileUpload" hidden />
      </label>
      <button @click="resetDemo" class="btn-reset">↺ 重置演示</button>
    </div>

    <!-- AI 检测结果模态框 -->
    <div class="modal-overlay" v-if="showModal" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>YOLO-Master 病害精细化识别报告</h3>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <!-- Loading 状态 -->
          <div v-if="isDetecting" class="loading-container">
            <div class="loading-spinner"></div>
            <p class="loading-text">YOLO-Master 模型推理中...</p>
            <p class="loading-sub">正在对病害区域进行深度特征提取与分类</p>
          </div>

          <!-- 检测结果 -->
          <template v-else-if="detectResult">
            <div class="video-placeholder">
              <img :src="'data:image/jpeg;base64,' + detectResult.annotated_image" class="mock-vision-img" alt="YOLO-Master Detection" />
              <div class="scan-line"></div>
              <p class="vision-tag">
                检测到 {{ detectResult.count }} 处病害
              </p>
            </div>

            <div class="detection-list" v-if="detectResult.detections.length > 0">
              <h4>检测目标列表</h4>
              <div class="det-item" v-for="(det, idx) in detectResult.detections" :key="idx">
                <span class="det-class">{{ det.class_name }}</span>
                <div class="conf-bar-wrap">
                  <div class="conf-bar" :style="{ width: (det.confidence * 100) + '%' }"></div>
                </div>
                <span class="det-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>

            <div class="report-details">
              <p><strong>AI 协同处置研判报告：</strong></p>
              <div class="advice-box">{{ detectResult.summary }}</div>
            </div>
          </template>

          <!-- 错误状态 -->
          <div v-else-if="detectError" class="error-container">
            <p class="error-text">{{ detectError }}</p>
            <button class="btn-retry" @click="retryDetect">重试</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, shallowRef } from 'vue';
import AMapLoader from '@amap/amap-jsapi-loader';

import imgCrack1 from './assets/crack_1.jpg';
import imgCrack2 from './assets/crack_2.jpg';
import imgCrack3 from './assets/crack_3.jpg';
import imgCrack4 from './assets/crack_4.jpg';
import imgCrack5 from './assets/crack_5.jpg';
import imgCrack6 from './assets/crack_6.jpg';

const speedDev = ref(8);    
const speedDrop = ref(12);  
const variation = ref(15);  
const spatial = ref(95);    
const entropy = ref(2);     
const dataScore = ref(45);  

const dispatchStatus = ref('常态巡检中...');
const reportGenerated = ref(false);
const isDispatching = ref(false);

const showModal = ref(false);
const isDetecting = ref(false);
const detectResult = ref(null);
const detectError = ref(null);
const pendingPointId = ref(null);

const closeModal = () => {
  showModal.value = false;
  detectResult.value = null;
  detectError.value = null;
};

const map = shallowRef(null);
let AMapObj = null;
let heatmapLayer = null;
let markers = [];
let polylines = [];

const yizhuangCenter = [116.5056, 39.7954];
const dispatchHub = [116.5050, 39.7820]; 

const anomalyPoints = [
  { id: 1, lnglat: [116.5056, 39.7954], imgUrl: imgCrack1 },
  { id: 2, lnglat: [116.5000, 39.7980], imgUrl: imgCrack2 },
  { id: 3, lnglat: [116.5120, 39.7920], imgUrl: imgCrack3 },
  { id: 4, lnglat: [116.5080, 39.7990], imgUrl: imgCrack4 },
  { id: 5, lnglat: [116.5025, 39.7905], imgUrl: imgCrack5 },
  { id: 6, lnglat: [116.5145, 39.7968], imgUrl: imgCrack6 },
];

// --- API 调用 ---

async function detectPreloaded(imageId) {
  isDetecting.value = true;
  detectResult.value = null;
  detectError.value = null;
  showModal.value = true;

  try {
    const resp = await fetch(`/api/detect-preloaded/${imageId}`);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `服务端错误 (${resp.status})`);
    }
    detectResult.value = await resp.json();
  } catch (e) {
    detectError.value = e.message || '网络连接失败，请确认后端服务已启动';
  } finally {
    isDetecting.value = false;
  }
}

async function detectUploaded(file) {
  isDetecting.value = true;
  detectResult.value = null;
  detectError.value = null;
  showModal.value = true;

  try {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch('/api/detect', { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `服务端错误 (${resp.status})`);
    }
    detectResult.value = await resp.json();
  } catch (e) {
    detectError.value = e.message || '网络连接失败，请确认后端服务已启动';
  } finally {
    isDetecting.value = false;
  }
}

function retryDetect() {
  if (pendingPointId.value) {
    detectPreloaded(pendingPointId.value);
  }
}

function handleFileUpload(event) {
  const file = event.target.files?.[0];
  if (file) {
    pendingPointId.value = null;
    detectUploaded(file);
  }
  event.target.value = '';
}

// --- 路网与热力图 ---

const vLngs = [116.4900, 116.4950, 116.5000, 116.5056, 116.5080, 116.5120, 116.5160, 116.5200]; 
const hLats = [39.7850, 39.7880, 39.7920, 39.7954, 39.7980, 39.7990, 39.8030, 39.8080]; 
const mainRoads = [];
vLngs.forEach(lng => mainRoads.push([[lng, 39.7750], [lng, 39.8150]])); 
hLats.forEach(lat => mainRoads.push([[116.4800, lat], [116.5300, lat]])); 

const getRandomPointOnRoad = () => {
  const road = mainRoads[Math.floor(Math.random() * mainRoads.length)];
  const ratio = Math.random(); 
  return {
    lng: road[0][0] + (road[1][0] - road[0][0]) * ratio,
    lat: road[0][1] + (road[1][1] - road[0][1]) * ratio
  };
};

const generateHeatData = (isAnomaly) => {
  let heatData = [];
  for(let i = 0; i < 800; i++) {
    const pt = getRandomPointOnRoad();
    heatData.push({ lng: pt.lng, lat: pt.lat, count: Math.floor(Math.random() * 120) + 10 });
  }
  if (isAnomaly) {
    anomalyPoints.forEach(pt => {
      heatData.push({ lng: pt.lnglat[0], lat: pt.lnglat[1], count: 200 });
      for(let j = 1; j <= 8; j++) {
        const step = 0.0006; 
        heatData.push({ lng: pt.lnglat[0] + j * step, lat: pt.lnglat[1], count: 150 - j*10 });
        heatData.push({ lng: pt.lnglat[0] - j * step, lat: pt.lnglat[1], count: 150 - j*10 });
        heatData.push({ lng: pt.lnglat[0], lat: pt.lnglat[1] + j * step, count: 150 - j*10 });
        heatData.push({ lng: pt.lnglat[0], lat: pt.lnglat[1] - j * step, count: 150 - j*10 });
      }
    });
  }
  return heatData;
};

// --- 地图初始化 ---

onMounted(() => {
  window._AMapSecurityConfig = {
    securityJsCode: '26a07d5e69469dd6e2d1169c67b13b3e',
  };
  
  AMapLoader.load({
    key: '6c50e30dfec341f7f1fec179d8abc9d8', 
    version: '2.0',
    plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.Driving', 'AMap.HeatMap'],
  }).then((AMap) => {
    AMapObj = AMap;
    map.value = new AMap.Map('map-container', {
      viewMode: '3D', pitch: 55, rotation: -10, zoom: 14.5, 
      center: yizhuangCenter, 
      mapStyle: 'amap://styles/light', 
      features: ['bg', 'road', 'building'], 
    });

    heatmapLayer = new AMap.HeatMap(map.value, {
      radius: 18, 
      opacity: [0.15, 0.85], 
      gradient: { 0.2: '#22c55e', 0.5: '#eab308', 0.7: '#f97316', 0.9: '#ef4444' }
    });
    
    heatmapLayer.setDataSet({ data: generateHeatData(false), max: 120 });
  }).catch(e => console.error('高德地图加载失败:', e));
});

// --- 演示流程 ---

const triggerAnomaly = () => {
  let interval = setInterval(() => {
    if (dataScore.value < 85) {
      dataScore.value += 4; speedDev.value += 3; speedDrop.value += 4;
      variation.value += 5; spatial.value -= 2; entropy.value += 1;
    } else {
      clearInterval(interval);
      dataScore.value = 85; speedDev.value = 42; speedDrop.value = 56;
      variation.value = 65; spatial.value = 68; entropy.value = 12;
      
      if (map.value && AMapObj && heatmapLayer) {
        map.value.setZoomAndCenter(15.5, yizhuangCenter, true); 
        heatmapLayer.setDataSet({ data: generateHeatData(true), max: 120 });
        
        anomalyPoints.forEach((pt) => {
          const customMarker = document.createElement('div');
          customMarker.className = 'pulse-marker-container';
          customMarker.innerHTML = `<div class="pulse-marker"></div><div class="pulse-ring"></div>`;
          
          const marker = new AMapObj.Marker({
            position: pt.lnglat, content: customMarker, offset: new AMapObj.Pixel(-15, -15), extData: pt
          });

          marker.on('click', (e) => {
            if (!reportGenerated.value) {
              alert('请先点击底部"激活病害精细化识别"以提取视觉特征！');
              return;
            }
            const pointData = e.target.getExtData();
            pendingPointId.value = pointData.id;
            detectPreloaded(pointData.id);
          });

          map.value.add(marker);
          markers.push(marker);
        });
      }
    }
  }, 100);
};

const startDispatch = () => {
  isDispatching.value = true;
  dispatchStatus.value = '正在进行全局路网注意力掩码解码...';
  
  if (map.value) { map.value.setPitch(40, true); map.value.setRotation(15, true); }

  setTimeout(() => {
    dispatchStatus.value = '最优路径已生成，正在绘制空地协同轨迹...';
    
    const droneTasks = anomalyPoints.slice(0, 3);
    const policeTasks = anomalyPoints.slice(3, 6); 

    droneTasks.forEach((pt) => {
      const droneLine = new AMapObj.Polyline({
        path: [dispatchHub, pt.lnglat], isOutline: true, outlineColor: '#fff', borderWeight: 1,
        strokeColor: '#0ea5e9', strokeOpacity: 0.8, strokeWeight: 4, 
        strokeStyle: 'dashed', strokeDasharray: [10, 5], lineJoin: 'round', zIndex: 50
      });
      map.value.add(droneLine);
      polylines.push(droneLine);
    });

    const driving = new AMapObj.Driving({ policy: AMapObj.DrivingPolicy.LEAST_TIME });
    policeTasks.forEach((pt) => {
      driving.search(
        new AMapObj.LngLat(dispatchHub[0], dispatchHub[1]), 
        new AMapObj.LngLat(pt.lnglat[0], pt.lnglat[1]), 
        (status, result) => {
          if (status === 'complete' && result.routes && result.routes.length) {
            const path = [];
            result.routes[0].steps.forEach(step => step.path.forEach(lnglat => path.push(lnglat)));
            const policeLine = new AMapObj.Polyline({
              path: path, strokeColor: '#16a34a', strokeOpacity: 1, strokeWeight: 6, 
              strokeStyle: 'solid', lineJoin: 'round', zIndex: 40, showDir: true 
            });
            map.value.add(policeLine);
            polylines.push(policeLine);
          }
        }
      );
    });

    setTimeout(() => { dispatchStatus.value = '空地智能体已抵达各目标空域'; }, 2000);
  }, 1000);
};

const generateReport = () => {
  reportGenerated.value = true;
  if (map.value) map.value.setZoomAndCenter(16.5, yizhuangCenter, true);
};

const resetDemo = () => {
  speedDev.value = 8; speedDrop.value = 12; variation.value = 15; spatial.value = 95; entropy.value = 2;
  dataScore.value = 45; dispatchStatus.value = '常态巡检中...';
  reportGenerated.value = false; isDispatching.value = false; showModal.value = false;
  detectResult.value = null; detectError.value = null; pendingPointId.value = null;
  
  if (map.value && heatmapLayer) {
    map.value.remove(markers); map.value.remove(polylines); markers = []; polylines = [];
    heatmapLayer.setDataSet({ data: generateHeatData(false), max: 120 });
    map.value.setZoomAndCenter(14.5, yizhuangCenter, true);
    map.value.setPitch(55, true); map.value.setRotation(-10, true);
  }
};
</script>

<style scoped>
.dashboard-container {
  width: 100vw; height: 100vh; background-color: #f8fafc; color: #334155; 
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; position: relative; overflow: hidden;
}
.map-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }

:deep(.pulse-marker-container) { position: relative; width: 30px; height: 30px; cursor: pointer; }
:deep(.pulse-marker) {
  width: 16px; height: 16px; background-color: #ef4444; border-radius: 50%;
  position: absolute; top: 7px; left: 7px; z-index: 2; box-shadow: 0 0 12px rgba(239, 68, 68, 0.9);
}
:deep(.pulse-ring) {
  width: 30px; height: 30px; background-color: transparent; border: 3px solid #ef4444;
  border-radius: 50%; position: absolute; top: 0; left: 0; z-index: 1; animation: radarPulse 1.5s infinite ease-out;
}
@keyframes radarPulse { 0% { transform: scale(0.5); opacity: 1; } 100% { transform: scale(3.5); opacity: 0; } }

.header {
  position: absolute; top: 0; width: 100%; text-align: center; z-index: 10; padding: 20px 0;
  background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(10px); pointer-events: none; 
}
.gradient-text { margin: 0; font-size: 32px; font-weight: 700; letter-spacing: 2px; background: linear-gradient(135deg, #2563eb, #0ea5e9); -webkit-background-clip: text; color: transparent; }
.subtitle { color: #64748b; font-size: 15px; margin-top: 6px; font-weight: 600; letter-spacing: 1px;}

.panel {
  position: absolute; top: 120px; width: 400px; 
  background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 1); box-shadow: 0 10px 40px rgba(15, 23, 42, 0.12);
  border-radius: 16px; padding: 25px 30px; z-index: 10;
}
.left-panel { left: 40px; }

h2 { font-size: 20px; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; margin-top: 0; margin-bottom: 20px; font-weight: 700;}

.metric-box { display: flex; flex-direction: column; gap: 14px; }
.metric { display: flex; justify-content: space-between; font-size: 16px; color: #475569; font-weight: 600;}
.metric span { color: #0f172a; font-weight: 700; font-family: monospace; font-size: 20px; }

.score-container { text-align: center; margin-top: 30px; }
.score-circle {
  width: 140px; height: 140px; border-radius: 50%; border: 8px solid #22c55e;
  display: flex; justify-content: center; align-items: center;
  font-size: 56px; font-weight: 800; margin: 15px auto; transition: all 0.5s;
  color: #15803d; background: #f0fdf4; box-shadow: 0 8px 16px rgba(34, 197, 94, 0.15);
}
.score-circle.danger { border-color: #ef4444; color: #b91c1c; background: #fef2f2; box-shadow: 0 8px 25px rgba(239, 68, 68, 0.3); }

.alert-text { color: #ef4444 !important; }
.alert-msg { color: #ef4444; font-size: 16px; font-weight: bold; animation: pulse 1s infinite; margin-top: 15px;}

.dispatch-status-box { margin-top: 20px; }
.divider { height: 1px; background: #e2e8f0; margin: 15px 0; }
.highlight { color: #0ea5e9; font-weight: 700; font-size: 15px;}
.tip-text { color: #10b981; font-weight: bold; margin-top: 12px; font-size: 14px; background: #ecfdf5; padding: 10px; border-radius: 6px; text-align: center; border: 1px dashed #34d399; animation: pulse 2s infinite;}

.demo-controls {
  position: absolute; bottom: 40px; left: 50%; transform: translateX(-50%); z-index: 20; display: flex; gap: 15px;
  background: rgba(255, 255, 255, 0.95); padding: 16px 24px; border-radius: 50px; 
  border: 1px solid #e2e8f0; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08); backdrop-filter: blur(10px);
}
.btn-primary { background: #ffffff; border: 1px solid #cbd5e1; color: #475569; padding: 12px 24px; cursor: pointer; border-radius: 30px; font-size: 15px; font-weight: 600; transition: all 0.2s; }
.btn-primary:hover:not(:disabled) { border-color: #0ea5e9; color: #0ea5e9; background: #f0f9ff; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.15);}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; background: #f1f5f9; border-color: #e2e8f0; }
.btn-reset { background: #f8fafc; border: 1px solid #e2e8f0; color: #64748b; padding: 12px 24px; cursor: pointer; border-radius: 30px; font-size: 15px; font-weight: 600; transition: all 0.2s;}
.btn-reset:hover { background: #f1f5f9; color: #334155; border-color: #cbd5e1;}

.btn-upload {
  background: #ffffff; border: 1px solid #cbd5e1; color: #475569; padding: 12px 24px; cursor: pointer;
  border-radius: 30px; font-size: 15px; font-weight: 600; transition: all 0.2s; display: inline-flex; align-items: center;
}
.btn-upload:hover { border-color: #8b5cf6; color: #8b5cf6; background: #f5f3ff; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15); }

/* 模态框 */
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(6px); display: flex; justify-content: center; align-items: center; z-index: 100; animation: fadeIn 0.2s ease-out;
}
.modal-content { background: #ffffff; border-radius: 12px; width: 750px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 50px rgba(0,0,0,0.25); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 1; }
.modal-header h3 { margin: 0; font-size: 18px; color: #0f172a; font-weight: 700;}
.close-btn { background: transparent; border: none; color: #94a3b8; font-size: 26px; cursor: pointer; line-height: 1; transition: color 0.2s; }
.close-btn:hover { color: #ef4444; }
.modal-body { padding: 24px; }

/* Loading */
.loading-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 0; }
.loading-spinner {
  width: 48px; height: 48px; border: 4px solid #e2e8f0; border-top-color: #0ea5e9;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
.loading-text { margin-top: 20px; font-size: 18px; font-weight: 700; color: #0f172a; }
.loading-sub { margin-top: 8px; font-size: 14px; color: #64748b; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 标注图 */
.video-placeholder { width: 100%; height: 400px; background: #0f172a; border-radius: 8px; position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center; box-shadow: inset 0 0 20px rgba(0,0,0,0.5);}
.mock-vision-img { width: 100%; height: 100%; object-fit: contain; position: absolute; top: 0; left: 0; z-index: 1; }
.scan-line { position: absolute; width: 100%; height: 2px; background: #10b981; box-shadow: 0 0 12px #10b981, 0 0 24px #10b981; z-index: 2; animation: scan 2.5s linear infinite; }
.vision-tag { position: absolute; bottom: 12px; left: 12px; color: #ffffff; font-family: monospace; font-size: 15px; z-index: 3; background: #0ea5e9; padding: 6px 12px; border-radius: 4px; font-weight: bold; box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);}

/* 检测结果列表 */
.detection-list { margin-top: 20px; }
.detection-list h4 { margin: 0 0 12px; font-size: 16px; color: #0f172a; font-weight: 700; }
.det-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f1f5f9; }
.det-class {
  min-width: 80px; font-size: 14px; font-weight: 700; color: #0ea5e9;
  background: #f0f9ff; padding: 4px 10px; border-radius: 4px; text-align: center;
}
.conf-bar-wrap { flex: 1; height: 8px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.conf-bar { height: 100%; background: linear-gradient(90deg, #22c55e, #eab308, #ef4444); border-radius: 4px; transition: width 0.6s ease; }
.det-conf { min-width: 50px; text-align: right; font-family: monospace; font-size: 14px; font-weight: 700; color: #0f172a; }

/* 诊断报告 */
.report-details { margin-top: 20px; font-size: 15px; color: #334155; line-height: 1.6;}
.advice-box { background: #f0f9ff; border-left: 4px solid #0ea5e9; padding: 12px 16px; margin-top: 8px; border-radius: 0 6px 6px 0; font-weight: 500; color: #0369a1; white-space: pre-line;}

/* 错误状态 */
.error-container { display: flex; flex-direction: column; align-items: center; padding: 40px 0; }
.error-text { color: #ef4444; font-size: 16px; font-weight: 600; margin-bottom: 16px; text-align: center; }
.btn-retry {
  background: #ffffff; border: 1px solid #ef4444; color: #ef4444; padding: 10px 24px;
  border-radius: 30px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.btn-retry:hover { background: #fef2f2; }

@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
@keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
@keyframes scan { 0% { top: 0; } 100% { top: 100%; } }
</style>
