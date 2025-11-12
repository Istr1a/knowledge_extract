from openai import OpenAI
def llm_generator(text:str):
    client = OpenAI(
        base_url='',
        api_key='', # ModelScope Token
    )

    completion = client.chat.completions.create(
        model = "",
        messages = [
            {"role": "system","content": "Y你是一名销售文件整理员，需要从文本中提取产品的知识信息用于推销，必须使用列表格式回答."},
            {"role": "user", "content": f"""从以下文本中生成尽可能多个高质量的产品信息问答对。
                文本内容：
                {text}
                
                要求：
                1. 答案应完整且基于文本内容准确无误
                2. 避免是/否（Yes/No）类型的问题
                3. 问题应具体且清晰
                4. 确保答案能够在文本中找到
                5. 不要进行推测或编造信息
                6.已有的问题答案对可以直接摘抄
                7.问题涉及具体产品的给出具体产品名字，不要用“这款产品”、“产品”等代词
                8.信息包含多个步骤时生成的问题不要拆开
                
                请将结果以列表形式返回，每个元素包含 “query” 和 “answer” 两个字段。              
                示例格式：
                [
                    {{"query": "……的主要目的是什么？", "answer": "主要目的是……"}},
                    {{"query": "……是如何运作的？", "answer": "它通过……实现。"}}
                ]
                """}
                ],
        temperature = 0.0,
        extra_body={"enable_thinking": False}

    )
    print(completion.choices[0].message.content)
    return completion.choices[0].message.content