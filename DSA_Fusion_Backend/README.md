# 🌌 DSA CORE // NEURAL_GRADER_V2

> **Automated Data Structures & Algorithms Evaluation Architecture**  
> Phân tích mã nguồn chuyên sâu qua AST, Neural AI (DeepSeek/Gemini), Safe Sandbox, và Cyber-Security Plagiarism Detection.

---

## 📋 MỤC LỤC

- [Tính Năng Nổi Bật](#-tính-năng-nổi-bật)
- [Kiến Trúc Hệ Thống (Decoupled MVC)](#-kiến-trúc-hệ-thống-decoupled-mvc)
- [Cấu Trúc Thư Mục](#-cấu-trúc-thư-mục)
- [Thiết Kế Cyber-Minimalist](#-thiết-kế-cyber-minimalist)
- [Hướng Dẫn Cài Đặt](#-hướng-dẫn-cài-đặt)

---

## ✨ TÍNH NĂNG NỔI BẬT

### **1. Giao Diện Cyber-Minimalist & Glassmorphism**
- 🌌 **Next.js 15+ & Tailwind**: Trải nghiệm siêu mượt với Dark Mode sâu, hiệu ứng kính mờ (Glassmorphism) và Neon accents.
- 🎯 **Neural Interface**: Giao diện tập trung vào dữ liệu với các hiệu ứng micro-interactions cao cấp và grid background kỹ thuật.
- 📊 **Command Center**: Dashboard quản trị viên thiết kế theo phong cách trung tâm điều khiển (Command Center) hiện đại.

### **2. Công Nghệ Chấm Điểm NEURAL CORE**
- 🧩 **AST Syntax Mapping**: Phân tích tĩnh nhận diện cấu trúc logic và thuật toán với độ chính xác cao.
- 🤖 **AI Neural Feedback**: Tích hợp mô hình AI để cung cấp phản hồi ngữ nghĩa sâu sắc và gợi ý tối ưu mã nguồn (Optimized Reference Code).
- 🛡️ **Safe-Node Sandbox**: Thực thi mã trong môi trường cô lập, giám sát tài nguyên thời gian thực.
- 🕵️ **Code Fingerprinting**: Phát hiện đạo văn dựa trên dấu vân tay logic mã nguồn, ngăn chặn sao chép tinh vi.

---

## 🏛️ KIẾN TRÚC HỆ THỐNG

Hệ thống được thiết kế theo mô hình **Decoupled MVC Architecture** kết hợp với **Service Layer Pattern**:

- **Model**: SQLAlchemy ORM định nghĩa thực thể tại `backend/app/models/`.
- **View**: Ứng dụng Next.js độc lập tại `frontend/` (Modern & Hi-Tech UI).
- **Controller**: FastAPI Routers điều phối yêu cầu qua RESTful API.
- **Engine Core**: Xử lý logic tại Service Layer (Grading, AI, Plagiarism).

---

## 📂 CẤU TRÚC THƯ MỤC

```text
DSA_Fusion_Final/
│
├── 📁 backend/                    # FastAPI Backend Server
│   ├── 📁 app/
│   │   ├── 📁 api/               # RESTful API Routes (auth, grading, admin)
│   │   ├── 📁 cache/             # Caching Layer (Redis & In-Memory)
│   │   ├── 📁 containers/        # Dependency Injection
│   │   ├── 📁 core/              # Config, Database, Models
│   │   ├── 📁 events/            # Event Bus System
│   │   ├── 📁 models/            # Pydantic Schemas
│   │   ├── 📁 schemas/           # Data Validation
│   │   ├── 📁 services/          # Business Logic
│   │   │   ├── 📁 ai_providers/  # AI Integration (Gemini, OpenAI)
│   │   │   └── 📁 grading/       # Grading Engine
│   │   ├── 📁 tests/             # Backend Unit Tests
│   │   └── 📁 utils/             # Helper Utilities
│   ├── 📁 data/
│   │   └── 📁 testcases/         # Test Case Data (20+ algorithms)
│   ├── 📁 deploy/                # Deployment Scripts (Linux/Windows)
│   ├── 📁 monitoring/            # Prometheus Monitoring Config
│   ├── requirements.txt          # Python Dependencies
│   └── .env                      # Environment Variables
│
├── 📁 frontend/                   # Next.js 15+ Frontend
│   ├── 📁 src/
│   │   ├── 📁 app/               # Next.js App Router Pages
│   │   ├── 📁 components/        # Reusable UI Components
│   │   └── 📁 store/             # State Management (Zustand)
│   ├── 📁 public/                # Static Assets
│   ├── package.json              # Node.js Dependencies
│   └── next.config.ts            # Next.js Configuration
│
├── 📁 infra/                      # Infrastructure & DevOps
│   ├── docker-compose.yml        # Docker Orchestration
│   └── Dockerfile.sandbox        # Sandboxed Execution Environment
│
├── 📁 data/                       # Shared Data Storage
│   └── 📁 rubrics/               # Grading Rubrics
│
├── 📁 logs/                       # Centralized Log Storage
│   └── .gitkeep                  # Directory Placeholder
│
├── main.py                        # Unified Application Entry Point
├── .gitignore                     # Git Ignore Rules
├── .dockerignore                  # Docker Ignore Rules
└── README.md                      # Project Documentation
```

### 🧹 Cleanup Guide (Automatic File Generation)

The system auto-generates temporary files during development. These are **safe to delete** anytime:

| Directory/File | Description | Regenerate Command |
|----------------|-------------|-------------------|
| `__pycache__/` | Python bytecode cache | Auto-generated on Python import |
| `.pytest_cache/` | Pytest test cache | `pytest` |
| `.next/` | Next.js build output | `npm run build` (in frontend/) |
| `out/` | Next.js static export | `npm run build` (in frontend/) |
| `*.tsbuildinfo` | TypeScript incremental build | Auto-generated on TypeScript compile |
| `*.log` | Application logs | Auto-generated during runtime |
| `node_modules/` | NPM dependencies | `npm install` (in frontend/) |
| `.venv/` | Python virtual environment | `python -m venv .venv && pip install -r requirements.txt` |

**To clean all temporary files:**
```bash
# Windows PowerShell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force backend\.pytest_cache, frontend\.next, frontend\out

# Linux/Mac
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf backend/.pytest_cache frontend/.next frontend/out
```

---

## 💻 HƯỚNG DẪN CÀI ĐẶT

### **Development Mode**
1. Khởi động Neural Backend: `cd backend && uvicorn app.main:app --reload`
2. Khởi động Cyber Frontend: `cd frontend && npm run dev`

### **Production Deployment**
1. Đóng gói Frontend: `cd frontend && npm run build`
2. Chạy Unified Server: `python main.py`

---

**Phiên bản:** Unknown ??? 
**Trạng thái:** ✅ STABLE // NEURAL_GRADER_ACTIVE  
