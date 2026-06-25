# Poly XInsight

聚合物复合材料 AI 智能助手 — 文献上传、解析、嵌入、检索、知识抽取与可视化分析一站式平台。

## 项目结构

```
PolyAgent/
├── backend/          # 后端服务（FastAPI + Milvus + Elasticsearch + PostgreSQL）
├── bge-api/          # BGE-M3 文本嵌入微服务（FlagEmbedding）
├── frontend/         # 前端界面（Next.js 14 + Tailwind CSS + shadcn/ui）
├── scripts/          # 运维工具脚本（部署、测试、环境检查）
├── docker-compose.yml # 全栈容器化编排文件
├── .env.example      # 环境变量模板
└── LOCAL_SETUP.md    # 本地搭建说明
```

## 各目录功能

### `backend/` — 后端服务

基于 FastAPI 构建，是整个系统的核心，包含以下模块：

| 子目录 | 功能 |
|--------|------|
| `routes/` | API 路由层，包括文献上传(`upload`)、论文管理(`papers`)、RAG 对话(`chat`)、知识抽取(`extract`)、可视化(`visualize`)、实体浏览(`entities`)、分析看板(`analytics`)、用户认证(`auth`)、对话历史(`conversations`)、领域管理(`domains`)、论文下载(`downloads`)、知识图谱(`knowledge_graph`) |
| `services/` | 业务逻辑层 — PDF 解析、文本分块、嵌入向量生成、混合检索(Milvus + ES)、RAG 对话、实体挖掘、材料属性抽取（导热高分子 / 固态电解质）、Schema 收敛、主题导航等 |
| `models/` | 数据库模型定义（SQLAlchemy ORM）与 Pydantic schema |
| `llm/` | LLM 统一接入层，支持 DeepSeek / OpenAI 兼容接口 |
| `tests/` | 24 个测试文件，覆盖分块、嵌入、检索、抽取、对话路由等 |

核心数据流：**PDF 上传 → 解析 → 分块 → 嵌入 → 存入 Milvus + ES → RAG 检索 → LLM 回答**

### `bge-api/` — 嵌入服务

独立的 FastAPI 微服务，加载 `BAAI/bge-m3` 模型提供文本向量化 API：
- 支持 GPU/CPU 自动检测
- 支持 HuggingFace / ModelScope 双源下载
- 提供 `/embed`（向量化）和 `/health`（健康检查）端点

### `frontend/` — 前端界面

基于 Next.js 14 + React 18 构建，使用 Tailwind CSS + shadcn/ui 组件库：

| 页面 | 路由 | 功能 |
|------|------|------|
| 文献库 | `/library` | 按领域/分类浏览已上传论文 |
| AI 对话 | `/` | 基于 RAG 的文献智能问答 |
| 实体挖掘 | `/entities` | 浏览抽取的材料实体与属性 |
| 数据看板 | `/analytics` | 领域数据分析与图表可视化 |
| 知识图谱 | `/graph` | 实体关系图谱浏览 |
| 论文下载 | `/downloads` | Sci-Hub 论文检索下载 |
| 登录/注册 | `/login`, `/register` | 用户认证 |

### `scripts/` — 运维脚本

| 脚本 | 用途 |
|------|------|
| `deploy.py` / `deploy_build.py` | 远程部署与构建 |
| `deploy_setup.sh` | 服务器初始化配置 |
| `smoke_test.sh` | 冒烟测试（API 健康检查） |
| `test_chat.sh` | 对话接口测试 |
| `ssh_check.py` | SSH 连通性检查 |
| `install_docker.sh` | Docker 安装脚本 |
| `fix_llm.sh` | LLM 配置修复 |

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python) |
| 向量数据库 | Milvus 2.5 |
| 全文检索 | Elasticsearch 8.15 |
| 关系数据库 | PostgreSQL 16 |
| 嵌入模型 | BGE-M3 (BAAI) |
| LLM 接入 | DeepSeek / OpenAI 兼容 API |
| 前端框架 | Next.js 14 + React 18 |
| UI 组件 | shadcn/ui + Tailwind CSS |
| 可视化 | ECharts 6 |
| 容器化 | Docker Compose |
| 对象存储 | MinIO（Milvus 依赖） |
| 协调服务 | etcd（Milvus 依赖） |

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY 等配置
```

### 2. 启动服务

```bash
docker compose up -d --build
```

### 3. 访问应用

- 前端界面：`http://localhost:3000`
- 后端健康检查：`http://localhost:8080/api/health`
- BGE 嵌入服务：`http://localhost:8001/health`

## 要求

- Docker & Docker Compose
- （可选）NVIDIA GPU + nvidia-container-toolkit（用于 BGE-M3 GPU 推理加速）
