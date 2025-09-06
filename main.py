# wait_and_test.py
"""
等待服务启动并重试测试
"""

import requests
import time
from datetime import datetime

API_URL = 'https://glicko-fastapi-project-production.up.railway.app'

def test_connection(timeout=60):
    """等待并测试连接"""
    print(f"🔄 等待Railway服务启动...")
    print(f"API地址: {API_URL}")
    print(f"最大等待时间: {timeout}秒")
    print("-" * 50)
    
    start_time = time.time()
    attempt = 1
    
    while time.time() - start_time < timeout:
        print(f"\n尝试 #{attempt} - {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # 增加超时时间
            response = requests.get(f"{API_URL}/health", timeout=30)
            
            if response.status_code == 200:
                print("✅ 连接成功!")
                result = response.json()
                print("响应:", result)
                return True
            else:
                print(f"❌ HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ 超时，服务可能还在启动...")
        except requests.exceptions.ConnectionError:
            print("🔌 连接错误，服务可能还没准备好...")
        except Exception as e:
            print(f"❓ 其他错误: {e}")
        
        print(f"等待10秒后重试...")
        time.sleep(10)
        attempt += 1
    
    print(f"\n❌ 在{timeout}秒内无法连接到服务")
    return False

def quick_test():
    """快速功能测试"""
    print("\n🧪 进行快速功能测试...")
    
    endpoints = [
        ("/", "根路径"),
        ("/health", "健康检查"),
        ("/info", "API信息")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{API_URL}{endpoint}", timeout=30)
            if response.status_code == 200:
                print(f"✅ {name}: 正常")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {e}")

if __name__ == "__main__":
    print("🚂 Railway服务启动等待器")
    print("=" * 50)
    
    if test_connection(timeout=120):  # 等待最多2分钟
        quick_test()
        print("\n🎉 服务启动成功！")
        print(f"🔗 访问API文档: {API_URL}/docs")
    else:
        print("\n⚠️  服务启动超时，可能需要检查配置")
        print("建议:")
        print("1. 检查Railway部署日志")
        print("2. 确认main.py配置正确")
        print("3. 检查requirements.txt")
        print("4. 重新部署项目")
