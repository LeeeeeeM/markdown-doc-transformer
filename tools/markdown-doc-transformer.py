from collections.abc import Generator
from typing import Any
import tempfile
import os

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

# from markitdown import MarkItDown
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

        return

        # Process each file
        for file in files:
            try:
                file_extension = file.extension if file.extension else '.tmp'

                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    blob = urlopen(file.url).read()
                    temp_file.write(blob)
                    temp_file_path = temp_file.name
                
                try:
                    md = MarkItDown()
                    result = md.convert(temp_file_path)
                    print(f"{result}")

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
                    
                    if result and hasattr(result, 'text_content'):
                        results.append({
                            "filename": file.filename,
                            "content": result.text_content
                        })
                        
                        # Add to JSON results
                        json_results.append({
                            "filename": file.filename,
                            "original_format": file_extension.lstrip('.'),
                            "markdown_content": result.text_content,
                            "status": "success"
                        })
                    else:
                        error_msg = f"Conversion failed for file {file.filename}. Result: {result}"
                        yield self.create_text_message(text=error_msg)
                        json_results.append({
                            "filename": file.filename,
                            "original_format": file_extension.lstrip('.'),
                            "error": error_msg,
                            "status": "error"
                        })
                        
                finally:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        
            except Exception as e:
                error_msg = f"Error processing file {file.filename}: {str(e)}"
                yield self.create_text_message(text=error_msg)
                json_results.append({
                    "filename": file.filename,
                    "original_format": file_extension.lstrip('.'),
                    "error": error_msg,
                    "status": "error"
                })
        
        # Create JSON response
        json_response = {
            "status": "success" if len(results) > 0 else "error",
            "total_files": len(files),
            "successful_conversions": len(results),
            "results": json_results
        }
        yield self.create_json_message(json_response)
        
        # Return text results based on number of files processed (for backward compatibility)
        if len(results) == 0:
            yield self.create_text_message("No files were successfully processed")
        elif len(results) == 1:
            yield self.create_text_message(results[0]["content"])
        else:
            combined_content = ""
            for idx, result in enumerate(results, 1):
                combined_content += f"\n{'='*50}\n"
                combined_content += f"File {idx}: {result['filename']}\n"
                combined_content += f"{'='*50}\n\n"
                combined_content += result['content']
                combined_content += "\n\n"
            
            yield self.create_text_message(combined_content.strip())

