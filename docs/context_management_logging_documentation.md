# 上下文管理日志逻辑文档（Step 4）

## 1. 设计目标

- 日志能力可注入、可替换。
- 是否启用由 DI 统一控制，不在业务代码中分散配置。
- 默认关闭，避免无意引入运行时噪声。

## 2. 设计落点

- 应用层接口：`Backend/Application/Interfaces/ILogger.py`
- 基础设施实现：`Backend/Infrastructure/logging/ContextModuleLogger.py`
  - `PythonLoggerAdapter`：写入 Python logging。
  - `NullLogger`：空实现（关闭日志时使用）。
- 注入点（唯一开关）：`Backend/Web/app_factory.py`

## 3. DI 开关规则

当前开关环境变量：`CONTEXT_MODULE_LOG_ENABLED`

- `true/1/yes/on`：启用上下文日志。
- 其他或未设置：关闭上下文日志（注入 `NullLogger`）。

对应实现：
- `app_factory.py` 读取环境变量 -> 构造 logger -> 注入 `DefaultContextManager(context_logger=...)`。

## 4. 日志事件目录

事件由 `DefaultContextManager._log_debug()` 发出，核心事件如下：
- `Context orchestration started`
- `Path pruning finished`
- `MMR deduplication finished`
- `Retrieval reordering finished`
- `Token budget evaluated`
- `History tiering applied`
- `Vector compression applied`
- `Vector hard cap applied`
- `KG one-hop restriction applied`
- `Context orchestration completed`

## 5. 日志上下文字段规范

- 计数字段：`seed_count`, `path_count`, `source_count`, `history_rounds`。
- 参数字段：`min_confidence`, `top_k`, `relevance_weight`, `keep_rate`。
- 结果字段：`before`, `after`, `actions`, `final_prompt_tokens`。
- 数值精度：利用率建议保留 4 位小数。

## 6. 安全与合规要求

- 禁止记录完整用户原文、完整文档片段。
- 优先记录统计值与动作标记。
- 错误场景日志应可定位阶段，但不泄露敏感内容。

## 7. 运维建议

- 生产默认关闭，仅在排障窗口短时开启。
- 开启时建议将 logger 名称 `Backend.ContextManagement` 单独配置级别与输出目标。
- 若日志量增加，优先降采样 debug，而非删除关键事件。

## 8. 审核结论模板（日志维度）

- 注入方式是否唯一：是/否
- 开关默认是否关闭：是/否
- 是否存在敏感字段泄露：是/否
- 关键阶段是否有事件覆盖：是/否
- 关闭开关时是否完全静默：是/否
