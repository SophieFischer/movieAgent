import requests
import traceback
import json
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from app import get_api_key, format_api_query, format_recommendation, follow_up_logic, check_request_body, \
    extract_params
from richContent import format_button, format_image, format_accordion, format_suggestions, format_description

app = Flask(__name__)
api = Api(app)

# docs:
# https://www.themoviedb.org/documentation/api

search_path = 'https://api.themoviedb.org/3/search'
genre_path = 'https://api.themoviedb.org/3/genre/movie/list?'
discover_path = 'https://api.themoviedb.org/3/discover/movie?'
options = '&page=1&include_adult=false'
prev_recommendation_id = []
last_kind = []

# PART B OF COURSEWORK
"""
API paths used:
First requests:
* movie discover (first request): GET /discover/movie 
* genres retrieval: GET /genre/movie/list

Follow ups:
* person follow up: GET /search/person/
* movie details follow up: GET /movie/<movie_id>
    - doesn't contain information about the cast/ crew
    - contains information about poster (take image_path) + backdrop_path
    - also a homepage, tagline, video, ...
* movie credits follow up: GET /movie/<movie_id>/credits
    - contains crew and cast information
* watch provider information: GET /movie/<movie_id>/watch/providers

* image: GET /movie/<movie_id>/image
    - image_path = base_url + size + file_path
    - will need configuration API request
    
    
Example of payload rich response for a movie query request
'''
        'fulfillmentMessages': [
            {'payload': {'richContent': [[
                {'title': '승리호', 'subtitle': None, 'text': "When the crew of a space junk collector ship called The "
                                                           "Victory discovers a humanoid robot named Dorothy that's "
                                                           "known to be a weapon of mass destruction, "
                                                           "they get involved in a risky business deal which puts "
                                                           "their lives at stake. <br/><b>Genres: </b>Drama, Fantasy, "
                                                           "Science Fiction", 'type': 'accordion'}]]}},
            {'payload': {
                'richContent': [[{'rawUrl': 'http://image.tmdb.org/t/p/w500/drulhSX7P5TQlEMQZ3JoXKSDEfz.jpg',
                                  'accessibilityText': '', 'type': 'image'}]]}},
            {'payload': {'richContent': [[{
                'icon': {'color': 'FF9800', 'type': 'link'}, 'text': 'Homepage of 승리호', 'type': 'button',
                'link': None}]]}},
            {'payload': {'richContent': [[{'options': [{'text': 'More details about directors'},
                                                       {'text': 'More details about the cast'},
                                                       {'text': 'Where to watch'}], 'type': 'chips'}]]}}],
        'fulfillmentText': 'How about 승리호? It has an average rating of 5.7'}
'''
"""


def get_person_info(person_id, api_key):
    # find the person ID in the movie API so that we can query movies with that person
    api_query = f"https://api.themoviedb.org/3/person/{person_id}?api_key={api_key}&language=en-US"
    r = requests.get(api_query)
    results = json.loads(r.text)
    if results == []:
        # no person with that name is the movie API database
        return None
    return results


def get_genre_name(genre_id, api_key, kind='movie'):
    # find the genre ID in the movie API so that we can query movies with that genre
    # retrieve all genres with their IDs
    request_api = "https://api.themoviedb.org/3/genre/{}/list?api_key={}&language=en-US".format(kind, api_key)
    genres = requests.get(request_api).text
    # try matching the passed in parameter from the user with one of the existing genres
    for g in json.loads(genres).get("genres"):
        if g["id"] == genre_id:
            return g["name"]
    # no matching genre has been found


def get_config(api_key):
    # image_path = base_url, size and file_path
    api_query = f'https://api.themoviedb.org/3/configuration?api_key={api_key}'
    r = requests.get(api_query)
    results = json.loads(r.text)['images']
    if results == []:
        # no person with that name is the movie API database
        return None
    image_base_path = results['base_url']
    return image_base_path


def get_image(result_id, api_key, kind='movie'):
    image_path = get_config(api_key) + 'w500'
    api_query = f'https://api.themoviedb.org/3/{kind}/{result_id}/images?api_key={api_key}'
    r = requests.get(api_query)
    results = json.loads(r.text)
    if results == []:
        # no person with that name is the movie API database
        return None
    first_image = results['backdrops'][0]['file_path']
    return image_path + first_image


def construct_rich_movie_recommendation(result, api_key, kind='movie'):
    print("first request")
    # adding text message from fulfillment text from part A
    messages = [{
        "text": {
            "text": [
                result['fulfillmentText']
            ]
        }
    }]
    details = result['details']
    title = details.get('original_title')
    if title is None:
        title = details.get('original_name')

    # adding accordion type overview of result
    if details.get('media_type') is not None:
        kind = details.get('media_type')
    genres = [get_genre_name(genre_id, api_key, kind=kind) for genre_id in details.get('genre_ids')]
    if kind == 'movie':
        release_date = f'<b>Release date:</b> {details.get("release_date")}'
    else:
        release_date = f'<b>First air date:</b> {details.get("first_air_date")}'
    messages.append(format_accordion(
        title=title, subtitle=details.get('tagline'),
        text=f'{details.get("overview")} <br/><b>Genres: </b>{", ".join(genres)}<br/><b>Rating: </b>'
             f'{details.get("vote_average")}<br/>{release_date}'))

    # adding image to rich content
    image_path = get_image(details['id'], api_key, kind=kind)
    messages.append(format_image("", image_path))

    # adding suggestion chips
    sug = ['More details about directors', 'More details about the cast', 'Where to watch']
    messages.append(format_suggestions(sug))
    return messages


def construct_rich_follow_up_response(response, result, api_key, kind='movie'):
    response['fulfillmentText'] += result['fulfillmentText']
    response['fulfillmentMessages'].append(
        {
            "text": {
                "text": [
                    result['fulfillmentText']
                    ]
            }
        }
    )

    # generating people info part
    people_ids = result.get("people")
    if people_ids is not []:
        for person in people_ids:
            person_info = get_person_info(person[1], api_key)
            if person_info.get('profile_path') is not None:
                image_path = get_config(api_key) + 'w185' + person_info.get('profile_path')
            else:
                image_path = ""
            if person_info.get('biography') is not None:
                text = person_info.get('biography').split(". ")
                first_text = text[0]
            else:
                text = ""
                first_text = ""
            response['fulfillmentMessages'].append(format_accordion(subtitle = first_text,
                                                                    title=person_info.get('name'),
                                                                    text=f"{' '.join(text[1:5])}</br><img src='{image_path}'/></br><b> Birthday: "
                                                                         f"</b>{person_info.get('birthday')}</br><b>"
                                                                         f"Known for: </b> {person_info.get('known_for_department')}"
                                                                    ))
    # generating watch provider response part
    watch_provider = result.get("watch_provider")
    if watch_provider is not None:
        if watch_provider.get("GB") is None:
            # take US if not found
            watch_provider = watch_provider.get("US")
        else:
            watch_provider = watch_provider.get("GB")

        # formulate text response to watch provider query
        response['fulfillmentText'] += text_response_watch_provider(watch_provider, kind=kind)
        providers = []
        if watch_provider.get("rent") is not None:
            providers.append(f'Rent on {watch_provider["rent"][0]["provider_name"]}')
        if watch_provider.get("buy") is not None:
            providers.append(f'Buy on {watch_provider["buy"][0]["provider_name"]}')
        if watch_provider.get("flatrate") is not None:
            providers.append(f'Stream on {watch_provider["flatrate"][0]["provider_name"]}')
        response['fulfillmentMessages'].append(
            format_description("Where to watch:", providers)
        )
        response['fulfillmentMessages'].append(format_button(watch_provider["link"], "TMDB result page"))

    sug = ['More details about directors', 'More details about the cast', 'Where to watch']
    response['fulfillmentMessages'].append(format_suggestions(sug))

    return response


def get_tv_or_movie_intent(request_body):
    result = request_body['queryResult']
    kind_of_intent = result['outputContexts'][0]['name']
    intent = kind_of_intent.split('contexts/')[1]
    if intent == 'findtv' or intent == 'findtv-followup':
        return False
    elif intent == 'findmovies' or intent == 'findmovies-followup':
        return True
    return None


def text_response_watch_provider(watch_provider, kind='movie'):
    watch_text = ""
    # checking if there can be a watch provider found for the UK
    if watch_provider is None:
        watch_text += f'This result of type {kind} is not available on watch providers.'
        return watch_text

    if watch_provider.get("rent"):
        watch_text += f'Rent this {kind} result on {watch_provider["rent"][0]["provider_name"]}. '
    if watch_provider.get("buy"):
        watch_text += f'Buy this {kind} result on {watch_provider["buy"][0]["provider_name"]}. '
    if watch_provider.get("flatrate"):
        watch_text += f'Watch this {kind} result on {watch_provider["flatrate"][0]["provider_name"]}. '
    return watch_text


class ExtendedMovieRecommender(Resource):
    API_KEY = get_api_key()

    @staticmethod
    def post():
        api_key = get_api_key()

        try:
            response = {'fulfillmentMessages': [], 'fulfillmentText': ""}
            follow_up = check_request_body()
            queries = extract_params(api_key)

            # get whether it's an movie or tv request
            movie_kind = get_tv_or_movie_intent(request.json)
            if movie_kind is None:
                # something went wrong with the request
                return make_response(
                    jsonify({'fulfillmentText': "Sorry, something went wrong: {}".format(traceback.format_exc())}))

            if movie_kind:
                kind = "movie"
            else:
                kind = "tv"


            if follow_up:
                if kind != last_kind[-1]:
                    # Wrong intent matched, correcting to first request type
                    kind = last_kind[-1]
                result = follow_up_logic(api_key, queries, kind=kind)
                response = construct_rich_follow_up_response(response, result, api_key, kind=kind)

            else:
                # first request for recommendation
                last_kind.append(kind)
                api_request = format_api_query(queries, api_key, kind=kind)
                result = json.loads(requests.get(api_request).text)
                if result['results'] == []:
                    # if no result is found for the user query, try finding a result matching the individual parameters
                    for q in queries:
                        api_request = format_api_query([q], api_key, kind=kind)
                        result = json.loads(requests.get(api_request).text)
                        if result != []:
                            # there has been a result found, yay!
                            break

                if "multi" in api_request:
                    for i in range(len(result['results'])):
                        if result['results'][i].get('known_for') is not None:
                            result = {'results': result['results'][i]['known_for']}
                            break
                result_dict = format_recommendation(result, queries, api_key, kind=kind)
                response['fulfillmentText'] += result_dict['fulfillmentText']
                response['fulfillmentMessages'].extend(construct_rich_movie_recommendation(result_dict, api_key, kind=kind))

            return make_response(jsonify(response))

        except Exception:
            print("Error")
            return make_response(
                jsonify({'fulfillmentText': "Sorry, something went wrong: {}".format(traceback.format_exc())}))


# Register the movie recommender endpoint to be handled by the QuizGenerator class.
api.add_resource(ExtendedMovieRecommender, '/')

if __name__ == '__main__':
    # start the server
    get_api_key()
    app.run()
    # then call ngrok http 5000, and copy paste the https link generated into the webhook settings in Dialogflow
