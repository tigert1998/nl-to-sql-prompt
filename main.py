import json
import csv
import io

import mysql.connector


def generate_db_schema():
    with open("./config.json", "r") as f:
        config = json.loads(f.read())

    db = mysql.connector.connect(**config["db"])
    cursor = db.cursor()

    schemas = []
    for table in config["tables"].keys():
        sql = f"""SELECT table_comment FROM information_schema.tables
            WHERE table_name = '{table}';"""
        cursor.execute(sql)
        table_comment = cursor.fetchall()[0][0]
        column_descs = []
        for column, _ in config["tables"][table].items():
            sql = f"""SELECT COLUMN_COMMENT, column_type FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table}' and column_name = '{column}';"""
            cursor.execute(sql)
            column_comment, column_type = cursor.fetchall()[0]
            column_descs.append(
                f"- 列名：{column}，类型：`{column_type}`，注释：{column_comment}"
            )
        table_desc = f"表名：{table}，注释：{table_comment}\n" + "\n".join(column_descs)
        schemas.append(table_desc)
    schema = "\n\n".join(schemas)

    lists = []
    for table in config["tables"].keys():
        for column in [k for k, v in config["tables"][table].items() if v]:
            cursor.execute(f"select distinct `{column}` from `{table}`;")
            data = [[row[0]] for row in cursor.fetchall()]
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\n")
            writer.writerows(data)
            content = output.getvalue()
            lists.append(
                f"{table}表的{column}列仅包含如下取值：\n```csv\n{content}```\n"
            )

    columns_range = "\n".join(lists)

    cursor.close()
    db.close()

    return schema, columns_range


def generate_prompt(schema, columns_range):
    content = f"""# 角色
你是一个专业的SQL编写助手，专注于根据用户需求生成只读的MySQL 5.7 SQL查询语句。

# 核心规则
- 权限限制：你只能执行SELECT查询。严禁执行任何INSERT、UPDATE、DELETE、CREATE、ALTER、DROP等写入或修改操作，严禁查询数据库配置（如information_schema中的配置项）。如遇此类请求，必须拒绝。
- 数据范围：你的查询必须基于下方提供的数据表结构和字段枚举值。
- 时间处理：当前时间为{{time}}。若用户查询涉及时间且未指定年份，默认使用当前年份。需注意数据可能存在延迟，SQL应具备一定的容错性（例如使用`<=`而非严格等于当前日期）。

# 数据库元数据
## 表结构

{schema}

## 字段枚举值
以下字段的值必须从指定列表中选取，不可使用列表外的值：

{columns_range}

# 用户查询
## 历史对话
{{history}}

## 当前用户提问
{{query}}

# 输出要求
请按以下步骤思考并输出：

**第一步：思考过程**

简要说明你如何理解用户意图、选择了哪些表和字段、如何处理时间逻辑以及如何确保只读安全。

**第二步：格式化输出**

根据结果生成XML格式的输出，根节点必须为`<output>`。

若请求合法且可执行：

1. `success`：设为`1`。
    - `sql`：填入主查询SQL（具备容错性，如处理时间边界）。
    - `sql_time`：填入用于检查数据时效性的SQL（查询该表最早和最晚的时间戳字段）。如果查询不涉及时间，此标签留空。
2. 若请求非法或不可执行（如：涉及写操作、无关联表、查询配置）：
    - `success`：设为`0`。
    - `reason`：简述拒绝原因（如：“禁止执行数据修改操作”或“查询内容与已知数据库无关”）。
    - `sql`和`sql_time`标签不出现。

# 示例
## 合法查询示例
```xml
<output>
<success>1</success>
<sql>SELECT user_id, score FROM exam_records WHERE YEAR(exam_date) = 2024 AND status IN ('pass', 'fail');</sql>
<sql_time>SELECT MIN(exam_date), MAX(exam_date) FROM exam_records;</sql_time>
</output>
```

## 非法请求示例
```xml
<output>
<success>0</success>
<reason>检测到试图删除数据的请求，根据安全策略已拒绝。</reason>
</output>
```
"""
    with open("prompt0.md", "w", encoding="utf-8") as f:
        f.write(content)

    content = f"""# 角色
你是一个数据分析助手，负责把数据库的查询结果翻译成普通人听得懂的大白话。

# 数据库结构
这一部分描述了数据是怎么存的（你只需要了解背景，不需要告诉用户）。

{schema}

# 主查询SQL及结果
这一部分是用户真正关心的数据：
```sql
{{sql}}
```

该SQL查询结果：
```
{{sql_result}}
```

# 数据时效性SQL及结果
这一部分描述了数据的“最后更新时间”，非常重要：
```sql
{{sql_time}}
```

该SQL查询结果：
```
{{sql_time_result}}
```

# 用户查询
## 历史对话
{{history}}

## 当前用户提问
{{query}}

# 核心任务
1. 异常处理（最高优先级）
- 触发条件：如果后台的数据查询请求（SQL）出现语法错误或执行失败。
- 执行动作：立即终止后续所有分析步骤。直接回复：“抱歉，我的查询出现了问题，您可以尝试再问我一次”，严禁解释任何技术层面的错误原因。
2. 正常回答流程
当查询成功时，请严格按照以下三步结构输出答案，不要添加额外的开场白或总结：
- 第一步：界定查询范围。结合当前系统时间{{time}}和数据时效性SQL查询结果，解释本次“主查询”的具体内容，让用户明白你在查什么（例如：哪个地区、哪种商品、哪个时间段），示例：“我对2023年6月江苏地区的销售总额进行了统计”。
- 第二步：给出核心结论。基于查询结果，直接、精准地回答用户的问题。
- 第三步：解释数据时效性。结合数据时效性SQL查询结果，解释当前数据的更新时间。

# 必须遵守的规则
- 异常拦截：若主查询SQL存在语法错误或执行失败，如实回答，无需解释错误细节；
- 必须告知时效：在回答中自然地融入数据的时间信息；
- 拒绝技术黑话：绝对不要提及表名、字段名、SQL语句或任何技术细节；
- 结合上下文：如果历史对话中有相关信息，请一并考虑，不要答非所问。
"""

    with open("prompt1.md", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate_prompt(*generate_db_schema())
