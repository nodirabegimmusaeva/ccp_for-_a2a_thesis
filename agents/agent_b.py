import random


# =====================================
# TEXT MODE
# =====================================

def process_text(message):

    # randomly lose vegetarian info
    if random.random() < 0.35:

        message = message.replace(
            "diet: vegetarian",
            ""
        )

    # randomly lose allergy info
    if random.random() < 0.40:

        message = message.replace(
            "allergy: peanuts",
            ""
        )

    # randomly lose seat preference
    if random.random() < 0.30:

        message = message.replace(
            "seat: window",
            ""
        )

    # randomly lose injury info
    if random.random() < 0.30:

        message = message.replace(
            "injury: knee pain",
            ""
        )

    # randomly lose gaming preference
    if random.random() < 0.25:

        message = message.replace(
            "purpose: gaming",
            ""
        )

    # randomly lose food interest
    if random.random() < 0.30:

        message = message.replace(
            "interest: food",
            ""
        )

    return message


# =====================================
# CCP MODE
# =====================================

def process_ccp(payload):

    # structured payload remains stable
    return payload