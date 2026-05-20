def build_ccp_payload(task):

    payload = {

        # protocol metadata
        "protocol_version": "1.0",
        "message_type": "task_request",

        # routing
        "task_id": task["task_id"],
        "agent_id": "A",

        # actual task
        "request": task["request"],

        # structured context
        "context": task["context"],

        # explicit constraints
        "constraints": task["ground_truth"],

        # traceability
        "history": [
            {
                "agent": "A",
                "action": "created_payload"
            }
        ]
    }

    return payload