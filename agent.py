from datetime import date
import requests
import json
import argparse
import re

import mysql.connector
import yaml


def query_llm(system_prompt, query, url, model, key, **kwargs):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
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


def parse_markdown_yaml_block(text: str):
    pattern = r"```ya?ml\s([\s\S]*?)\s```"
    matches = re.findall(pattern, text)
    last_block = matches[-1].strip()
    return yaml.safe_load(last_block)


def load_prompt(path, args):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for k, v in args.items():
        content = content.replace(f"{{{k}}}", str(v))
    return content


def agent(query, config):
    logger = Logger(config["agent"]["log"])

    history = ""

    prompt0 = load_prompt("prompt0.md", {"time": date.today()})
    logger.log("LLM #1 Query", prompt0)

    profiles = config["llm"]["profiles"]
    profile = profiles[config["llm"]["profile"]]
    output = query_llm(prompt0, query, **profile)
    logger.log("LLM #1 Response", output)

    obj = parse_markdown_yaml_block(output)
    success = obj["success"]
    if success:
        main_sql = obj["main_sql"]
        time_sql = obj["time_sql"]
        main_sql_result = query_db(main_sql, **config["db"])
        time_sql_result = query_db(time_sql, **config["db"])

        prompt1 = load_prompt(
            "prompt1.md",
            {
                "main_sql": main_sql,
                "main_sql_result": main_sql_result,
                "time_sql": time_sql,
                "time_sql_result": time_sql_result,
                "time": date.today(),
            },
        )
        logger.log("LLM #2 Query", prompt1)

        output = query_llm(prompt1, query, **profile)
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
