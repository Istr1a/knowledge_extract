# 文档知识提取工具

## 功能描述
识别 PDF 和 Word 文件，并从中提取知识生成问答对（QA对），最后保存为 Excel (.xlsx) 格式。

## 安装依赖
```bash
pip3 install -r requirements.txt
1.windows安装office软件
2.下载安装tesseract并将pytesseract.pytesseract.tesseract_cmd = r""替换为安装目录
3.llm.py中替换大模型api

运行：
python app.py
