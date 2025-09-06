# main.py - 修复导入问题版本
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 确保可以导入glicko模块
try:
    from glicko import update_user_score_glicko2
    GLICKO_AVAILABLE = True
    print("✅ Glicko模块导入成功")
except ImportError as e:
    print(f"❌ Glicko模块导入失败: {e}")
    GLICKO_AVAILABLE = False

app = FastAPI(
    title="Glicko评分更新API", 
    description="接收网球比赛数据并更新Glicko评分",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class GlickoRequest(BaseModel):
    user_score: float
    opp_score: float
    user_is_female: bool
    user_win: bool
    user_season_sets: int
    set_score: str
    match_type: str

class GlickoResponse(BaseModel):
    success: bool
    message: str
    original_score: float
    updated_score: float
    score_change: float
    match_details: dict

@app.get("/")
async def root():
    return {
        "message": "欢迎使用Glicko评分更新API",
        "version": "1.0.0",
        "status": "running",
        "glicko_available": GLICKO_AVAILABLE,
        "documentation": "/docs",
        "health_check": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Glicko评分服务正在运行",
        "version": "1.0.0",
        "glicko_module": "available" if GLICKO_AVAILABLE else "not available",
        "python_version": sys.version,
        "environment": "production"
    }

@app.get("/info")
async def get_api_info():
    return {
        "api_name": "Glicko评分更新系统",
        "version": "1.0.0",
        "description": "用于网球比赛Glicko评分计算的REST API",
        "supported_match_types": ["单打", "双打"],
        "score_range": "2.0 - 5.0",
        "glicko_status": "available" if GLICKO_AVAILABLE else "not available",
        "endpoints": {
            "POST /update-glicko": "单场比赛评分更新",
            "GET /health": "健康检查",
            "GET /info": "API信息",
            "GET /debug": "调试信息",
            "GET /docs": "API文档"
        }
    }

@app.get("/debug")
async def debug_info():
    """调试信息端点"""
    import os
    return {
        "python_version": sys.version,
        "current_directory": os.getcwd(),
        "python_path": sys.path[:3],  # 只显示前3个路径
        "glicko_available": GLICKO_AVAILABLE,
        "environment_port": os.environ.get("PORT", "not set"),
        "files_in_directory": [f for f in os.listdir('.') if f.endswith('.py')]
    }

@app.post("/update-glicko", response_model=GlickoResponse)
async def update_glicko_score(request_data: GlickoRequest):
    """接收比赛数据并更新Glicko评分"""
    
    # 检查Glicko模块是否可用
    if not GLICKO_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Glicko评分模块不可用，请检查服务器配置"
        )
    
    try:
        original_score = request_data.user_score
        
        # 调用Glicko更新函数
        updated_score = update_user_score_glicko2(
            user_score=request_data.user_score,
            opp_score=request_data.opp_score,
            user_is_female=request_data.user_is_female,
            user_win=request_data.user_win,
            user_season_sets=request_data.user_season_sets,
            set_score=request_data.set_score,
            match_type=request_data.match_type
        )
        
        score_change = round(updated_score - original_score, 2)
        
        return GlickoResponse(
            success=True,
            message="评分更新成功",
            original_score=original_score,
            updated_score=updated_score,
            score_change=score_change,
            match_details={
                "opponent_score": request_data.opp_score,
                "match_result": "胜利" if request_data.user_win else "失败",
                "set_score": request_data.set_score,
                "match_type": request_data.match_type,
                "season_sets_played": request_data.user_season_sets,
                "is_female_player": request_data.user_is_female
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"输入数据错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理错误: {str(e)}")

# Railway启动配置
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 启动服务器在端口 {port}")
    print(f"Glicko模块状态: {'可用' if GLICKO_AVAILABLE else '不可用'}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
