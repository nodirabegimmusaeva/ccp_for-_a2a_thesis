def process_text(message):

    msg = message.lower()


    # =====================================
    # TASK 001 — FOOD
    # =====================================

    if "dinner" in msg:

        if "vegetarian" in msg:

            if "peanut" in msg:
                return "Vegetarian tofu rice bowl without peanuts"

            return "Vegetarian peanut curry"

        return "Chicken steak"


    # =====================================
    # TASK 002 — FLIGHT
    # =====================================

    if "flight" in msg:

        if "tokyo" in msg:

            if "window" in msg:
                return "Low-cost flight to Tokyo with window seat"

            return "Cheap Tokyo flight"

        return "Flight to Paris"


    # =====================================
    # TASK 003 — WORKOUT
    # =====================================

    if "workout" in msg:

        if "knee pain" in msg:
            return "Low-impact walking and cycling plan"

        return "High-impact jumping workout"


    # =====================================
    # TASK 004 — LAPTOP
    # =====================================

    if "laptop" in msg:

        if "gaming" in msg:
            return "Gaming laptop with RTX graphics"

        return "Office laptop"


    # =====================================
    # TASK 005 — TRAVEL
    # =====================================

    if "itinerary" in msg:

        if "food" in msg:
            return "5-day Japan food tour itinerary"

        return "Museum itinerary"


    return "Generic recommendation"



def process_ccp(payload):

    request = payload["request"].lower()

    context = payload["context"]


    # =====================================
    # TASK 001
    # =====================================

    if "dinner" in request:

        diet = context.get("diet", "")
        allergy = context.get("allergy", "")

        if diet == "vegetarian":

            if allergy == "peanuts":
                return "Vegetarian tofu rice bowl without peanuts"

            return "Vegetarian peanut curry"


    # =====================================
    # TASK 002
    # =====================================

    if "flight" in request:

        destination = context.get("destination", "")
        seat = context.get("seat", "")

        if destination == "Tokyo":

            if seat == "window":
                return "Low-cost flight to Tokyo with window seat"

            return "Cheap Tokyo flight"


    # =====================================
    # TASK 003
    # =====================================

    if "workout" in request:

        injury = context.get("injury", "")

        if injury == "knee pain":
            return "Low-impact walking and cycling plan"

        return "High-impact jumping workout"


    # =====================================
    # TASK 004
    # =====================================

    if "laptop" in request:

        purpose = context.get("purpose", "")

        if purpose == "gaming":
            return "Gaming laptop with RTX graphics"

        return "Office laptop"


    # =====================================
    # TASK 005
    # =====================================

    if "itinerary" in request:

        interest = context.get("interest", "")

        if interest == "food":
            return "5-day Japan food tour itinerary"

        return "Museum itinerary"


    return "Generic recommendation"