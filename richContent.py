
def format_button(link, text):
    return {
        "richContent": [
            [
                {
                    "icon": {
                        "color": "FF9800",
                        "type": "link"
                    },
                    "text": text,
                    "type": "button",
                    "link": link
                }
            ]
        ]
    }


def format_suggestions():
    return {
        "richContent": [
            [
                {
                    "options": [
                        {
                            "text": "go back to main menu"
                        }
                    ],
                    "type": "chips"
                }
            ]
        ]
    }


def format_image(link, description, image_path):
    return {
        "richContent": [
            [
                {
                    "rawUrl": image_path+link,
                    "accessibilityText": description,
                    "type": "image"
                }
            ]
        ]
    }


def format_accordion(title, subtitle, text):
    return {
        "richContent": [
            [
                {
                    "title": title,
                    "subtitle": subtitle,
                    "text": text,
                    "type": "accordion"
                }
            ]
        ]
    }

"""
        response_body["fulfillmentText"] = next_question[0]

    response_body["fulfillmentMessages"].append(
        {
            "text": {
                "text": [
                    next_question[0]
                ]
            }
        }
    )
    response_body["fulfillmentMessages"].append(
        {
            "payload": {
                "richContent": [
                    [
                        {
                            "options": [
                                {
                                    "text": "A:" + next_question[1]
                                },
                                {
                                    "text": "B:" + next_question[2]
                                },
                                {
                                    "text": "C:" + next_question[3]
                                }
                            ],
                            "type": "chips"
                        }
                    ]
                ]
            }
        }

    )
"""