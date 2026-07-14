"""
LLM大模型问答模块
支持OpenAI兼容API和本地fallback回答
"""
import requests
import json
from config import Config


class LLMService:
    """大模型服务"""

    def __init__(self):
        self.api_url = Config.LLM_API_URL
        self.api_key = Config.LLM_API_KEY
        self.model = Config.LLM_MODEL

    def chat(self, question, context=None, history=None):
        """
        发送对话请求到LLM
        Args:
            question: 用户问题
            context: 上下文信息
            history: 历史对话记录 [{"role":"user","content":"..."}, ...]
        Returns:
            answer: 回答文本
        """
        messages = self._build_messages(question, context, history)

        # 尝试调用远程API
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 1500,
                    "temperature": 0.7,
                    "stream": False
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                answer = data['choices'][0]['message']['content']
                return answer
            else:
                print(f"[LLM] API返回错误: {response.status_code}")
        except requests.exceptions.Timeout:
            print("[LLM] API请求超时，使用本地回答")
        except requests.exceptions.ConnectionError:
            print("[LLM] 无法连接到LLM API，使用本地回答")
        except Exception as e:
            print(f"[LLM] 调用异常: {e}")

        # Fallback: 本地规则回答
        return self._local_answer(question, context, history)

    def _build_messages(self, question, context, history):
        """构建消息列表"""
        system_prompt = """你是一个专业的网络舆情分析助手，具备以下能力：
1. 分析网络舆情事件的发展趋势和传播规律
2. 解读公众情感倾向和舆论走向
3. 评估舆情事件的风险等级和影响范围
4. 提供专业的舆情应对建议

请基于提供的事件信息，给出专业、客观、简洁的中文回答。
如果信息不足以回答，请说明需要更多哪些信息。"""

        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        if history:
            for msg in history[-6:]:  # 最近3轮
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # 添加上下文
        user_message = ""
        if context:
            user_message += f"【事件背景】\n{context}\n\n"
        user_message += f"【用户问题】\n{question}"
        messages.append({"role": "user", "content": user_message})

        return messages

    def _local_answer(self, question, context, history):
        """本地智能回答（LLM不可用时的fallback）"""
        q = question.lower()

        # 基于规则的回答策略
        if any(w in q for w in ['情感', '情绪', '态度', '看法', '评价', '好评', '差评']):
            return self._sentiment_answer(context)
        elif any(w in q for w in ['趋势', '发展', '预测', '走向', '未来', '后续']):
            return self._trend_answer(context)
        elif any(w in q for w in ['风险', '危害', '影响', '后果', '严重']):
            return self._risk_answer(context)
        elif any(w in q for w in ['原因', '起因', '为什么', '为何', '根源']):
            return self._cause_answer(context)
        elif any(w in q for w in ['传播', '路径', '溯源', '来源', '首发']):
            return self._propagation_answer(context)
        elif any(w in q for w in ['总结', '概括', '概要', '简述', '概述']):
            return self._summary_answer(context)
        elif any(w in q for w in ['建议', '应对', '策略', '措施', '怎么办']):
            return self._advice_answer(context)
        elif any(w in q for w in ['真假', '虚假', '谣言', '真实', '可信']):
            return self._authenticity_answer(context)
        else:
            return self._general_answer(question, context)

    def _sentiment_answer(self, context):
        sentiment_info = self._extract_from_context(context, ['正面', '负面', '中性'])
        return f"""【情感倾向分析】

根据当前舆情数据，公众对该事件的情感态度分布如下：
{sentiment_info}

分析要点：
1. 情感分布反映了公众对该事件的核心态度
2. 需要重点关注占比最高的情感倾向背后的诉求
3. 建议持续监测情感变化趋势，特别关注极端情绪

如需了解情感趋势的时间变化，可以进一步查询趋势数据。"""

    def _trend_answer(self, context):
        lifecycle = self._extract_from_context(context, ['生命周期', '阶段'])
        return f"""【发展趋势分析】

{lifecycle_info}

事件发展趋势分析：
1. 事件热度随时间的变化呈现明显的阶段性特征
2. 当前阶段的关键是把握舆论走向，做好引导工作
3. 根据传播规律，事件可能在未来1-3天内出现新的变化

建议密切关注报道量的变化，及时调整应对策略。"""

    def _risk_answer(self, context):
        risk = self._extract_from_context(context, ['风险等级', '风险'])
        return f"""【风险评估】

{risk}

风险分析维度：
1. **传播风险**：事件在多平台的扩散程度
2. **情绪风险**：负面情绪的集中度和烈度
3. **升级风险**：是否可能引发次生舆情
4. **公信力风险**：对相关机构/企业的影响程度

建议：根据风险等级制定分级应对方案，重点防范情绪升级和谣言扩散。"""

    def _cause_answer(self, context):
        cause = self._extract_from_context(context, ['起因', '原因'])
        return f"""【原因分析】

{cause}

事件发生的深层因素：
1. **直接原因**：事件发生的直接触发点
2. **社会背景**：当前社会环境中的相关因素
3. **传播因素**：媒体报道和社交传播的放大效应
4. **利益关系**：涉及各方的利益诉求和博弈

理解事件的深层原因有助于找到问题的根本解决之道。"""

    def _propagation_answer(self, context):
        return """【传播路径分析】

事件的传播过程分析：
1. **首发阶段**：信息最初由某个具体来源发布
2. **扩散阶段**：经过社交平台转发和信息裂变
3. **爆发阶段**：主流媒体跟进，进入大众视野
4. **持续阶段**：保持一定热度，出现衍生话题

关键传播节点：
- 初始来源：事件信息的首发渠道
- 关键转发：影响力较大的传播者介入
- 官方介入：权威机构或媒体的参与

建议关注传播路径中的关键节点，合理引导信息流向。"""

    def _summary_answer(self, context):
        return f"""【事件概要】

{context}

以上是该事件的核心信息。总结要点：
1. 事件基本情况已基本明确
2. 舆情反应呈现多元化特征
3. 需要持续关注事件后续发展

如需了解更详细的某个方面，请具体提问。"""

    def _advice_answer(self, context):
        risk = self._extract_from_context(context, ['风险等级'])
        return f"""【应对建议】

基于当前舆情态势，建议采取以下措施：

1. **信息发布**：
   - 及时发布权威信息，抢占舆论主导权
   - 保持信息透明，避免信息真空

2. **舆论引导**：
   - 邀请权威专家进行理性分析
   - 发挥主流媒体的引导作用

3. **情绪疏导**：
   - 积极回应公众关切
   - 妥善处理极端情绪

4. **风险防控**：
   - 加强谣言监测和辟谣力度
   - 制定舆情升级应对预案

建议相关部门尽快研判，形成统一口径和应对方案。"""

    def _authenticity_answer(self, context):
        return """【真实性评估】

关于信息真实性的判断：
1. 建议以官方机构的权威发布为准
2. 对来源不明的信息保持警惕
3. 交叉验证多个信息源的报道
4. 关注发布方的可信度和历史记录

系统已对相关信息进行了真实性初筛，展示了置信度评分。
但最终判断仍然需要人工复核和专业机构的鉴定。"""

    def _general_answer(self, question, context):
        return f"""感谢您的提问。关于「{question}」，基于现有舆情数据，我的分析如下：

{context}

综合分析：
• 该事件在舆情场中的表现符合相关传播规律
• 建议从多个维度持续关注事件发展
• 如需更深层次分析，可以提出更具体的问题

如果您有关于情感分析、趋势预测、风险评估等方面的具体问题，
我可以提供更有针对性的分析。"""

    def _extract_from_context(self, context, fields):
        """从上下文中提取特定字段"""
        if not context:
            return "暂无相关数据"

        lines = []
        for line in context.split('\n'):
            for field in fields:
                if field in line:
                    lines.append(line.strip())

        return '\n'.join(lines) if lines else "请参考事件详情中的相关数据"


# 单例
llm_service = LLMService()
