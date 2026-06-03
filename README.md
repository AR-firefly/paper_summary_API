# PDF 论文自动提取与结构化输出工具

基于大模型 API 从 PDF 论文中自动提取元数据、关键指标，并生成结构化摘要。

## 功能

- PDF 文本提取（自动读取 PDF 文件内容）
- 大模型结构化分析：元数据提取、关键指标抽取、内容总结
- 批量处理：多篇 PDF 自动排队，支持已处理文件追踪（避免重复）
- 自定义 prompt：复制 `api/prompt.py` 可定制分析模板

## 使用前提

1. 申请 DeepSeek API Key（或兼容的 OpenAI 接口）
2. 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1. 在 `api/代码逻辑.py` 配置区填入 API Key 和 PDF 文件夹路径
2. 运行：

```bash
python api/代码逻辑.py
```

3. 每篇 PDF 的总结自动保存在 `summaries/` 子文件夹中

## 自定义 prompt

工具内置通用 prompt，若需自定义分析模板：

```bash
# 创建自定义 prompt（可选）
cp api/prompt.py api/prompt.py  # 或手动创建
```

编辑 `api/prompt.py` 中的 `PROMPT_TEMPLATE` 变量，格式参照内置模板。

## 依赖

- PyPDF2：PDF 文本提取
- openai：大模型 API 调用
