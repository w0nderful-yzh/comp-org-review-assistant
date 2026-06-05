# 计算机组成原理复习助手

面向《计算机组成原理》课程的复习练习系统。基于学校已有的九章复习资料和作业题，提供章节练习、自动批改、错题本、学习统计、AI 智能出题、历年真题模拟、实验模拟考试等功能。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + TypeScript |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL 16 (Docker) |
| AI 出题 | OpenAI 兼容接口 (可配置模型) |
| 认证 | JWT (python-jose + passlib/bcrypt) |
| 部署 | Docker Compose + Caddy (自动 HTTPS) |

## 项目完成情况

### 已交付功能

**用户认证系统**
- 学号（8位数字）+ 密码登录注册
- JWT Token 认证，支持多用户并发
- 登录后显示使用指南弹窗（首次登录）
- 免责声明（弹窗内 + 页面底部）

**练习系统**
- 按 9 个章节分别练习，支持总复习跨章节随机抽题
- 题型：单选、多选、判断、填空、简答、计算
- 自动批改与评分，提交后即时显示正确答案和解析
- 题目来源标签（作业原题 / AI 生成 / 样例题）

**四种练习模式**
- 📚 **只做原题**：仅练习原始题库中的题目
- ⭐ **标准练习**：原题 + 已验证的 AI 好题
- 👥 **社区 AI 题库**：社区用户共创的 AI 题目
- ✨ **AI 新题**：实时生成全新 AI 题目

**AI 题目生态系统**
- AI 题目生命周期：临时 → 候选 → 社区认可 → 已验证
- 完成 AI 新题后可为题目点赞/踩
- 优质题目自动进入社区题库
- 每日 AI 生成限额：50 道题
- 常规出题超时按题数动态计算（30s + 30s/题），整卷生成独立 5 分钟超时

**题目用尽处理**
- 当题库题目全部完成时，提示用户选择：
  1. 进行错题复盘
  2. 再刷一遍
  3. 进行 AI 加练

**错题本**
- 自动记录答错题目，支持多次错题计数
- 错题重练：从错题本中抽题重新练习
- 标记已掌握功能

**学习统计**
- 总览：练习次数、作答总数、正确率、未掌握错题数（SVG 环形进度图）
- 按章节展示掌握度评分（0-100 分），进度条带 shimmer 光泽动画
- 综合考量：刷题数量、正确率、覆盖率、掌握率
- 掌握度等级：优秀(≥80)、良好(≥60)、一般(≥40)、待加强(<40)
- 学习建议和推荐功能
- 卡片交错入场动画

**历年真题模拟**
- 收录 2017–2023 年共 7 套历年真题试卷（PDF 原卷 + 答案）
- 结构化题目数据，逐题逐问作答，自动计时
- 原卷配图缩放查看，支持原卷/答案 PDF 预览与下载
- 年份卡片网格选择，含题目数、总分、示意图标识

**实验模拟考试**
- AI 生成实验模拟试卷（基于 RISC-V RV32I + 多周期模型机）
- 覆盖选择题、汇编分析、CPU 设计（FSM/控制信号/Verilog）、拓展题
- 每日限额 1 次，后台异步生成，生成完成通知

**知识库**
- 基于 9 章复习笔记 DOCX 解析的知识点和知识块
- 按章节浏览知识点
- 全文检索知识块内容
- 课件 PDF 在线预览与下载

**彩蛋 & 视觉美化**
- 二进制雨背景动画（Canvas 0/1 飘落）
- 侧栏 Logo「组」可点击轮换为计/机/存/算/指/流等字符，带 360° 旋转
- 键盘彩蛋：输入 `comporg` / `riscv` / `alu` / `cpu` 触发粒子爆发 + 金色 toast
- 顶栏版本号可点击切换（流水线级 → 超标量级 → Alpha 0xDEAD…）
- 底部自动轮播计组冷知识（10 条）
- 统计页 SVG 环形进度图、进度条 shimmer 光泽
- 答题反馈动画（正确弹跳、错误抖动）、卡片悬浮光晕、骨架屏加载态

**数据导入**
- 从作业文本文件批量导入题目（`scripts/import_homework_questions.py`）
- 从 DOCX 复习笔记导入知识点和知识块（`scripts/import_review_notes.py`）
- 样例题种子数据（`scripts/seed_sample_questions.py`）

## 快速启动

### 1. 启动数据库

```bash
docker compose up -d
```

### 2. 启动后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 配置 AI API Key 和认证密钥
cp .env.example .env
# 编辑 .env 填入 AI_API_KEY 和 SECRET_KEY

# 导入数据
cd backend
python scripts/seed_sample_questions.py
python scripts/import_homework_questions.py
python scripts/import_review_notes.py

# 批量生成 AI 题目（可选，自动跳过题目充足的章节）
python scripts/batch_generate_ai.py

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 生产部署

### Docker Compose 部署

```bash
# 创建 .env 文件并配置
cp .env.production.example .env
# 编辑 .env，至少修改 POSTGRES_PASSWORD、SECRET_KEY。
# 有域名后把 PUBLIC_SITE_ADDRESS 改为你的域名，例如 review.example.com。

# 启动所有服务
docker compose -f docker-compose.prod.yml up -d --build

# 首次创建 postgres_data 数据卷时，docker/postgres/init/*.sql 会自动初始化数据库。

# 导入数据
docker exec -it comp-org-backend python scripts/seed_sample_questions.py
docker exec -it comp-org-backend python scripts/import_homework_questions.py
docker exec -it comp-org-backend python scripts/import_review_notes.py

# 可选：提前批量生成 AI 题
docker exec -it comp-org-backend python scripts/batch_generate_ai.py
```

访问 `http://服务器IP`。绑定域名并把 `.env` 中的 `PUBLIC_SITE_ADDRESS` 改成域名后，Caddy 会自动申请 HTTPS 证书。

### 数据库备份与迁移

```bash
# 1. 本地导出数据库
./scripts/db_backup.sh export

# 2. 将备份文件上传到服务器
scp ./backups/comp_org_backup_*.sql.gz user@server:/path/to/project/

# 3. 服务器上导入（先启动容器，再导入）
docker compose -f docker-compose.prod.yml up -d
./scripts/db_backup.sh import ./backups/comp_org_backup_*.sql.gz

# 查看数据库状态
./scripts/db_backup.sh status
```

备份包含：章节、知识点、所有题目（含 AI 题）、练习记录、错题本、用户账号、知识库。

### 服务器更新

```bash
cd /path/to/project
git pull origin main

# 仅代码变更时重建 backend/frontend
docker compose -f docker-compose.prod.yml up -d --build

# materials/ 是 volume 挂载，git pull 后自动生效，无需重建
```

### 服务架构

```
Caddy (:80/:443) → Frontend (Nginx :80) → Backend (FastAPI :8000) → PostgreSQL (:5432)
```

### 环境变量说明

| 变量名 | 说明 |
|--------|------|
| `PUBLIC_SITE_ADDRESS` | 公网访问地址，临时 IP 部署用 `:80`，域名部署用真实域名 |
| `CORS_ORIGINS` | 允许跨域访问的前端来源，通常填公网 HTTP/HTTPS 地址 |
| `AI_API_KEY` | AI 服务 API Key |
| `AI_BASE_URL` | AI 服务地址 |
| `AI_MODEL` | AI 模型名称 |
| `AI_ENABLED` | 是否启用 AI 出题 |
| `AI_REQUEST_TIMEOUT` | AI 请求超时秒数（默认 45s，常规出题按题数动态计算） |
| `COURSEWARE_PDF_DIR` | 课件 PDF 目录，生产容器默认 `/materials/courseware-pdfs` |
| `SECRET_KEY` | JWT 认证密钥 |
| `TOKEN_ALGORITHM` | JWT 算法 (默认 HS256) |
| `TOKEN_EXPIRE_MINUTES` | Token 过期时间 (默认 1440 分钟) |

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py              # API 路由
│   │   │   └── deps.py                # 依赖注入（认证）
│   │   ├── models/entities.py         # 数据模型
│   │   ├── schemas/api.py             # 请求/响应 Schema
│   │   ├── services/
│   │   │   ├── ai_generation.py       # AI 题目生成
│   │   │   └── lab_exam_generation.py # 实验模拟卷 AI 生成
│   │   └── core/
│   │       ├── config.py              # 配置
│   │       ├── database.py            # 数据库连接
│   │       ├── security.py            # JWT 认证
│   │       ├── limiter.py             # 速率限制
│   │       └── logging.py             # 日志配置
│   ├── scripts/                       # 数据导入和批量生成脚本
│   │   ├── structure_exam_papers.py   # 历年试卷结构化
│   │   ├── download_exam_papers.py    # 试卷下载
│   │   └── crop_exam_diagrams.py      # 试卷配图裁剪
│   ├── tests/                         # 后端测试
│   └── Dockerfile                     # 后端容器配置
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginView.vue          # 登录页面
│   │   │   ├── GuideModal.vue         # 使用指南弹窗
│   │   │   ├── PracticeView.vue       # 练习页面
│   │   │   ├── ExamMockView.vue       # 历年真题模拟
│   │   │   ├── LabExamMockView.vue    # 实验模拟考试
│   │   │   ├── WrongQuestionsView.vue # 错题本
│   │   │   ├── StatsView.vue          # 学习统计
│   │   │   ├── KnowledgeView.vue      # 知识库
│   │   │   └── BinaryRain.vue         # 二进制雨背景
│   │   ├── composables/
│   │   │   ├── useAuth.ts             # 认证状态管理
│   │   │   ├── useSharedState.ts      # 共享状态
│   │   │   └── useEasterEggs.ts       # 彩蛋逻辑
│   │   ├── api/client.ts              # API 客户端
│   │   └── styles/global.css          # 全局样式
│   ├── Dockerfile                     # 前端容器配置
│   └── nginx.conf                     # Nginx 配置
├── materials/                         # 课程资料
│   ├── exam-papers/                   # 历年真题（PDF + 图片 + JSON）
│   ├── lab-exams/                     # 实验模拟卷（静态模板 + 格式参考）
│   └── courseware-pdfs/               # 课件 PDF
├── scripts/
│   └── db_backup.sh                   # 数据库备份与恢复脚本
├── deploy/
│   └── Caddyfile                      # Caddy 反向代理配置
├── docker/
│   └── postgres/init/                 # 数据库初始化 SQL
├── docker-compose.yml                 # 开发环境
└── docker-compose.prod.yml            # 生产环境
```

## 使用说明

### 首次登录
1. 使用学号（8位数字）和密码注册账号
2. 登录后会显示使用指南弹窗
3. 可选择"下次不再显示"来关闭弹窗

### 练习模式选择
- **只做原题**：适合初次练习，熟悉基础知识点
- **标准练习**：原题 + 社区验证的 AI 好题，巩固知识
- **社区 AI 题库**：社区用户共创的 AI 题目，拓展练习
- **AI 新题**：实时生成新题，每日限额 50 道

### 真题模拟
- 选择年份进入模拟考试，系统自动计时
- 逐题逐问作答，支持原卷配图缩放查看
- 可随时查看原卷 PDF 或答案 PDF

### 实验模拟
- AI 生成基于 RISC-V 的实验模拟试卷
- 每日限生成 1 次，生成完成后可反复练习

### 学习建议
1. 先完成"只做原题"模式，建立知识基础
2. 使用"标准练习"巩固知识
3. 尝试"真题模拟"检验综合能力
4. 关注学习统计中的章节掌握度，查漏补缺
5. 定期进行错题复盘，强化薄弱环节

### 彩蛋发现
- 🖱️ 点击侧栏金色「组」Logo
- ⌨️ 在页面任意位置输入 `comporg`、`riscv`、`alu`、`cpu`
- 🏷️ 点击顶栏版本号
- 👀 关注底部轮播冷知识

## 免责声明

本系统知识库从 HDU 教学课件中提取，仅供学习参考使用。系统内容可能存在疏漏或偏差，不保证与教材完全一致。AI 生成的题目基于大语言模型，可能存在错误或不准确之处，请结合教材和课堂内容进行判断。本系统不构成任何形式的考试承诺或成绩保证，使用者应自行承担使用风险。如有疑问，请以任课教师的讲解和官方教材为准。
