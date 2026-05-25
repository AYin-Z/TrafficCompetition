# 改动日志：YOLO-Master 大模型推理接入演示系统

**日期：** 2026-04-22  
**目标：** 将前端 Demo 从纯硬编码模拟改造为可接入 YOLO 模型进行真实推理的演示系统

---

## 一、新增文件

### 1. `backend/main.py` — FastAPI 后端入口

- 启动时自动扫描 `backend/weights/` 目录加载 YOLO 权重文件
- 若无自定义权重，自动下载 yolov8n 预训练模型作为演示替代
- 启用 CORS 中间件，允许前端跨域请求
- 提供三个接口：
  - `GET /api/health` — 健康检查，返回模型加载状态
  - `POST /api/detect` — 接收上传图片，执行 YOLO 推理，返回标注图(base64) + 检测结果 + 诊断报告
  - `GET /api/detect-preloaded/{image_id}` — 对预置的 crack_1~4 图片直接推理（地图事故点点击时调用）

### 2. `backend/detect.py` — YOLO 推理封装

- `YOLODetector` 类：封装模型加载（`load()`）和推理（`detect()`）
- 推理流程：图片解码 → YOLO 推理 → 提取检测框/类别/置信度 → 绘制标注图 → 编码为 base64
- `DISEASE_ADVICE` 字典：病害类别 → 铁骑行动建议 + 无人机建议 的映射模板
  - 已预置：`zxlf`(纵向裂缝)、`hxlf`(横向裂缝)、`kc`(坑槽)、`xb`(修补)、`lj`(裂缝)、`bl`(剥落)、`sf`(渗水)
  - 未识别类别使用 `DEFAULT_ADVICE` 通用建议
- `generate_advice()` 函数：根据检测结果自动生成结构化诊断报告文本

### 3. `backend/requirements.txt` — Python 依赖

```
fastapi, uvicorn[standard], python-multipart, ultralytics, opencv-python, Pillow
```

### 4. `backend/weights/` — 权重文件目录（空，用户放入 .pt 文件）

### 5. `backend/images/` — 备用图片目录（也会自动搜索前端 src/assets/）

---

## 二、修改文件

### 1. `transport-demo/vite.config.js` — Vite 开发代理

**改动：** 新增 `server.proxy` 配置，将 `/api` 请求转发到 `http://localhost:8000`

```js
// 改动前
export default defineConfig({
  plugins: [vue()],
})

// 改动后
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### 2. `transport-demo/src/App.vue` — 核心组件全面改造

#### 模板（template）改动：

- **模态框重写**：
  - 新增 loading 状态：显示旋转动画 + "YOLO-Master 模型推理中..."
  - 标注图展示：从 `data:image/jpeg;base64,` + 后端返回的 base64 渲染
  - 新增检测目标列表：每个检测结果显示类别标签 + 置信度进度条 + 百分比
  - AI 诊断报告：展示后端自动生成的 `summary` 文本（替换原硬编码 advice）
  - 新增错误状态：显示错误信息 + 重试按钮
- **底部控制栏**：新增第 4 个按钮"上传自定义图片检测"（`<label>` 包裹隐藏 `<input type="file">`）

#### 脚本（script）改动：

- **移除**：硬编码的 `type`、`conf`、`advice` 字段（原 `anomalyPoints` 数组简化为只保留 `id`、`lnglat`、`imgUrl`）
- **新增状态变量**：
  - `isDetecting` — API 调用中的 loading 状态
  - `detectResult` — 后端返回的检测结果对象
  - `detectError` — 错误信息
  - `pendingPointId` — 当前待检测的事故点 ID（用于重试）
- **新增函数**：
  - `detectPreloaded(imageId)` — 调用 `GET /api/detect-preloaded/{id}`
  - `detectUploaded(file)` — 调用 `POST /api/detect`（FormData 上传）
  - `retryDetect()` — 错误后重试
  - `handleFileUpload(event)` — 处理文件选择事件
- **改动函数**：
  - `marker.on('click')` — 从直接赋值 `activeReport` 改为调用 `detectPreloaded()`
  - `closeModal()` — 关闭时同时清空 `detectResult` 和 `detectError`
  - `resetDemo()` — 重置时清空所有新增状态

#### 样式（style）改动：

- 新增 `.btn-upload` 样式（紫色悬停风格，与其他按钮区分）
- 新增 `.loading-container` / `.loading-spinner` / `.loading-text` — loading 动画
- 新增 `.detection-list` / `.det-item` / `.det-class` / `.conf-bar-wrap` / `.conf-bar` / `.det-conf` — 检测结果列表
- 新增 `.error-container` / `.error-text` / `.btn-retry` — 错误状态
- 新增 `@keyframes spin` — 旋转动画
- `.modal-content` 增加 `max-height: 90vh; overflow-y: auto` 防止内容溢出
- `.modal-header` 增加 `position: sticky; top: 0` 固定头部
- `.video-placeholder` 高度从 350px 调整为 400px

---

## 三、启动方式

```bash
# 终端 1：启动后端（端口 8000）
cd backend
python main.py

# 终端 2：启动前端（端口 5173，通过 proxy 转发 API）
cd 交科赛系统前端(1)/交科赛系统前端/transport-demo
npm run dev
```

## 四、待办

- [x] 将 YOLO-Master 自定义权重文件（.pt）放入 `backend/weights/`（`best.pt`）
- [x] 确认 `detect.py` 中的 `DISEASE_ADVICE` 字典覆盖了模型所有输出类别（8 类）
- [x] 预置图片：`crack_1`～`crack_6` 位于 `transport-demo/src/assets/`，并镜像至 `backend/images/`

---

## 五、补充（2026-04-22 演示图扩展）

- 用户提供的两张行车记录仪风格演示图已保存为 `src/assets/crack_5.jpg`、`crack_6.jpg`（由 PNG 复制为 `.jpg` 扩展名，便于与现有命名一致）。
- `App.vue`：`anomalyPoints` 增加 id 5、6 及对应坐标；空地协同调度改为 **3 机 + 3 骑**（`slice(0,3)` / `slice(3,6)`）。
- `main.py`：`detect-preloaded` 文档说明扩展为支持 `crack_1`～`crack_6`。
