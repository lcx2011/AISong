# step2_train.py
import pandas as pd
import jieba
import joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
# -*- coding: utf-8 -*-
import sys
import io

# 设置标准输出为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# 1. 自定义分词函数，告诉 AI 怎么理解中文
def jieba_tokenize(text):
    return jieba.lcut(text)

def train_model():
    print("正在加载数据集...")
    # 读取你打好标签的数据
    df = pd.read_csv('training_data.csv', encoding='utf-8-sig')
    
    # 清理掉你忘了打分的数据
    df = df.dropna(subset=['score'])
    df['score'] = df['score'].astype(int)
    
    # 特征工程：把标题和UP主拼到一起，让AI一起阅读
    df['text_feature'] = df['title'] + " " + df['author']
    
    # 定义 X (特征) 和 y (答案)
    X = df[['text_feature', 'duration', 'play']]
    y = df['score']
    
    print(f"有效训练数据共 {len(df)} 条。开始构建模型...")
    
    # 2. 构建数据处理流水线
    # 文本特征走 TF-IDF 处理，数字特征走标准化缩放
    preprocessor = ColumnTransformer(
        transformers=[
            ('text', TfidfVectorizer(tokenizer=jieba_tokenize), 'text_feature'),
            ('num', StandardScaler(), ['duration', 'play'])
        ])
    
    # 3. 组合预处理器和随机森林分类器
    # 16G内存的电脑，你可以把 n_estimators(树的数量) 设到 200，能力更强
    clf = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced'))
    ])
    
    # 4. 训练模型
    print("AI 正在学习你的偏好，请稍候...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)
    clf.fit(X_train, y_train)
    
    # 评估准确率
    score = clf.score(X_test, y_test)
    print(f"模型训练完成！测试集准确率: {score * 100:.2f}%")
    
    # 5. 保存整个流水线
    joblib.dump(clf, 'music_model.pkl')
    print("模型已保存为 music_model.pkl ！（只有几MB，随便复制到Win7去用）")

if __name__ == "__main__":
    train_model()
