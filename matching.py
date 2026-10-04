import re


# Words that should not affect matching
STOP_WORDS = {
    "the",
    "is",
    "for",
    "my",
    "i",
    "need",
    "want",
    "this",
    "that",
    "item",
    "and",
    "or",
    "a",
    "an",
    "to",
    "of",
    "in",
    "with",
    "from",
    "on",
    "have",
    "has",
    "please",
    "give",
    "get",
    "looking",
    "look"
}


def get_words(text):
    """
    Convert text into useful keywords.
    """

    if not text:
        return set()

    words = re.findall(
        r"[a-zA-Z0-9]+",
        text.lower()
    )

    return {
        word
        for word in words
        if len(word) > 2
        and word not in STOP_WORDS
    }


def calculate_match(item, recipient):
    """
    Calculate how well an item matches
    a recipient's requirement.

    Maximum score = 100
    """

    score = 0
    reasons = []

    # ==================================================
    # 1. CATEGORY MATCH - 30 POINTS
    # ==================================================

    item_category = (
        item["category"] or ""
    ).lower().strip()

    recipient_category = (
        recipient["category"] or ""
    ).lower().strip()

    if (
        item_category
        and recipient_category
        and item_category == recipient_category
    ):
        score += 30

        reasons.append(
            "Category matches"
        )

    # ==================================================
    # 2. KEYWORD MATCH - 30 POINTS
    # ==================================================

    item_title = item["title"] or ""
    item_description = item["description"] or ""

    item_text = (
        item_title
        + " "
        + item_description
    )

    requirement = (
        recipient["requirement"] or ""
    )

    item_words = get_words(item_text)
    requirement_words = get_words(requirement)

    common_words = (
        item_words.intersection(
            requirement_words
        )
    )

    if common_words:

        keyword_score = min(
            len(common_words) * 10,
            30
        )

        score += keyword_score

        reasons.append(
            "Keyword match: "
            + ", ".join(
                sorted(common_words)
            )
        )

    # ==================================================
    # 3. LOCATION MATCH - 20 POINTS
    # ==================================================

    item_location = (
        item["location"] or ""
    ).lower().strip()

    recipient_location = (
        recipient["location"] or ""
    ).lower().strip()

    if (
        item_location
        and recipient_location
        and item_location == recipient_location
    ):
        score += 20

        reasons.append(
            "Same location"
        )

    # ==================================================
    # 4. CONDITION - 10 POINTS
    # ==================================================

    condition = (
        item["condition"] or ""
    ).lower().strip()

    if condition == "new":

        score += 10

        reasons.append(
            "Item is in new condition"
        )

    elif condition == "like new":

        score += 10

        reasons.append(
            "Item is in like-new condition"
        )

    elif condition == "good":

        score += 8

        reasons.append(
            "Item is in good condition"
        )

    elif condition == "used":

        score += 5

        reasons.append(
            "Item is usable"
        )

    # ==================================================
    # 5. TITLE RELEVANCE - 10 POINTS
    # ==================================================

    title_words = get_words(
        item_title
    )

    title_matches = (
        title_words.intersection(
            requirement_words
        )
    )

    if title_matches:

        score += 10

        reasons.append(
            "Item title matches your requirement"
        )

    # ==================================================
    # FINAL SCORE
    # ==================================================

    # Make sure score never goes above 100
    score = min(score, 100)

    return score, reasons