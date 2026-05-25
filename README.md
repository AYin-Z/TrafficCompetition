# 智巡速诊：道路病害的快速发现及精准诊断系统

> **交通科技大赛参赛作品 | 空地协同 · 道路病害检测 · 态势感知**

基于 **YOLOv8 + FastAPI + Vue 3** 的全栈路面病害检测系统，深度融合空地协同调度策略，实现道路病害从检测识别到应急处置的全链路闭环。

## 系统架构

```
                         ┌──────────────────┐
                         │   前端 (Vue 3)    │
                         │  端口 5173 (dev)  │
                         │  高德地图 JS API  │
                         └────────┬─────────┘
                                  │ /api (Vite proxy)
                         ┌───────┴──────────┐
                         │  后端 (FastAPI)   │
                         │  端口 8000        │
                         │  YOLOv8 推理引擎   │
                         └──────────────────┘
```

## 项目结构

```
TrafficCompetition/
├── frontend/                 # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── assets/           # 预设病害图片 (crack_1~6)
│   │   ├── components/       # UI 组件
│   │   ├── composables/      # 可复用逻辑 (检测/地图)
│   │   ├── App.vue           # 主应用入口
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── vite.config.js         # 代理 /api → localhost:8000
│   └── package.json
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # API 路由 & 服务入口
│   │   ├── detector.py        # YOLOv8 推理封装
│   │   ├── disease_advice.py  # 病害处置知识库 & 建议生成
│   │   ├── weights/           # 自定义训练权重
│   │   └── images/            # 预设检测图片
│   ├── run.py                 # 快捷启动
│   └── requirements.txt
├── docs/                      # 项目文档
│   ├── ref-paper.pdf          # 参考论文
│   ├── 立项申请书.docx        # 2026 年学生科研项目立项申请书
│   └── dev-log.md             # 开发日志
├── deploy/                    # 部署配置
│   └── docker-compose.yml
└── README.md
```

## 病害检测类别

| 类别 | 名称 | 处置策略 |
|------|------|----------|
| lmlj | 路面裂缝 | 灌缝密封 |
| hbgdf | 横斑/龟裂/断缝 | 挖除重建 |
| hxlf | 横向裂缝 | 密封胶处理 |
| zxlf | 纵向裂缝 | 热灌缝 |
| jl | 井盖缺损 | 市政更换 |
| kc | 坑槽 | 热沥青重铺 |
| ssf | 松散/碎裂 | 铣刨重铺 |
| CZ | 车辙 | 铣刨罩面 |

每类病害均配有两套处置方案：**铁骑行动**（地面交警快速响应）与**无人机建议**（养护施工深度方案）。

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py
# → http://localhost:8000
# → API 文档: http://localhost:8000/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Docker (一键部署)

```bash
docker compose -f deploy/docker-compose.yml up -d
```

## 演示流程

1. 打开页面 → 点击 **"触发路网风险热力爆变"**（模拟异常数据注入）
2. 态势面板风险指数突破阈值 → 点击 **"启动空地协同调度"**（3机+3骑动画）
3. 智能体抵达 → 点击 **"激活病害精细化识别"**（YOLOv8 推理预设图片）
4. 查看检测结果 → 置信度条 + 协同处置研判报告

## 技术栈

- **目标检测**: Ultralytics YOLOv8 (PyTorch)
- **后端框架**: FastAPI + Uvicorn
- **前端框架**: Vue 3 (Composition API) + Vite
- **地图引擎**: 高德地图 JS API
- **图像处理**: OpenCV + Pillow
