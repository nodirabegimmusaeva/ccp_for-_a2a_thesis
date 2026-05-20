import json
import csv
import os

from tabulate import tabulate

from protocols.text_protocol import build_text_message
from protocols.ccp_protocol import build_ccp_payload

from agents import agent_a
from agents import agent_b
from agents import agent_c

from evaluator.scorer import (
    check_forbidden,
    check_required
)

from evaluator.metrics import context_retention


# =====================================
# LOAD TASKS
# =====================================

with open("tasks/dataset.json", "r") as f:
    tasks = json.load(f)


# =====================================
# CSV SETUP
# =====================================

log_file = "logs/results.csv"

fieldnames = [
    "task_id",
    "trial",

    "text_output",
    "text_accuracy",

    "ccp_output",
    "ccp_accuracy",

    "crs"
]

file_exists = os.path.isfile(log_file)

csvfile = open(log_file, "w", newline="")

writer = csv.DictWriter(
    csvfile,
    fieldnames=fieldnames
)

writer.writeheader()


# =====================================
# RUN EXPERIMENTS
# =====================================

for task in tasks:

    for i in range(50):

        print("\n===========================")
        print("TASK:", task["task_id"])
        print("TRIAL:", i + 1)
        print("===========================\n")


        # =====================================
        # TEXT MODE
        # =====================================

        text_message = build_text_message(task)

        msg_a = agent_a.process_text(text_message)
        msg_b = agent_b.process_text(msg_a)

        final_text_output = agent_c.process_text(msg_b)


        # =====================================
        # TEXT EVALUATION
        # =====================================

        required = task["ground_truth"].get(
            "must_include",
            []
        )

        forbidden = task["ground_truth"].get(
            "must_not_include",
            []
        )

        required_score = check_required(
            final_text_output,
            required
        )

        forbidden_score = check_forbidden(
            final_text_output,
            forbidden
        )

        text_accuracy = (
            required_score * forbidden_score
        )


        # =====================================
        # CCP MODE
        # =====================================

        ccp_payload = build_ccp_payload(task)

        payload_a = agent_a.process_ccp(ccp_payload)
        payload_b = agent_b.process_ccp(payload_a)

        final_ccp_output = agent_c.process_ccp(payload_b)


        # =====================================
        # CONTEXT RETENTION
        # =====================================

        original_context = task["context"]

        final_context = payload_b["context"]

        crs = context_retention(
            original_context,
            final_context
        )


        # =====================================
        # CCP EVALUATION
        # =====================================

        required_score_ccp = check_required(
            final_ccp_output,
            required
        )

        forbidden_score_ccp = check_forbidden(
            final_ccp_output,
            forbidden
        )

        ccp_accuracy = (
            required_score_ccp *
            forbidden_score_ccp
        )


        # =====================================
        # RESULTS TABLE
        # =====================================

        table = [[
            task["task_id"],
            i + 1,
            text_accuracy,
            ccp_accuracy,
            crs
        ]]

        headers = [
            "Task",
            "Trial",
            "Text Acc",
            "CCP Acc",
            "CRS"
        ]

        print(tabulate(table, headers=headers))


        # =====================================
        # CSV LOGGING
        # =====================================

        writer.writerow({

            "task_id": task["task_id"],
            "trial": i + 1,

            "text_output": final_text_output,
            "text_accuracy": text_accuracy,

            "ccp_output": final_ccp_output,
            "ccp_accuracy": ccp_accuracy,

            "crs": crs
        })


# =====================================
# CLOSE CSV
# =====================================

csvfile.close()

print("\n===========================")
print("ALL EXPERIMENTS COMPLETE")
print("===========================\n")