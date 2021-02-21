def format_button(link, text):
    return {
        "payload": {
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
    }


def format_suggestions(options):
    return {
        "payload": {
            "richContent": [
                [
                    {
                        "options": [{'text': o} for o in options],
                        "type": "chips"
                    }
                ]
            ]
        }
    }


def format_image(description, image_path):
    return {
        "payload": {
            "richContent": [
                [
                    {
                        "rawUrl": image_path,
                        "accessibilityText": description,
                        "type": "image"
                    }
                ]
            ]
        }
    }


def format_accordion(title, subtitle, text):
    return {
        "payload": {
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
    }


def format_description(title, text_list):
    return {
        "payload": {
            'richContent': [
                [
                    {
                        'title': title,
                        'type': 'description',
                        'text': text_list
                    }
                ]
            ]
        }
    }

