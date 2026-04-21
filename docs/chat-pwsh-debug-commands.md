# Chat 接口 pwsh 调试命令（已实测）

本文档只包含已在 `pwsh` 中实测通过的命令，目标是方便你调试当前项目的 SSE 流式传输内容。

## 0. 启动服务

```powershell
c:/Users/tangx/Desktop/RAG/.venv/Scripts/python.exe main.py
```

服务地址默认：`http://127.0.0.1:8080`

## 1. 获取会话列表

接口：`GET /api/conversations`

```powershell
$baseUrl = 'http://127.0.0.1:8080'; Invoke-RestMethod -Uri "$baseUrl/api/conversations" -Method GET | ConvertTo-Json -Depth 8
```

用途：拿到 `conversation_id`，供后续详情查询、继续对话、删除会话使用。

## 2. 获取单个会话详情

接口：`GET /api/conversations/{conversation_id}`

```powershell
$baseUrl = 'http://127.0.0.1:8080'; $conversationId = (Invoke-RestMethod -Uri "$baseUrl/api/conversations" -Method GET | Select-Object -First 1).id; Invoke-RestMethod -Uri "$baseUrl/api/conversations/$conversationId" -Method GET | ConvertTo-Json -Depth 10
```

用途：查看 rounds、prompt、answer、sources 等完整历史内容。

## 3. 发起流式对话（原始 SSE 输出）

接口：`POST /api/chat`

```powershell
$baseUrl = 'http://127.0.0.1:8080'; $json = '{"question":"请用一句话回复：这是 pwsh SSE 调试。"}'; curl.exe -N -H "Content-Type: application/json" -X POST "$baseUrl/api/chat" -d $json
```

用途：完整观察 SSE 原始事件流（`event: conversation`、`event: sources`、`event: token`、`event: done`）。

## 4. 在已有会话中继续流式对话（仅保留 event/data 行）

接口：`POST /api/chat`

```powershell
$baseUrl = 'http://127.0.0.1:8080'; $conversationId = (Invoke-RestMethod -Uri "$baseUrl/api/conversations" -Method GET | Select-Object -First 1).id; $json = @{ question = 'Reply with OK only'; conversation_id = $conversationId } | ConvertTo-Json -Compress; curl.exe -NsS -H "Content-Type: application/json" -X POST "$baseUrl/api/chat" -d $json | Select-String '^(event:|data:)'
```

用途：聚焦观察事件类型和 data 内容，减少终端噪音。

## 5. 删除会话

接口：`DELETE /api/conversations/{conversation_id}`

```powershell
$baseUrl = 'http://127.0.0.1:8080'; $conversationId = '7d39b7f1-c132-4d1a-9b0f-cecaedc2db74'; Invoke-RestMethod -Uri "$baseUrl/api/conversations/$conversationId" -Method DELETE | ConvertTo-Json
```

用途：清理测试数据，避免测试会话累积（请先替换为你要删除的 `conversation_id`，再执行）。

## 6. SSE 调试要点

- `curl.exe -N` 用于关闭缓冲，实时看到 token 推送。
- `curl.exe -NsS` 在保留流式输出的同时去掉进度条干扰。
- 若只想看 token，可在命令后追加：

```powershell
| Select-String '"content"'
```

- 若出现中文乱码，先执行：

```powershell
chcp 65001
```

然后再重新执行 SSE 调试命令。
