from collections.abc import Generator
from typing import Any
import tempfile
import os

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from urllib.request import urlopen
import pypandoc

# 自动下载并安装 Pandoc（仅在首次运行时执行）
try:
    pypandoc.get_pandoc_version()
except OSError:
    pypandoc.download_pandoc()

class MarkdownDocTransformerTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # files = tool_parameters.get("files", [])
        markdown = tool_parameters.get("markdown", "")
        
        # Handle empty files array
        if not markdown:
            yield self.create_text_message("No markdown provided")
            yield self.create_json_message({
                "status": "error",
                "message": "No markdown provided",
                "results": []
            })
            return

        json_results = []

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix="docx") as temp_file:
                temp_file_path = temp_file.name
            try:
                pypandoc.convert_text(
                    markdown,                # 输入文本
                    to="docx",           # 输出格式
                    format="markdown",   # 输入文本的格式（Markdown）
                    outputfile=temp_file_path,  # 输出文件路径
                    encoding="utf-8"     # 编码
                )

                with open(temp_file_path, 'rb') as file_t:
                    docx_blob = file_t.read()
                
                # Create blob message for backward compatibility
                yield self.create_blob_message(
                    docx_blob,
                    meta={
                        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    },
                )
            finally:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

            yield self.create_text_message(markdown)
        except Exception as e:
                error_msg = f"Error processing markdown {markdown}: {str(e)}"
                yield self.create_text_message(text=error_msg)
                json_results.append({
                    "error": error_msg,
                    "status": "error"
                })
        # Create JSON response
        json_response = {
            "results": json_results
        }
        yield self.create_json_message(json_response)

