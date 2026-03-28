import requests
import pandas as pd
import re
import time
import os
from urllib.parse import quote  # 导入编码工具

def search_bilibili(keyword):
    # 1. 对关键词进行 URL 编码，解决 latin-1 报错问题
    encoded_keyword = quote(keyword)
    
    print(f"正在搜索: {keyword} ...")
    
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        'search_type': 'video',
        'keyword': keyword, # params 里的中文 requests 会自动处理，不用担心
        'page': 1,
        'page_size': 20
    }
    
    # 2. 在 Referer 中使用编码后的关键词
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://search.bilibili.com/all?keyword={encoded_keyword}',
        # 如果依然返回 -412 错误，请取消下面这行的注释并填入你的 Cookie
        'Cookie': "buvid3=05F65891-9A80-CEF4-573C-34AC1E741ECC29339infoc; b_nut=1774677229; bsource=search_bing; _uuid=D99DE5B7-8284-54A8-E2F5-FED78EFA1049F87220infoc; bmg_af_switch=1; bmg_src_def_domain=i0.hdslb.com; buvid_fp=e69b60c0497bf8fe189300b89fc45adf; buvid4=9F87B1B8-6501-C98A-2293-019138D8EFE130544-026032813-Dc4XJZfzpAB1Hw92vpu41g%3D%3D; CURRENT_QUALITY=0; rpdid=|(k)YmRY)uJR0J'u~~RY~~kRl; home_feed_column=4; browser_resolution=890-794; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzQ5NDAyMDMsImlhdCI6MTc3NDY4MDk0MywicGx0IjotMX0.htRwVdB7Y3UAynDjxYJLDXbx3AXP-iipUR6GvqNy0EU; bili_ticket_expires=1774940143; SESSDATA=891afd62%2C1790233019%2C25c1d%2A32CjANhjgG_wcgIXkpDNRl40OEb8AKXVV_GJ8E6G9j7olTZwWgKIltuEg6qHRhXlc0JjMSVnBlYWZza3JJOTIxaTJTTG5sM0xhbm5aYmFJMHVEa05iY3J0OXFVRjhCZ1RiaFZvN0E0a2l5eVJLR1FZU2tNM2ZLVWhpbC1scXk3akpBS2ZqTjVpWGpRIIEC; bili_jct=b4f8a9f9c5894c44c546fc964c385565; DedeUserID=3546563771107975; DedeUserID__ckMd5=10d7f5633d94eada; theme-tip-show=SHOWED; sid=896i0s7c; CURRENT_FNVAL=4048; bp_t_offset_3546563771107975=1184735169181908992; b_lsid=9998C3C9_19D333CB802"
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        
        if res.status_code != 200:
            print(f"请求失败，状态码: {res.status_code}")
            return []
            
        data = res.json()
        
        if data.get('code') != 0:
            print(f"B站拒绝了请求，错误代码: {data.get('code')}, 信息: {data.get('message')}")
            if data.get('code') == -412:
                print(">>> 触发了频率限制！请务必在 headers 中加入你的 Cookie 才能继续。")
            return []

        # 这里的解析逻辑保持不变
        items = data.get('data', {}).get('result', [])
        if not isinstance(items, list):
            items = []

        video_list = []
        for item in items:
            raw_title = item.get('title', '')
            clean_title = re.sub(r'<[^>]+>', '', raw_title)
            
            duration_str = item.get('duration', '0:0')
            try:
                parts = duration_str.split(':')
                if len(parts) == 3: 
                    duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else: 
                    duration_sec = int(parts[0]) * 60 + int(parts[1])
            except:
                duration_sec = 0
                
            video_list.append({
                'keyword': keyword,
                'title': clean_title,
                'author': item.get('author', ''),
                'duration': duration_sec,
                'play': item.get('play', 0),
                'bvid': item.get('bvid', ''),
                'score': '' 
            })
        return video_list

    except Exception as e:
        print(f"搜索 {keyword} 发生异常: {e}")
        return []

if __name__ == "__main__":
    # 建议先用这 3 个词测试，成功后可以扩展到 50 个词以上来增加训练量
    song_list = ["周杰伦 晴天", "起风了", "孤勇者", "林俊杰 江南", 
        "米津玄师 Lemon", "后来 刘若英", "deadman",
        "青花瓷", "岁月神偷", "海阔天空", "小半",
        "海屿你", "绿色" # 请尽量再多加一些
        ]
    
    all_data = []
    for song in song_list:
        results = search_bilibili(song)
        if results:
            all_data.extend(results)
            print(f"成功获取 {len(results)} 条结果")
        
        # 保持间歇，保护IP
        time.sleep(3) 
        
    if all_data:
        df = pd.DataFrame(all_data)
        # 存储为 CSV，使用 utf-8-sig 确保 Excel 打开不乱码
        df.to_csv('training_data.csv', index=False, encoding='utf-8-sig')
        print(f"\n采集完成！共计 {len(all_data)} 条数据。请开始打分。")
    else:
        print("\n未采集到数据，请检查网络或是否需要配置 Cookie。")
