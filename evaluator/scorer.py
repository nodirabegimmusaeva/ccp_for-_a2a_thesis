FORBIDDEN_VARIATIONS = {
    "peanuts": [
        "peanut",
        "peanuts"
    ],
    "chicken": [
        "chicken"
    ],
    "beef": [
        "beef"
    ]
}


def check_forbidden(output, forbidden_items):

    output = output.lower()

    for item in forbidden_items:

        variations = FORBIDDEN_VARIATIONS.get(
            item,
            [item]
        )

        for word in variations:

            safe_phrase = f"without {word}"

            if word in output:

                if safe_phrase not in output:
                    return 0

    return 1


def check_required(output, required_words):

    output = output.lower()

    for word in required_words:

        if word.lower() not in output:
            return 0

    return 1