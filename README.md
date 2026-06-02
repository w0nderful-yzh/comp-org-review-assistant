# 计算机组成原理复习助手

面向《计算机组成原理》课程的复习练习系统。基于学校已有的九章复习资料和作业题，提供章节练习、自动批改、错题本、学习统计和 AI 智能出题等功能。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + TypeScript |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL 16 (Docker) |
| AI 出题 | OpenAI 兼容接口 (可配置模型) |
| 认证 | JWT (python-jose + passlib/bcrypt) |
| 部署 | Docker Compose + Nginx |

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
- AI 生成时显示加载动画提示

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
- 总览：练习次数、作答总数、正确率、未掌握错题数
- 按章节展示掌握度评分（0-100 分）
- 综合考量：刷题数量、正确率、覆盖率、掌握率
- 掌握度等级：优秀(≥80)、良好(≥60)、一般(≥40)、待加强(<40)
- 学习建议和推荐功能

**知识库**
- 基于 9 章复习笔记 DOCX 解析的知识点和知识块
- 按章节浏览知识点
- 全文检索知识块内容

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
cp .env.example .env
# 编辑 .env 填入生产环境配置

# 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 初始化数据库（首次部署）
docker exec -i comp-org-postgres psql -U comp_org -d comp_org_review < docker/postgres/init/001_schema.sql
docker exec -i comp-org-postgres psql -U comp_org -d comp_org_review < docker/postgres/init/002_question_feedback.sql
docker exec -i comp-org-postgres psql -U comp_org -d comp_org_review < docker/postgres/init/003_question_source.sql
docker exec -i comp-org-postgres psql -U comp_org -d comp_org_review < docker/postgres/init/004_user_auth.sql

# 导入数据
docker exec -it comp-org-backend python scripts/seed_sample_questions.py
docker exec -it comp-org-backend python scripts/import_homework_questions.py
docker exec -it comp-org-backend python scripts/import_review_notes.py
```

访问 http://localhost (Nginx 反向代理)

### 环境变量说明

| 变量名 | 说明 |
|--------|------|
| `AI_API_KEY` | AI 服务 API Key |
| `AI_BASE_URL` | AI 服务地址 |
| `AI_MODEL_NAME` | AI 模型名称 |
| `SECRET_KEY` | JWT 认证密钥 |
| `TOKEN_ALGORITHM` | JWT 算法 (默认 HS256) |
| `TOKEN_EXPIRE_MINUTES` | Token 过期时间 (默认 480 分钟) |

## 目录结构

```
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py          # API 路由
│   │   │   └── deps.py            # 依赖注入（认证）
│   │   ├── models/entities.py     # 数据模型
│   │   ├── schemas/api.py         # 请求/响应 Schema
│   │   ├── services/              # 批改、AI 出题
│   │   └── core/
│   │       ├── config.py          # 配置
│   │       ├── database.py        # 数据库连接
│   │       ├── security.py        # JWT 认证
│   │       ├── limiter.py         # 速率限制
│   │       └── logging.py         # 日志配置
│   ├── scripts/                   # 数据导入和批量生成脚本
│   ├── tests/                     # 后端测试
│   └── Dockerfile                 # 后端容器配置
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginView.vue      # 登录页面（赛博朋克风格）
│   │   │   ├── GuideModal.vue     # 使用指南弹窗
│   │   │   ├── PracticeView.vue   # 练习页面
│   │   │   ├── WrongQuestionsView.vue  # 错题本
│   │   │   ├── StatsView.vue      # 学习统计
│   │   │   └── KnowledgeView.vue  # 知识库
│   │   ├── composables/
│   │   │   ├── useAuth.ts         # 认证状态管理
│   │   │   └── useSharedState.ts  # 共享状态
│   │   ├── api/client.ts          # API 客户端
│   │   └── styles/global.css      # 全局样式
│   ├── Dockerfile                 # 前端容器配置
│   └── nginx.conf                 # Nginx 配置
├── materials/                     # 课程资料（复习笔记、课件、作业）
├── docker/
│   └── postgres/init/             # 数据库初始化 SQL
├── docker-compose.yml             # 开发环境
└── docker-compose.prod.yml        # 生产环境
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

### 学习建议
1. 先完成"只做原题"模式，建立知识基础
2. 使用"标准练习"巩固知识
3. 关注学习统计中的章节掌握度，查漏补缺
4. 定期进行错题复盘，强化薄弱环节

## 免责声明

本系统知识库从 HDU 教学课件中提取，仅供学习参考使用。系统内容可能存在疏漏或偏差，不保证与教材完全一致。AI 生成的题目基于大语言模型，可能存在错误或不准确之处，请结合教材和课堂内容进行判断。本系统不构成任何形式的考试承诺或成绩保证，使用者应自行承担使用风险。如有疑问，请以任课教师的讲解和官方教材为准。

## 开发团队

- 计算机组成原理课程项目
- HDU 计算机学院
