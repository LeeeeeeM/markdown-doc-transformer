from collections.abc import Generator
from typing import Any
import tempfile
import os
import re
import hashlib
import shutil

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from urllib.request import urlopen
import pypandoc

# 自动下载并安装 Pandoc（仅在首次运行时执行）
try:
    pypandoc.get_pandoc_version()
except OSError:
    pypandoc.download_pandoc()

# 生成图片并替换 Markdown 内容的辅助函数
def generate_and_replace(file_api, echarts_json, temp_images_dir, image_width, image_height):
    # 根据 echarts_json 的 md5 生成图片文件名
    md5 = hashlib.md5(echarts_json.encode('utf-8')).hexdigest()
    image_name = f'image_{md5}.png'
    image_path = os.path.join(temp_images_dir, image_name)
    generate_chart(file_api, echarts_json, image_path, image_width, image_height)
    # 使用绝对路径确保 Pandoc 可以找到图片
    abs_image_path = os.path.abspath(image_path)
    return f'![]({abs_image_path})'

# 一次性替换整个 Markdown 来提高效率
def optimize_markdown(markdown, file_api, temp_images_dir, image_width, image_height):
    # 使用更灵活的正则表达式来匹配不同格式的特定字符串
    markdown = re.sub(
        r'```\s*echarts\s+(.*?)```',
        lambda match: generate_and_replace(file_api, match.group(1).strip(), temp_images_dir, image_width, image_height), 
        markdown, 
        flags=re.DOTALL
    )
    return markdown

def generate_chart(api_url, json_str, image_path, width, height):
    """
    生成echarts图表并保存为图片。
    """
    import requests
    import json
    
    # 先移除转义字符
    json_str = json_str.strip()

    headers = {"Content-Type": "application/json"}
    data = {
        "width": width,
        "height": height,
        "echartOption": json_str  # 使用解析后的JSON对象
    }
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    response.raise_for_status()  # 检查请求是否成功
    
    # 直接获取二进制响应内容
    image_data = response.content
    
    # 确保临时图片文件夹存在
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
    # 保存图片到临时文件夹
    with open(image_path, "wb") as f:
        f.write(image_data)
    return image_path

class MarkdownDocTransformerTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        markdown = tool_parameters.get("markdown", "")
        file_api = tool_parameters.get("file_api", "")
        image_width = tool_parameters.get("image_width") or 800
        image_height = tool_parameters.get("image_height") or 500
        reference_docx = tool_parameters.get("reference_docx", "") or None
        
        # Handle empty files array
        if not markdown:
            yield self.create_text_message("No markdown provided")
            yield self.create_json_message({
                "status": "error",
                "message": "No markdown provided",
                "results": []
            })
            return
        
        # 创建随机临时文件夹来存储图片
        temp_images_dir = tempfile.mkdtemp()
        
        markdown = optimize_markdown(markdown, file_api, temp_images_dir, image_width, image_height)

        json_results = []

        try:
            # 创建临时文件夹来存储生成的 DOCX 文件和图片
            temp_dir = tempfile.mkdtemp()
            docx_file_name = "output.docx"
            docx_file_path = os.path.join(temp_dir, docx_file_name)
            
            temp_ref_file_path = None
            if reference_docx:
                temp_ref_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=temp_dir)
                temp_ref_file.write(urlopen(reference_docx.url).read())
                temp_ref_file_path = temp_ref_file.name
                temp_ref_file.close()  # 立即关闭文件，以便后续使用文件路径

            try:
                # 转换 Markdown 到 DOCX
                pypandoc.convert_text(
                    markdown,                # 输入文本
                    to="docx",               # 输出格式
                    format="markdown",       # 输入文本的格式（Markdown）
                    outputfile=docx_file_path,  # 输出文件路径
                    extra_args=[f'--reference-doc={temp_ref_file_path}'] if temp_ref_file_path else [],
                    encoding="utf-8"         # 编码
                )

                # 读取生成的 DOCX 文件
                with open(docx_file_path, 'rb') as file_t:
                    docx_blob = file_t.read()
                
                # Create blob message for backward compatibility
                yield self.create_blob_message(
                    docx_blob,
                    meta={
                        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    },
                )
            finally:
                # 删除临时文件
                if temp_ref_file_path and os.path.exists(temp_ref_file_path):
                    os.unlink(temp_ref_file_path)

            yield self.create_text_message(markdown)
        except Exception as e:
            error_msg = f"Error processing markdown: {str(e)}"
            yield self.create_text_message(text=error_msg)
            json_results.append({
                "error": error_msg,
                "status": "error"
            })
        finally:
            # 删除临时图片文件夹及其内容
            if os.path.exists(temp_images_dir):
                shutil.rmtree(temp_images_dir)
            # 删除 DOCX 临时文件夹及其内容
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        # Create JSON response
        json_response = {
            "results": json_results
        }
        yield self.create_json_message(json_response)