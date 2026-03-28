import sklearn
import sklearn.ensemble
import sklearn.tree
import sklearn.utils._cython_blas
import sklearn.neighbors.typedefs
import sklearn.neighbors.quad_tree
import sklearn.tree._utils
import requests
import re
import pandas as pd
import joblib
import os
import sys
import random
import urllib.parse
import jieba
import logging
import warnings

warnings.filterwarnings("ignore")
jieba.setLogLevel(logging.ERROR)

def jieba_tokenize(text):
    return jieba.lcut(text)

USER_AGENTS =[
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
]

# 核心魔法：使用 Session 保持“游客状态”
session = requests.Session()
visitor_initialized = False

def init_visitor():
    """先访问主页，拿取B站发给未登录游客的临时Cookie和通行证"""
    global visitor_initialized
    if visitor_initialized:
        return
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }
    try:
        # 访问主页，Session 会自动记住返回的匿名 Cookie
        session.get("https://www.bilibili.com", headers=headers, timeout=5)
        visitor_initialized = True
    except:
        pass

def search_bilibili(keyword):
    init_visitor() # 搜索前确保已经拿到了游客通行证
    
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {'search_type': 'video', 'keyword': keyword, 'page': 1}
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': f'https://search.bilibili.com/all?keyword={urllib.parse.quote(keyword)}',
        'Origin': 'https://search.bilibili.com'
    }
    
    print(f"\n正在 B站 搜索: {keyword} ...")
    try:
        # 这里用 session.get 而不是 requests.get，带着通行证去搜！
        res = session.get(url, params=params, headers=headers, timeout=10)
        data = res.json()
        
        # 如果依然被风控（通常返回 code -412），给出明确提示
        if data.get('code') == -412:
            print("⚠️ 警告：当前网络 IP 被 B站 防火墙拦截了！")
            print("💡 解决方法：请断开当前网络，连接一下手机热点更换IP即可解决。")
            return[]
            
        items = data.get('data', {}).get('result',[])
    except Exception as e:
        print(f"网络请求失败: {e}")
        return []
    
    videos =[]
    for item in items:
        clean_title = re.sub(r'<[^>]+>', '', item.get('title', ''))
        duration_str = item.get('duration', '0:0')
        try:
            parts = duration_str.split(':')
            duration_sec = int(parts[0]) * 60 + int(parts[1])
        except:
            duration_sec = 0
            
        videos.append({
            'title': clean_title,
            'author': item.get('author', ''),
            'duration': duration_sec,
            'play': item.get('play', 0),
            'bvid': item.get('bvid', '')
        })
    
    return videos

def ai_rank_videos(videos, model):
    df = pd.DataFrame(videos)
    df['text_feature'] = df['title'] + " " + df['author']
    
    predictions = model.predict(df[['text_feature', 'duration', 'play']])
    probabilities = model.predict_proba(df[['text_feature', 'duration', 'play']])
    
    for i in range(len(videos)):
        videos[i]['score'] = predictions[i]
        class_index = list(model.classes_).index(predictions[i])
        videos[i]['prob'] = probabilities[i][class_index] 
        
    ranked = sorted(videos, key=lambda x: (x['score'], x['prob']), reverse=True)
    return ranked

def download_video(bvid, title):
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    print(f"\n======== 开始下载 ========")
    print(f"目标: {safe_title} (BVID: {bvid})")
    print("下载中，请稍候...")
    
    # 核心修改：在 -S 后面加入了 vcodec:h264
    # 完整含义：首选 H.264 编码，最高 720P 画质，合并为 mp4 格式
    cmd = f'yt-dlp -q --no-warnings --extractor-args "bilibili:player_client=android" -S "vcodec:h264,res:720,ext:mp4:m4a" -o "{safe_title}.%(ext)s" "https://www.bilibili.com/video/{bvid}"'
    os.system(cmd)
    
    print("======== 下载完成 ========\n")
def load_ai_model():
    # 核心逻辑：获取当前 .exe 或 .py 所在的文件夹路径
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境
        base_path = os.path.dirname(sys.executable)
    else:
        # 普通 python 环境
        base_path = os.path.dirname(os.path.abspath(__file__))

    model_path = os.path.join(base_path, 'music_model.pkl')
    
    # 打印一下路径，方便在 CMD 里调试看它到底在找哪儿
    print(f"正在尝试从以下位置加载 AI 模型: {model_path}")

    if not os.path.exists(model_path):
        # 这里会打印出程序实际寻找的路径，如果报错，你会一眼看到问题
        print(f"❌ 错误：在文件夹内找不到 music_model.pkl")
        print(f"请检查文件是否存在于: {base_path}")
        return None

    try:
        model = joblib.load(model_path)
        print("✅ AI 模型加载成功！")
        return model
    except Exception as e:
        print(f"❌ 模型加载失败，可能是版本不匹配：\n{e}")
        return None
def main():
    model = load_ai_model()
    if model is None: sys.exit()

    while True:
        # 为了让第一步点播就在原位，不再在上面打印多余信息
        song = input("请输入歌曲名")
        if song.lower() == 'q': break
        
        mode = input("请选择模式 (1.手动 2.半自动 3.全自动): ")
        if mode not in ['1', '2', '3']:
            print("输入错误，请重新选择。\n")
            continue
            
        videos = search_bilibili(song)
        total_count = len(videos)
        
        if total_count == 0:
            print("未找到任何视频，请换个关键词试试。")
            continue
            
        print(f"成功获取第一页全部 {total_count} 个视频！")
            
        if mode == '1': # 手动模式
            print(f"\n--- 搜索结果 (共 {total_count} 个) ---")
            for i, v in enumerate(videos):
                print(f"[{i+1}] {v['title']} | UP: {v['author']} | 时长: {v['duration']}s | 播放: {v['play']}")
            idx = int(input(f"\n请输入你要下载的序号(1-{total_count}): ")) - 1
            download_video(videos[idx]['bvid'], videos[idx]['title'])
            
        else: # AI 参与模式
            ranked_videos = ai_rank_videos(videos, model)
            
            if mode == '2': # 半自动
                print("\n--- AI 为您筛选出的 Top 3 ---")
                top3 = ranked_videos[:3]
                for i, v in enumerate(top3):
                    print(f"[{i+1}] (AI评分:{v['score']}) {v['title']} | UP: {v['author']}")
                idx = int(input("\n请输入你要下载的序号(1-3): ")) - 1
                download_video(top3[idx]['bvid'], top3[idx]['title'])
                
            elif mode == '3': # 全自动
                best = ranked_videos[0]
                if best['score'] == 0:
                    print(f"\n⚠️ 警告：AI扫遍了 {total_count} 个视频，认为排名第一的视频也不适合(得分0)！")
                    print(f"标题：{best['title']}")
                    force = input("是否强制下载？(y/n): ")
                    if force.lower() == 'y':
                        download_video(best['bvid'], best['title'])
                else:
                    print(f"\n🎯 AI 已从 {total_count} 个视频中自动锁定最佳选择 (得分:{best['score']})！")
                    print(f"标题: {best['title']} | UP主: {best['author']}")
                    download_video(best['bvid'], best['title'])

if __name__ == "__main__":
    main()
