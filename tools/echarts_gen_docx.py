from collections.abc import Generator
from typing import Any
import os

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

import requests
import json

class EchartsGenDocx(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        file_api = tool_parameters.get("file_api", "")

        images = tool_parameters.get("images", "[]")

        func = tool_parameters.get("func", "")
        
        # Handle empty files array
        if not file_api:
            yield self.create_text_message("No file_api provided")
            yield self.create_json_message({
                "status": "error",
                "message": "No file_api provided",
                "results": []
            })
            return
        
        if not images:
            yield self.create_text_message("No images provided")
            yield self.create_json_message({
                "status": "error",
                "message": "No images provided",
                "results": []
            })
            return
        
        if not func:
            yield self.create_text_message("No func provided")
            yield self.create_json_message({
                "status": "error",
                "message": "No func provided",
                "results": []
            })
            return

        try:

          headers = {"Content-Type": "application/json"}
          data = {
              "images": images,
              "func": func,
          }
          response = requests.post(file_api, headers=headers, data=json.dumps(data))
          if response.status_code != 200:
            raise Exception(f"Server error {response.reason}")
          
          # 直接获取二进制响应内容
          image_data = response.content

          yield self.create_blob_message(
              image_data,
              meta={
                  "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
              },
          )
        except Exception as e:
          error_msg = f"Error processing file : {str(e)}"
          yield self.create_text_message(text=error_msg)
          yield self.create_json_message({
              "status": "文档生成失败",
              "message": error_msg
          })
          return

        json_response = {
            "status": "文档生成成功" 
        }
        yield self.create_text_message("success")
        yield self.create_json_message(json_response)
          
        
        


