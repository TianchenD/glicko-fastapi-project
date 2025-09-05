# main.py - 支持外部访问的版本
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from glicko import update_user_score_glicko2
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

app = FastAPI(
    title="Glicko评分更新API", 
    description="接收网球比赛数据并更新Glicko评分",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件 - 允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
)

# 定义请求数据模型
class GlickoRequest(BaseModel):
    user_score: float          # 2.0~5.0
    opp_score: float           # 2.0~5.0
    user_is_female: bool       # 女=True / 男=False
    user_win: bool             # 本盘胜负 True/False
    user_season_sets: int      # 本赛季已打盘数
    set_score: str             # "6-4" / "7:5" / "10-7"
    match_type: str            # "单打" / "双打"

    class Config:
        schema_extra = {
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

# 主要API端点
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

# 批量处理端点
@app.post("/update-glicko-batch")
async def update_glicko_batch(matches: list[GlickoRequest]):
    """批量处理多场比赛的评分更新"""
    try:
        results = []
        current_score = None
        
        for i, match in enumerate(matches):
            if i > 0 and current_score is not None:
                match.user_score = current_score
            
            original_score = match.user_score
            
            updated_score = update_user_score_glicko2(
                user_score=match.user_score,
                opp_score=match.opp_score,
                user_is_female=match.user_is_female,
                user_win=match.user_win,
                user_season_sets=match.user_season_sets,
                set_score=match.set_score,
                match_type=match.match_type
            )
            
            current_score = updated_score
            score_change = round(updated_score - original_score, 2)
            
            results.append({
                "match_number": i + 1,
                "original_score": original_score,
                "updated_score": updated_score,
                "score_change": score_change,
                "match_details": {
                    "opponent_score": match.opp_score,
                    "result": "胜利" if match.user_win else "失败",
                    "set_score": match.set_score,
                    "match_type": match.match_type
                }
            })
        
        return {
            "success": True,
            "message": f"成功处理 {len(matches)} 场比赛",
            "total_matches": len(matches),
            "final_score": current_score,
            "total_change": round(current_score - matches[0].user_score, 2) if matches else 0,
            "match_results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理错误: {str(e)}")

# 简单的测试端点（GET请求）
@app.get("/test-glicko")
async def test_glicko_get(
    user_score: float = 3.5,
    opp_score: float = 3.8,
    user_win: bool = True,
    set_score: str = "6-4"
):
    """简单的GET请求测试端点"""
    try:
        updated_score = update_user_score_glicko2(
            user_score=user_score,
            opp_score=opp_score,
            user_is_female=False,
            user_win=user_win,
            user_season_sets=5,
            set_score=set_score,
            match_type="单打"
        )
        
        return {
            "original_score": user_score,
            "updated_score": updated_score,
            "score_change": round(updated_score - user_score, 2),
            "test_parameters": {
                "user_score": user_score,
                "opp_score": opp_score,
                "user_win": user_win,
                "set_score": set_score
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Glicko评分服务正在运行",
        "version": "1.0.0",
        "endpoints": [
            "/update-glicko (POST)",
            "/update-glicko-batch (POST)", 
            "/test-glicko (GET)",
            "/health (GET)",
            "/docs (GET)"
        ]
    }

# API信息
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
            "POST /update-glicko-batch": "批量比赛评分更新",
            "GET /test-glicko": "简单测试（GET请求）",
            "GET /health": "健康检查",
            "GET /info": "API信息"
        },
        "example_usage": {
            "curl_post": "curl -X POST http://YOUR_IP:8000/update-glicko -H 'Content-Type: application/json' -d '{\"user_score\":3.5,\"opp_score\":3.8,\"user_is_female\":true,\"user_win\":true,\"user_season_sets\":5,\"set_score\":\"6-4\",\"match_type\":\"单打\"}'",
            "curl_get": "curl 'http://YOUR_IP:8000/test-glicko?user_score=3.5&opp_score=3.8&user_win=true&set_score=6-4'"
        }
    }

@app.get("/")
async def root():
    return {
        "message": "欢迎使用Glicko评分更新API",
        "version": "1.0.0",
        "documentation": "/docs",
        "api_info": "/info",
        "health_check": "/health"

    }
