def build_text_message(task):

    request = task["request"]
    context = task["context"]

    message = f"Request: {request}\n"

    for key, value in context.items():
        message += f"{key}: {value}\n"

    return message