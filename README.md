识别PDF和Word文件并提取知识生成QA对，保存为xlsx

pip3 install -r requirements.txt
1.windows安装office软件
2.下载安装tesseract并将pytesseract.pytesseract.tesseract_cmd = r""替换为安装目录
3.llm.py中替换大模型api

运行：
python app.py
