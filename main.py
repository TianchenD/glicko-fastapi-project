# main.py - 最小工作版本
import os
from fastapi import FastAPI

# 创建FastAPI应用
app = FastAPI(title="Glicko API", version="1.0.0")

@app.get("/")
def read_root():
    return {
        "message": "Glicko API is running!",
        "status": "ok",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Service is running"
    }

@app.get("/test")
def test_endpoint():
    return {
        "test": "success",
        "message": "This is a test endpoint"
    }

# Railway启动配置
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(
        "main:app",  # 使用字符串引用
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
