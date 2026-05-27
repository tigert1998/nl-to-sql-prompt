from datetime import date
import requests
import json
import argparse
import re

import mysql.connector


def query_llm(prompt, url, model, key, **kwargs):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        **kwargs,
    }

    response = requests.post(url=url, headers=headers, json=payload)
    response_data = response.json()
    answer = response_data["choices"][0]["message"]["content"]
    return answer


def query_db(sql, host, user, password, database):
    db = mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        output = cursor.fetchall()
    except Exception as e:
        output = str(e)
    cursor.close()
    db.close()
    return output


class Logger:
    def __init__(self, log_file):
        if log_file is not None:
            self.log_fp = open(log_file, "w", encoding="utf-8")
        else:
            self.log_fp = None

    def log(self, section, s):
        if self.log_fp is not None:
            self.log_fp.write(f'<h1 style="color:red">{section}</h1>\n\n')
            self.log_fp.write(s + "\n\n")
            self.log_fp.flush()

    def close(self):
        if self.log_fp is not None:
            self.log_fp.close()


def parse_markdown_json_block(text: str):
    pattern = r"```json\s([\s\S]*?)\s```"
    matches = re.findall(pattern, text)

    if not matches:
        return None

    last_block = matches[-1].strip()

    try:
        return json.loads(last_block)
    except json.JSONDecodeError:
        return None


def load_prompt(path, args):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for k, v in args.items():
        content = content.replace(f"{{{k}}}", str(v))
    return content


def agent(query, config):
    logger = Logger(config["agent"]["log"])

    history = ""

    prompt0 = load_prompt(
        "prompt0.md", {"history": history, "query": query, "time": date.today()}
    )
    logger.log("LLM #1 Query", prompt0)

    profiles = config["llm"]["profiles"]
    profile = config["llm"]["profile"]
    output = query_llm(prompt0, **profiles[profile])
    logger.log("LLM #1 Response", output)

    obj = parse_markdown_json_block(output)
    success = obj["success"]
    if success:
        sql = obj["sql"]
        sql_time = obj["sql_time"]
        sql_result = query_db(sql, **config["db"])
        sql_time_result = query_db(sql_time, **config["db"])

        prompt1 = load_prompt(
            "prompt1.md",
            {
                "sql": sql,
                "sql_result": sql_result,
                "sql_time": sql_time,
                "sql_time_result": sql_time_result,
                "query": query,
                "history": history,
                "time": date.today(),
            },
        )
        logger.log("LLM #2 Query", prompt1)

        output = query_llm(prompt1, **profiles[profile])
        logger.log("LLM #2 Response", output)
    else:
        reason = obj["reason"]
        logger.log("Rejection Reason", reason)

    logger.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("")
    parser.add_argument("-q")

    args = parser.parse_args()

    with open("config.json", "r") as f:
        config = json.load(f)

    agent(args.q, config)
