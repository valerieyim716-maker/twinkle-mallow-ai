# 🧸 Twinkle Mallow AI 客服系统测试与落地指南

这是一个专为 **Twinkle Mallow** 打造的 AI 客服体验中心。我们通过一个**前端交互沙盒（Playground）** + **FastAPI 后端服务**，完全还原并模拟了 TikTok 实时聊天、智能分流、AI 温暖回复和飞书警报的真实运行过程。

---

## 1. 快速启动与体验 (Quick Start)

### 步骤 1：安装依赖包
打开电脑的终端（Terminal），进入当前项目目录，运行以下命令安装 Python 依赖：
```bash
pip install -r requirements.txt
```

### 步骤 2：启动本地服务
运行以下命令启动服务：
```bash
python3 -m uvicorn app:app --reload
```

### 步骤 3：在浏览器中游玩
打开浏览器，访问以下地址：
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 2. 交互测试推荐（自问自答游玩指南）

你可以直接在网页左侧的“手机模拟器”输入框中，发送以下几类消息，观察中间的**“决策大脑”**和右侧的**“飞书警报”**：

1.  **触发规则回复 (0 Token 成本)**：
    *   发送：`When will my order ship?` 或 `Where is my package?`
    *   *AI 大脑反馈*：识别意图为 `RULE_SHIPPING`，自动加载发货政策模板，本次调用 Token 数为 **0**，费用为 **$0.000000**。
2.  **触发 AI 个性化回复**：
    *   发送：`Are your rompers soft for newborns?` 或 `I need a gift recommendation for a 1-year-old girl.`
    *   *AI 大脑反馈*：识别意图为 `LLM_GENERATE`。
    *   *注*：若你在底部填入了 `Gemini API Key`，它会实时调用真实大模型以 **Sarah 店主的口吻**回复你；如果不填，系统会使用预设的 Sarah 语料库进行高仿真模拟。
3.  **触发人工客服接管与飞书报警**：
    *   发送：`This is a scam, I want my money back!` 或 `The snap on my romper is broken!`
    *   *AI 大脑反馈*：识别意图为 `ESCALATE` (高危词/质量问题触发) 或大模型输出带 `[ESC_REQ]`。
    *   *飞书反馈*：系统自动将该用户状态改为 `"escalated"` (人工已接管)，AI 自动闭嘴。同时右侧的“飞书警报器”会弹出红色警报卡片。如果你在底部配置了**真实的飞书 Webhook 链接**，你的手机飞书上会收到真实的卡片消息推送！

---

## 3. 睡醒之后，你需要做什么（落地生产的准备）

要将这套系统真正接入你的 **TikTok Shop** 店铺并让所有顾客用上，开发人员需要完成以下准备：

1.  **注册 TikTok 开发者账号 (TikTok Shop Developer)**：
    *   登录 [TikTok Shop Partner Platform](https://partner.tiktokshop.com/)。
    *   创建 App 并获取 `App Key` 和 `App Secret`，用于通过 API 发送和接收消息。
2.  **飞书机器人 Webhook 配置**：
    *   在飞书群组里：点击群设置 -> 机器人 -> 添加机器人 -> 自定义机器人。
    *   复制机器人提供的 `Webhook 地址`，把它配入我们系统的环境变量中。
3.  **部署到云端服务器**：
    *   因为 TikTok 的 Webhook 要求接收端必须支持 **HTTPS 安全协议**，你需要将此项目部署到支持 HTTPS 的云服务上（如 Vercel, Render 或 AWS）。
    *   部署后，将 TikTok Shop 后台的消息通知地址（Webhook URL）指向你的域名即可（例如 `https://your-domain.com/api/chat`）。
