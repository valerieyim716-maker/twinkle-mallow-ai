import os
import re
import json
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai

# 加载本地 .env 文件
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val

load_env()

app = FastAPI(title="Twinkle Mallow AI CS Portal")

# 模拟数据库状态 (内存存储)
SESSIONS_DB = {}
FAQ_RULES = {
    "RULE_SHIPPING": "Oh, happy early birthday to your little one! 🎂 We usually pack and ship our sweet packages within 1 to 2 business days. Once it leaves our boutique, standard shipping takes about 3 to 5 business days to reach your porch. I'll send the tracking link to your inbox as soon as it's on the way, mama! ✨",
    "RULE_SIZE_CHART": "Oh, babies grow up way too fast, don't they? 🧸 Here is our size guide: Newborn is for 5-8 lbs, 0-3M is for 8-12 lbs, 3-6M is for 12-16 lbs, and 6-9M is for 16-20 lbs. For our cuddly, chubby little ones, I always recommend sizing up just to be safe and comfy, sweetie! 💕"
}

# 静态文件映射
os.makedirs("static", exist_ok=True)

class ChatPayload(BaseModel):
    message: str
    user_id: str
    gemini_key: str = ""
    feishu_webhook: str = ""

def classify_intent(text: str) -> str:
    """
    意图分类分流引擎 (规则优先，免 AI 费用)
    """
    text_lower = text.lower()
    # 1. 敏感词/退货退款/质量问题 -> 直接人工
    if re.search(r"(scam|sue|worst|broken|refund|manager|police|fake|garbage|terrible)", text_lower):
        return "ESCALATE"
    # 2. 运费物流查询 -> 规则回复
    if re.search(r"(shipping|track|delivery|status|where is my package|when will it ship)", text_lower):
        return "RULE_SHIPPING"
    # 3. 尺码表查询 -> 规则回复
    if re.search(r"(size chart|size guide|how big|what size|fitting)", text_lower):
        return "RULE_SIZE_CHART"
    
    # 4. 其他复杂或开放性咨询 -> AI 回复
    return "LLM_GENERATE"

def send_feishu_alert(webhook_url: str, user_id: str, reason: str, last_msg: str):
    """
    发送真实的飞书群组报警通知
    """
    if not webhook_url:
        return
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "⚠️ Twinkle Mallow AI 客服转接提醒",
                    "content": [
                        [
                            {"tag": "text", "text": "用户 ID: "},
                            {"tag": "text", "text": f"{user_id}\n"}
                        ],
                        [
                            {"tag": "text", "text": "转接原因: "},
                            {"tag": "text", "text": f"{reason}\n"}
                        ],
                        [
                            {"tag": "text", "text": "客户最后消息: "},
                            {"tag": "text", "text": f"\"{last_msg}\"\n"}
                        ],
                        [
                            {"tag": "text", "text": "状态: "},
                            {"tag": "text", "text": "🚨 AI已闭嘴，请人工客服速登后台处理！"}
                        ]
                    ]
                }
            }
        }
    }
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending Feishu alert: {e}")

def get_mock_ai_response(text: str) -> str:
    """
    当没有提供 Gemini Key 时，本地模拟 Sarah 的精品店语气回复
    """
    text_lower = text.lower()
    if "material" in text_lower or "fabric" in text_lower or "organic" in text_lower:
        return "Oh, congratulations on your sweet new bundle! 🍼 Yes, mama, we care so much about sensitive baby skin. All of our newborn collections are made from 100% certified organic bamboo and cotton. They are buttery-soft, hypoallergenic, and have tags on the outside so nothing scratches your sweet pea. You can dress your newborn with peace of mind! 🌸"
    if "gift" in text_lower or "present" in text_lower or "recommend" in text_lower:
        return "Oh, I'd love to help you find the perfect gift, darling! 🎁 For a sweet little one, our organic bamboo sleep sack or a cozy matching romper set are always huge hits! They come wrapped in our signature tissue paper with a little card. What age is the sweetie you're shopping for? ✨"
    
    # 默认兜底 mock
    return "Oh, hello sweetie! 🌸 I'm Sarah, the owner here at Twinkle Mallow. I want to make sure your little one has the absolute comfiest and cutest outfits. Tell me more about what you're looking for, mama, and I'll help you pick out the sweetest pieces! 💕"

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    user_id = payload.user_id
    message = payload.message
    gemini_key = payload.gemini_key or os.getenv("GEMINI_API_KEY", "")
    feishu_webhook = payload.feishu_webhook or os.getenv("FEISHU_WEBHOOK", "")

    # 初始化 Session
    if user_id not in SESSIONS_DB:
        SESSIONS_DB[user_id] = {
            "status": "active_ai",
            "history": []
        }
    
    session = SESSIONS_DB[user_id]
    
    # 如果已转接人工，AI 直接闭嘴
    if session["status"] == "escalated":
        return JSONResponse({
            "bot_reply": "[Silent] (Human customer service has taken over the chat. AI is silenced.)",
            "route_tag": "ESCALATED_SILENT",
            "token_count": 0,
            "cost": 0.0,
            "session_status": "escalated",
            "feishu_triggered": False
        })
    
    # 1. 意图分类
    route_tag = classify_intent(message)
    session["history"].append({"role": "user", "text": message})
    
    # 2. 根据分类处理
    feishu_triggered = False
    token_count = 0
    cost = 0.0
    
    if route_tag == "ESCALATE":
        # 转人工
        session["status"] = "escalated"
        bot_reply = "Oh, I am so sorry about that! Let me get my team to look into this for you right away. [ESC_REQ]"
        send_feishu_alert(feishu_webhook, user_id, "Triggered by negative keyword / complaint", message)
        feishu_triggered = True
        
    elif route_tag.startswith("RULE_"):
        # 规则引擎
        bot_reply = FAQ_RULES[route_tag]
        
    else:
        # LLM 大模型生成
        if gemini_key:
            try:
                # 配置并调用 Gemini API
                client = genai.Client(api_key=gemini_key)
                
                # 组装 Prompt
                system_prompt = (
                    "You are Sarah, the warm, loving, and helpful owner of 'Twinkle Mallow' — a cozy children's boutique clothing brand in the US. You are chatting with a customer on TikTok Shop.\n"
                    "CORE PERSONA & TONE GUIDELINES:\n"
                    "1. Tone: Speak like a sweet, close Southern mom/friend. Be warm, enthusiastic, and supportive.\n"
                    "2. Vocabulary: Regularly use sweet terms of endearment such as 'mama', 'sweetie', 'little one', 'sweet pea', 'darling'.\n"
                    "3. Emojis: Always use cute, warm emojis (🌸, 🧸, 👶, ✨, 🚚, 💕, 🎂) to show friendliness. Strictly limit to 1-2 emojis per response. Do not flood the message with emojis.\n"
                    "4. Length: Keep your responses short, sweet, and to the point (under 3 sentences where possible).\n"
                    "STRICT RULES:\n"
                    "1. NO BOT TALK: Never say 'As an AI...', 'I am a chatbot...', 'How can I assist you today?'.\n"
                    "2. TRUTH ONLY: If you don't know the shipping status or sizing, say: 'Oh dear, let me double check that with our warehouse team for you, mama! I'll get back to you here shortly.'\n"
                    "3. ESCALATION SIGNAL: If the customer is complaining, demands a refund, or seems angry, output the tag [ESC_REQ] at the end of your message.\n"
                )
                
                # 组装近期历史记录，限制在 3 轮
                history_text = ""
                for msg in session["history"][-6:-1]:
                    role_label = "Customer" if msg["role"] == "user" else "Sarah"
                    history_text += f"{role_label}: {msg['text']}\n"
                
                full_prompt = f"{system_prompt}\nChat History:\n{history_text}\nCustomer: {message}\nSarah:"
                
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=full_prompt
                )
                bot_reply = response.text.strip()
                
                # 计算 Token 消耗 (Flash 计费大约: Input $0.15/1M, Output $0.60/1M)
                # 使用字数近似估计 Token (1 word ≈ 1.3 tokens)
                input_tokens = int(len(full_prompt.split()) * 1.3)
                output_tokens = int(len(bot_reply.split()) * 1.3)
                token_count = input_tokens + output_tokens
                cost = (input_tokens * 0.00000015) + (output_tokens * 0.0000006)
                
                # 检查 AI 是否触发了转接
                if "[ESC_REQ]" in bot_reply:
                    session["status"] = "escalated"
                    send_feishu_alert(feishu_webhook, user_id, "AI generated Escalation tag [ESC_REQ]", message)
                    feishu_triggered = True
                    
            except Exception as e:
                bot_reply = f"Oh dear, I had a little hiccup wiggling my way here! 🥺 Let me double check with my team for you, mama! (Error: {str(e)})"
                session["status"] = "escalated"
                send_feishu_alert(feishu_webhook, user_id, f"Gemini API Error: {str(e)}", message)
                feishu_triggered = True
        else:
            # 走 Mock AI
            bot_reply = get_mock_ai_response(message)
            # 假装消耗了微量 Token
            token_count = 580
            cost = 0.00009
            
    # 保存历史回复
    session["history"].append({"role": "assistant", "text": bot_reply})
    
    return JSONResponse({
        "bot_reply": bot_reply.replace("[ESC_REQ]", "").strip(),
        "route_tag": route_tag,
        "token_count": token_count,
        "cost": float(f"{cost:.6f}"),
        "session_status": session["status"],
        "feishu_triggered": feishu_triggered
    })

@app.post("/api/reset")
async def reset_session(payload: dict):
    user_id = payload.get("user_id", "default_user")
    if user_id in SESSIONS_DB:
        SESSIONS_DB[user_id] = {
            "status": "active_ai",
            "history": []
        }
    return {"status": "reset", "user_id": user_id}

@app.get("/")
async def root():
    return HTMLResponse(content=open("static/index.html", "r").read(), status_code=200)
