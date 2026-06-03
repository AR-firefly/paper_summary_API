import os
import PyPDF2
from openai import OpenAI
import time
import re

# ==================== 配置区 ====================
DEEPSEEK_API_KEY = ""  # 你的Key
PDF_FOLDER = r"D:\学习\节能减排比赛论文\deepseek自动总结PDF"  # PDF 存放路径
SLEEP_SECONDS = 2  # 每篇间隔秒数
# ===============================================

# 子文件夹：存放所有总结文件
SUMMARY_SUBFOLDER = "summaries"
SUMMARY_PATH = os.path.join(PDF_FOLDER, SUMMARY_SUBFOLDER)

# 记录已处理PDF的文件
PROCESSED_LOG = os.path.join(PDF_FOLDER, "processed_pdfs.txt")

# 确保子文件夹存在
os.makedirs(SUMMARY_PATH, exist_ok=True)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")


def load_processed_pdfs():
    """读取已处理的PDF文件名列表"""
    if not os.path.exists(PROCESSED_LOG):
        return []
    with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def save_processed_pdf(filename):
    """将新处理的PDF文件名追加到记录中"""
    print(f"  记录已处理：{filename}")  # 加这一行
    with open(PROCESSED_LOG, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')


def extract_text_from_pdf(pdf_path):
    """从PDF文件中提取文字（只取前15页）"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(min(15, len(reader.pages))):
                page_text = reader.pages[page_num].extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        print(f"  提取失败：{e}")
        return ""


def generate_summary(title, full_text):
    """调用DeepSeek，基于全文生成结构化总结，并提取论文元数据"""
    try:
        from prompt import PROMPT_TEMPLATE
    except ImportError:
        PROMPT_TEMPLATE = """你是一个科研论文分析助手。请基于以下论文全文，完成以下任务：

【任务一：提取元数据】作者、发表年份、期刊名称、论文标题、DOI（如果有）
【任务二：提取关键指标】核心参数、实验数据、方法类型、性能指标等
【任务三：评估相关度】高/中/低，并说明理由
【任务四：内容总结】用中文总结核心研究问题、主要方法、关键发现、主要结论（每部分200-300字）
【任务五：生成数据摘要表】将提取的数据整理为表格格式

论文标题：{title}
全文内容（节选）：{full_text}"""

    if len(full_text) > 15000:
        full_text = full_text[:15000]

    prompt = PROMPT_TEMPLATE

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个严谨的科研助手，严格根据给定文本提取和总结，绝不编造。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=6000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  API调用出错：{e}")
        return "生成失败"


def parse_metadata(summary_text):
    """从总结文本中提取作者、年份、期刊、标题"""
    metadata = {}
    patterns = {
        'authors': r'作者[：:]\s*(.+)',
        'year': r'年份[：:]\s*(.+)',
        'journal': r'期刊[：:]\s*(.+)',
        'title': r'标题[：:]\s*(.+)'
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, summary_text, re.MULTILINE)
        metadata[key] = match.group(1).strip() if match else ''
    return metadata


def safe_filename(s, max_len=200):
    """替换非法字符，截断过长字符串"""
    illegal_chars = r'[\\/*?:"<>|]'
    s = re.sub(illegal_chars, '_', s)
    s = s.strip().replace(' ', '_')
    if len(s) > max_len:
        s = s[:max_len]
    return s


def build_filename_from_metadata(metadata):
    """根据元数据构造安全的文件名（支持中文），优先完整信息，过长则简化"""
    authors_raw = metadata.get('authors', '未知作者')
    year_raw = metadata.get('year', '无年份')
    journal_raw = metadata.get('journal', '无期刊')
    title_raw = metadata.get('title', '无标题')

    def clean_field(s):
        illegal_chars = r'[\\/*?:"<>|]'
        s = re.sub(illegal_chars, '_', s)
        s = s.strip().replace(' ', '_')
        return s

    authors = clean_field(authors_raw)
    year = clean_field(year_raw)
    journal = clean_field(journal_raw)
    title = clean_field(title_raw)

    MAX_LEN = 200

    # 尝试完整文件名
    filename = f"{authors}_{year}_{journal}_{title}.txt"
    if len(filename) <= MAX_LEN:
        return filename

    # 如果太长，逐步简化
    author_list = authors_raw.split('、') if '、' in authors_raw else authors_raw.split(',')
    if len(author_list) > 3:
        simplified_authors = '、'.join([a.strip() for a in author_list[:3]]) + '等'
        authors = clean_field(simplified_authors)
        filename = f"{authors}_{year}_{journal}_{title}.txt"
        if len(filename) <= MAX_LEN:
            return filename

    if len(author_list) > 0:
        first_author = author_list[0].strip() + '等'
        authors = clean_field(first_author)
        filename = f"{authors}_{year}_{journal}_{title}.txt"
        if len(filename) <= MAX_LEN:
            return filename

    title_short = title_raw[:30] + '...'
    title = clean_field(title_short)
    filename = f"{authors}_{year}_{journal}_{title}.txt"
    if len(filename) <= MAX_LEN:
        return filename

    filename = f"{authors}_{year}_{journal}.txt"
    if len(filename) <= MAX_LEN:
        return filename

    return filename[:MAX_LEN - 4] + '.txt'


def main():
    # 加载已处理的PDF列表
    processed = load_processed_pdfs()
    print(f"已处理过的PDF数量：{len(processed)}")

    # 获取所有PDF文件
    all_pdfs = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    # 过滤出未处理的PDF
    to_process = [f for f in all_pdfs if f not in processed]
    print(f"待处理PDF数量：{len(to_process)}")

    if not to_process:
        print("🎉 所有PDF都已处理过，无需操作。")
        return

    print(f"开始处理 {len(to_process)} 篇新论文...\n")

    for idx, filename in enumerate(to_process, 1):
        pdf_path = os.path.join(PDF_FOLDER, filename)
        print(f"[{idx}/{len(to_process)}] 正在处理：{filename}")

        # 提取全文
        full_text = extract_text_from_pdf(pdf_path)
        if not full_text:
            print("  ⚠️ 全文提取失败，跳过")
            # 即使失败也标记为已处理？不，应该保留以便后续重试
            continue

        # 生成总结
        summary = generate_summary(filename, full_text)
        if summary == "生成失败":
            continue

        # 解析元数据并构建新文件名
        metadata = parse_metadata(summary)
        if all(metadata.values()):
            new_filename = build_filename_from_metadata(metadata)
            txt_path = os.path.join(SUMMARY_PATH, new_filename)  # 保存到子文件夹
            # 避免重名
            if os.path.exists(txt_path):
                base, ext = os.path.splitext(new_filename)
                counter = 1
                while os.path.exists(os.path.join(SUMMARY_PATH, f"{base}_{counter}{ext}")):
                    counter += 1
                txt_path = os.path.join(SUMMARY_PATH, f"{base}_{counter}{ext}")
        else:
            # 回退方案：使用原PDF名 + "_总结"
            base_name = os.path.splitext(filename)[0]
            txt_filename = base_name + "_总结.txt"
            txt_path = os.path.join(SUMMARY_PATH, txt_filename)
            print(f"  ⚠️ 元数据提取不完整，使用默认文件名：{txt_filename}")

        # 保存总结文件
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(summary)

        # 标记为已处理
        save_processed_pdf(filename)

        print(f"  ✅ 总结已保存至：{os.path.basename(txt_path)} (位于 {SUMMARY_SUBFOLDER} 文件夹)")
        print(f"  休息 {SLEEP_SECONDS} 秒...\n")
        time.sleep(SLEEP_SECONDS)

    print("🎉 全部新论文处理完成！")


if __name__ == "__main__":
    main()