from datetime import date
import requests
import json
import argparse
import re

import mysql.connector


def query_llm(prompt, url, model, key):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "enable_thinking": False,
    }

    response = requests.post(url=url, headers=headers, json=payload)
    response_data = response.json()
    answer = response_data["choices"][0]["message"]["content"]
    return answer


def decode_xml_entities(input_str):
    xml_entities = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&apos;": "'",
    }
    return re.sub(
        r"&(lt|gt|amp|quot|apos);",
        lambda match: xml_entities[match.group(0)],
        input_str,
    )


def extract_xml_tag(s, tag):
    ms = re.findall(f"<{tag}>([\\s\\S]*?)<\\/{tag}>", s)
    if len(ms) <= 0:
        return None
    return decode_xml_entities(ms[-1])


def query_db(sql, host, user, password, database):
    db = mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )
    cursor = db.cursor()
    cursor.execute(sql)
    output = cursor.fetchall()
    cursor.close()
    db.close()
    return output


class Logger:
    def __init__(self, log_file):
        if log_file is not None:
            self.log_fp = open(log_file, "w", encoding="utf-8")
            self.is_first = True
        else:
            self.log_fp = None

    def log(self, section, s):
        if self.log_fp is not None:
            self.log_fp.write(f'<h1 style="color:red">{section}</h1>\n')
            self.log_fp.write(s + "\n")
            self.log_fp.flush()
            self.is_first = False

    def close(self):
        if self.log_fp is not None:
            self.log_fp.close()


def agent(query, config):
    logger = Logger(config["agent"]["log"])

    with open("prompt0.md", "r", encoding="utf-8") as f:
        prompt0 = f.read()
    with open("prompt1.md", "r", encoding="utf-8") as f:
        prompt1 = f.read()

    history = ""

    prompt0 = prompt0.format(history=history, query=query, time=date.today())
    logger.log("LLM #1 Query", prompt0)

    output = query_llm(prompt0, **config["llm"])
    logger.log("LLM #1 Response", output)

    success = extract_xml_tag(output, "success")
    success = int(success) > 0
    if success:
        sql = extract_xml_tag(output, "sql")
        sql_time = extract_xml_tag(output, "sql_time")
        sql_result = query_db(sql, **config["db"])
        sql_time_result = query_db(sql_time, **config["db"])

        prompt1 = prompt1.format(
            sql=sql,
            sql_result=sql_result,
            sql_time=sql_time,
            sql_time_result=sql_time_result,
            query=query,
            history=history,
        )
        logger.log("LLM #2 Query", prompt1)

        output = query_llm(prompt1, **config["llm"])
        logger.log("LLM #2 Response", output)
    else:
        reason = extract_xml_tag(output, "reason")
        logger.log("Rejection Reason", reason)

    logger.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser("")
    parser.add_argument("-q")

    args = parser.parse_args()

    with open("config.json", "r") as f:
        config = json.load(f)

    agent(args.q, config)
