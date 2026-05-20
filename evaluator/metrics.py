def context_retention(original_context, final_context):

    total = len(original_context)
    preserved = 0

    for key, value in original_context.items():

        if key in final_context:

            if final_context[key] == value:
                preserved += 1

    return preserved / total