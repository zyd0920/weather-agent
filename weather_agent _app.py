import json
import requests
from zhipuai import ZhipuAI
import streamlit as st

# ===== 从Streamlit的Secrets读取API密钥 =====
API_KEY = st.secrets["ZHIPUAI_API_KEY"]

# ===== 1. 定义工具 =====
def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=%C+%t&lang=zh"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            weather_text = response.text.strip()
            return f"{city}天气：{weather_text}"
        else:
            return f"查询{city}天气失败"
    except Exception as e:
        return f"查询{city}天气失败，错误：{str(e)}"

# ===== 2. 工具说明书 =====
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息，包括天气状况、温度、湿度等。当用户询问天气时，必须使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、三门峡"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ===== 3. 创建客户端 =====
client = ZhipuAI(api_key=API_KEY)

# ===== 4. Streamlit界面 =====
st.set_page_config(page_title="天气智能助手", page_icon="🌤️")
st.title("🌤️ 智能天气问答Agent")

# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 输入框
if prompt := st.chat_input("请问你想查询哪个城市的天气？"):
    # 显示用户消息
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用Agent
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            # 第一步：AI判断要不要调用工具
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice="auto"
            )
            
            # 检查是否调用工具
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # 执行工具
                result = ""
                if function_name == "get_weather":
                    result = get_weather(arguments["city"])
                
                # 把工具结果给AI
                messages = [
                    {"role": "user", "content": prompt},
                    response.choices[0].message.model_dump(),
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    }
                ]
                
                second_response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=messages
                )
                
                answer = second_response.choices[0].message.content
            else:
                answer = response.choices[0].message.content
            
            st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})