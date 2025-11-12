#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import pandas as pd
from pathlib import Path
import pytesseract
from flask import Flask, request, render_template, send_file, jsonify, flash, redirect, url_for
import re
import unicodedata
from datetime import datetime
import zipfile
import io
from llm import llm_generator
import fitz
from typing import Dict
from PIL import Image
from docx2pdf import convert
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
pytesseract.pytesseract.tesseract_cmd = r""

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'docx', 'doc'}

# 确保文件夹存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_filename(filename):
    """安全处理文件名，保留中文字符但移除危险字符"""
    # 移除或替换危险字符，但保留中文字符
    # 移除路径分隔符和其他危险字符
    filename = re.sub(r'[<>:"/\|?*]', '', filename)
    # 移除控制字符
    filename = ''.join(char for char in filename if unicodedata.category(char)[0] != 'C')
    # 确保文件名不为空且不以点开头
    filename = filename.strip('. ')
    if not filename:
        filename = 'unnamed_file'
    return filename


def read_pdf(file_path: Path) -> Dict[int, str]:
    """读取PDF文件并提取文本和图片中的文本，按页组织"""
    page_contents = {}
    try:
        # 使用PyMuPDF (fitz) 打开PDF
        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = ""
            print(f"正在识别第{page_num+1}页")
            # 1. 提取原生文本
            page_text_content = page.get_text()
            if page_text_content:
                page_text += f"\n{page_text_content}\n"

            # 2. 提取并处理图片
            img_list = page.get_images(full=True)

            for img_index, img in enumerate(img_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]


                # 从字节流创建PIL图像
                try:
                    image = Image.open(io.BytesIO(image_bytes))

                    # 进行OCR识别
                    ocr_text = pytesseract.image_to_string(
                        image,
                        lang='chi_sim+eng'  # 支持中文和英文
                    )

                    # 如果识别到的文本不为空，则添加
                    if ocr_text.strip():
                        page_text += f"\n[图片内容] {ocr_text}\n"
                except Exception as e:
                    print(f"处理图片时出错：{e}")
            print(page_text)
            page_contents[page_num + 1] = page_text

        return page_contents

    except Exception as e:
        print(f"打开文件 {file_path} 时出错: {e}")

def get_qa_pairs(pdf_path, output_dir,original_name):
    text = read_pdf(pdf_path)
    qa_pairs = []
    for num_page, page_text in text.items():
        if page_text:
            print(f"正在解析第 {num_page} 页")
            result = llm_generator(page_text)
            # 防御式解析
            if not result or not result.strip():
                current_qa_pairs = []
            else:
                try:
                    current_qa_pairs = json.loads(result.strip())
                except json.JSONDecodeError:
                    current_qa_pairs = []
            qa_pairs.extend(current_qa_pairs or [])
    df = pd.DataFrame(qa_pairs)
    print(qa_pairs)
    df.to_excel(f"{output_dir}/{original_name}.xlsx", index=False)
    return True, f"成功输出QA对"

def read_word(word_path, output_dir):
    """将Word文件转换为Markdown（需要安装pandoc）"""
    # 获取原始文件名（不包含扩展名），保持原有的文件名格式
    word_name = os.path.splitext(os.path.basename(word_path))[0]
    markdown_path = os.path.join(output_dir, f"{word_name}.md")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    results = []
    output_files = []
    
    # 创建临时输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_output_dir = os.path.join(OUTPUT_FOLDER, timestamp)
    os.makedirs(temp_output_dir, exist_ok=True)
    
    for file in files:
        if file and allowed_file(file.filename):
            # 使用自定义的安全文件名函数，保留中文字符
            filename = safe_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # 根据文件类型进行转换
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            if file_ext == 'pdf':
                original_name = os.path.splitext(filename)[0]
                success, message = get_qa_pairs(file_path, temp_output_dir,original_name)
                if success:
                    # 使用原始文件名（不包含扩展名）
                    output_files.append(f"{original_name}.xlsx")


            elif file_ext in ['docx', 'doc']:
                original_name = os.path.splitext(filename)[0]
                convert(file_path,f'{UPLOAD_FOLDER}/{original_name}.pdf',keep_active=True)
                success, message = get_qa_pairs(f'{UPLOAD_FOLDER}/{original_name}.pdf', temp_output_dir, original_name)
                if success:
                    output_files.append(f"{original_name}.xlsx")
                    os.remove(f'{UPLOAD_FOLDER}/{original_name}.pdf')
            results.append({
                'filename': filename,
                'success': success,
                'message': message
            })
                        # 清理上传的文件
            os.remove(file_path)
    
    return jsonify({
        'success': True,
        'results': results,
        'output_dir': timestamp,
        'output_files': output_files
    })

@app.route('/download/<output_dir>')
def download_files(output_dir):
    """下载转换后的文件（打包为ZIP）"""
    output_path = os.path.join(OUTPUT_FOLDER, output_dir)
    
    if not os.path.exists(output_path):
        return "文件不存在", 404
    
    # 创建ZIP文件
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(output_path):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, output_path)
                zf.write(file_path, arc_name)
    
    memory_file.seek(0)
    
    return send_file(
        io.BytesIO(memory_file.read()),
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'converted_files_{output_dir}.zip'
    )

@app.route('/download_single/<output_dir>/<filename>')
def download_single_file(output_dir, filename):
    """下载单个转换后的文件"""
    file_path = os.path.join(OUTPUT_FOLDER, output_dir, filename)
    
    if not os.path.exists(file_path):
        return "文件不存在", 404
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
