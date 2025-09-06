# main.py - Railway兼容版本
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from glicko import update_user_score_glicko2

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

# 定义请求数据模型
class GlickoRequest(BaseModel):
    user_score: float
    opp_score: float
    user_is_female: bool
    user_win: bool
    user_season_sets: int
    set_score: str
    match_type: str

    class Config:
        json_schema_extra = {  # 使用新的配置名称
            "example": {
                "user_score": 3.5,
                "opp_score": 3.8,
                "user_is_female": True,
                "user_win": True,
                "user_season_sets": 5,
                "set_score": "6-4",
                "match_type": "单打"
            }
        }

# 定义响应数据模型
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
        "documentation": "/docs",
        "health_check": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Glicko评分服务正在运行",
        "version": "1.0.0",
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
        "endpoints": {
            "POST /update-glicko": "单场比赛评分更新",
            "GET /health": "健康检查",
            "GET /info": "API信息",
            "GET /docs": "API文档"
        }
    }

@app.post("/update-glicko", response_model=GlickoResponse)
async def update_glicko_score(request_data: GlickoRequest):
    """接收比赛数据并更新Glicko评分"""
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

# Railway需要这个配置来正确启动
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 启动服务器在端口 {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
