import json
import csv
import io

import mysql.connector


def generate_db_schema():
    with open("./config.json", "r") as f:
        config = json.loads(f.read())

    db = mysql.connector.connect(**config["db"])
    cursor = db.cursor()
    cursor.execute("show tables;")
    tables = [row[0] for row in cursor.fetchall()]

    schema_sqls = []
    for table in tables:
        cursor.execute(f"show create table `{table}`;")
        _, sql = cursor.fetchall()[0]
        schema_sqls.append(sql + ";")

    columns_range = []
    for dic in config["columns"]:
        table = dic["table"]
        column = dic["column"]
        cursor.execute(f"select distinct `{column}` from `{table}`;")
        data = [[row[0]] for row in cursor.fetchall()]
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerows(data)
        csv_string = output.getvalue()
        columns_range.append((table, column, csv_string))

    cursor.close()
    db.close()

    schema = "\n\n".join(schema_sqls)
    return schema, columns_range


def generate_prompt(schema, columns_range):
    ls = []
    for table, column, content in columns_range:
        ls.append(f"`{table}`表的`{column}`列仅包含如下取值：\n```csv\n{content}```\n")

    content = f"""# 角色
你是SQL编写机器人，能根据用户的查询需求生成正确无误的SQL语句。你仅能对已知的数据表进行只读查询，你应当拒绝所有涉及增加、修改、删除数据表的用户请求，你应当拒绝所有涉及数据库配置查询、修改的请求。

# 数据库
这是一个MySQL 5.7版本数据库，你能查询的数据表格如下所示：
```sql
{schema}
```

数据表格中部分字段仅能从有限的值中选择，务必在构建SQL时不要超出给定的取值列表，下面是这些列的可选值列表：

{"\n".join(ls)}

# 用户查询
{{query}}

# 任务要求
1. 在用户查询能够实现的情况下，根据用户查询和数据表格结构，生成正确的SQL查询语句；
2. 现在的时间是{{time}}，如果用户查询涉及时间且没有明确指定年份，则默认指代今年，你需要在SQL语句中指定为今年；
3. 生成两条SQL语句：
    - 第一条：查询用户所需数据，因为数据更新可能不及时，所以生成的SQL需要具有容错性；
    - 第二条：查询相关数据的最早和最晚时间，作为数据更新时效的参考。若查询不涉及时间，则第二条SQL留空。

# 格式
按照XML格式输出，标签内容中不要转义特殊字符，即保留原有的`<&>"'`。XML的顶部节点名字必须为`output`。如果用户查询与已知数据库无关，或者用户希望增加、删除、修改数据表，或者其他高危越权情况，则继续生成`success`标签为0的XML，并继续生成包含拒绝理由的`reason`标签，例如：

```xml
<output>
<success>0</success>
<reason>用户查询与已知数据库无关，无法生成SQL语句</reason>
</output>
```

或者：

```xml
<output>
<success>0</success>
<reason>用户希望修改数据表项，应拒绝</reason>
</output>
```

若用户查询可成功转化为SQL语句，则输出`success`标签值为1，并依次生成包含目标SQL的`sql`标签，以及用于查询数据时间区间的`sql_time`标签。示例如下：

```xml
<output>
<success>1</success>
<sql>select required_data from sample_table;</sql>
<sql_time>select min(start_date), max(end_date) from sample_table;</sql_time>
</output>
```
"""
    with open("prompt0.md", "w") as f:
        f.write(content)

    content = f"""# 数据库结构
```sql
{schema}
```

# SQL
{{sql}}

该SQL查询结果：

{{sql_result}}

# 用于查询有效数据记录时间的SQL
{{sql_time}}

该SQL查询结果：

{{sql_time_result}}

# 用户提问
{{query}}

# 任务
根据数据库的表结构、SQL查询结果，回答用户提问，不得透露数据表名称等信息。
"""

    with open("prompt1.md", "w") as f:
        f.write(content)


if __name__ == "__main__":
    generate_prompt(*generate_db_schema())
