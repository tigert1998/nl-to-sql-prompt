# NL2SQL 提示词生成器

本工具用于自动生成 **NL2SQL（自然语言转SQL）** 所需的提示词，并支持端到端测试。

## 功能概述

- **提示词生成**：运行 `main.py`，自动读取数据库结构与配置，生成两部分提示词：
  1. **SQL生成提示词**：将自然语言问题转化为 SQL 查询语句。
  2. **结果解析提示词**：根据 SQL 执行结果，用自然语言回答用户问题。
- **测试验证**：运行 `agent.py`，使用生成好的提示词与大模型交互，完成完整的 NL2SQL 问答测试。

## 配置说明

所有配置统一存放在 `config.json` 中，格式如下：

```json
{
    "db": {
        "host": "数据库地址",
        "user": "用户名",
        "password": "密码",
        "database": "数据库名"
    },
    "tables": {
        "表名": {
            "desc": "表的注释",
            "columns": {
                "列名1": {
                    "desc": "列的注释",
                    "enumerable": true
                },
                "列名2": {
                    "desc": "列的注释",
                    "enumerable": false
                }
            }
        }
    },
    "llm": {
        "profile": "模型提供商名字",
        "profiles": {
            "模型提供商名字": {
                "key": "API密钥",
                "url": "https://模型接口地址/v1/chat/completions",
                "model": "模型名称"
            }
        }
    },
    "agent": {
        "log": "./log.md"
    }
}
```

### 配置项说明

| 字段 | 说明 |
|------|------|
| `db` | MySQL 数据库连接信息。 |
| `tables` | 参与查询的表及其列，`desc` 为表、列的注释，`enumerable` 字段表示列的取值是否需要在提示词中枚举出来。|
| `llm` | `agent.py` 使用的大模型配置（API Key、接口地址、模型名称）。 |
| `agent` | `agent.py` 的运行配置，如日志文件路径。 |

## 快速开始

1. **准备配置**：填写 `config.json`。
2. **生成提示词**：
   ```bash
   python main.py
   ```
3. **测试提示词**：
   ```bash
   python agent.py
   ```

## 工作流程

```
自然语言问题 → [SQL生成提示词] → SQL查询 → 执行查询 → [结果解析提示词] → 自然语言答案
```
