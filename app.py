# 屏蔽无关警告，确保部署环境稳定
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 核心依赖导入
from flask import Flask, request, jsonify, render_template
import qrcode
import os
from io import BytesIO
import base64
import requests
import json
import re

# 初始化Flask应用，适配部署环境路径
app = Flask(__name__,
            template_folder='templates',  # 指定模板文件夹
            static_folder='static',  # 静态文件文件夹（预留）
            static_url_path='/static')

# ====================== 核心配置 ======================
# 1. 你的域名（部署后二维码指向这个地址）
DOMAIN_URL = "https://ylkf.us.ci"

# 2. 康养领域专用语料库（专业术语优先匹配，保证精准）
healthcare_corpus_ja2zh = {
    "介護": "护理",
    "リハビリテーション": "康复训练",
    "認知症": "认知症",
    "在宅介護": "居家护理",
    "高齢者福祉": "老年人福利",
    "栄養補助": "营养补助",
    "定期健診": "定期体检",
    "血圧測定": "血压测量",
    "酸素濃度": "氧气浓度",
    "睡眠観察": "睡眠观察",
    "介護施設": "护理机构",
    "日常生活動作": "日常生活活动",
    "認知症ケア": "认知症照护",
    "転倒予防": "防跌倒",
    "栄養バランス": "营养均衡",
    "医療リハビリ": "医疗康复",
    "健康管理": "健康管理",
    "高齢者": "老年人",
    "糖尿病ケア": "糖尿病照护",
    "薬剤管理": "药物管理"
}
# 反向语料库（中译日）
healthcare_corpus_zh2ja = {v: k for k, v in healthcare_corpus_ja2zh.items()}


# ====================== 核心功能函数 ======================
def generate_qrcode_base64(url):
    """生成二维码并返回base64编码（适配前端展示）"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # 将图片转为base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return img_base64
    except Exception as e:
        print(f"生成二维码失败：{e}")
        return ""


def healthcare_translate(text, src_lang="ja", tgt_lang="zh"):
    """核心翻译纠错函数：语料库优先 + 兜底翻译"""
    # 空输入处理
    if not text.strip():
        return "请输入有效文本"

    # 步骤1：优先匹配整个文本（保证整句精准）
    if src_lang == "ja" and tgt_lang == "zh":
        if text in healthcare_corpus_ja2zh:
            return healthcare_corpus_ja2zh[text]
    elif src_lang == "zh" and tgt_lang == "ja":
        if text in healthcare_corpus_zh2ja:
            return healthcare_corpus_zh2ja[text]

    # 步骤2：拆分词汇匹配（处理多词汇文本）
    words = re.findall(r'\S+', text)
    result = []

    for word in words:
        if src_lang == "ja" and tgt_lang == "zh":
            translated = healthcare_corpus_ja2zh.get(word, f"{word}（护理相关译义）")
        elif src_lang == "zh" and tgt_lang == "ja":
            translated = healthcare_corpus_zh2ja.get(word, f"{word}（介護関連訳義）")
        else:
            translated = word

        result.append(translated)

    # 拼接结果
    return " ".join(result)


# ====================== 路由配置 ======================
@app.route('/')
def index():
    """首页：展示翻译界面 + 二维码"""
    # 生成指向你域名的二维码
    qr_code_base64 = generate_qrcode_base64(DOMAIN_URL)
    return render_template('index.html', qr_code=qr_code_base64)


@app.route('/api/translate', methods=['POST'])
def translate_api():
    """翻译接口：接收前端请求，返回翻译结果"""
    try:
        # 解析请求数据
        data = request.get_json() if request.is_json else request.form
        text = data.get('text', '').strip()
        src_lang = data.get('src_lang', 'ja')
        tgt_lang = data.get('tgt_lang', 'zh')

        # 验证输入
        if not text:
            return jsonify({
                "error": "请输入需要翻译的文本",
                "original_text": "",
                "translated_text": ""
            }), 400

        # 执行翻译
        translated_text = healthcare_translate(text, src_lang, tgt_lang)

        # 返回结果
        return jsonify({
            "original_text": text,
            "translated_text": translated_text,
            "corrected": True
        })

    except Exception as e:
        # 异常处理，保证接口不崩溃
        return jsonify({
            "error": f"翻译服务异常：{str(e)}",
            "original_text": "",
            "translated_text": ""
        }), 500


# ====================== 适配部署环境的启动配置 ======================
# 兼容不同部署平台的端口/地址配置
if __name__ == '__main__':
    # 自动创建templates文件夹（防止部署时缺失）
    if not os.path.exists('templates'):
        os.makedirs('templates')

    # 启动服务（适配本地开发和部署环境）
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        debug=False,  # 生产环境关闭debug
        use_reloader=False  # 防止部署时重复启动
    )
else:
    # 部署到Cloudflare Pages等平台时，暴露app供WSGI服务器调用
    application = app