import requests
import traceback
import json
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from app import get_api_key, format_api_query, format_recommendation, follow_up_logic, check_request_body, \
    extract_params
from richContent import format_button, format_image, format_accordion, format_suggestions

app = Flask(__name__)
api = Api(app)

# docs:
# https://www.themoviedb.org/documentation/api

search_path = 'https://api.themoviedb.org/3/search'
genre_path = 'https://api.themoviedb.org/3/genre/movie/list?'
discover_path = 'https://api.themoviedb.org/3/discover/movie?'
image_path = 'https://www.themoviedb.org/t/p/w600_and_h900_bestv2'
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
    - will need configuration API request
    
"""


def rich_reply(result_id, api_key, kind='movie'):
    api_query = f'https://api.themoviedb.org/3/{kind}/{result_id}/images?api_key={api_key}'

    r = requests.get(api_query)
    results = json.loads(r.text)["results"]
    if results == []:
        # no person with that name is the movie API database
        return None
    return


def get_tv_or_movie_intent(request_body):
    result = request_body['queryResult']
    kind_of_intent = result['outputContexts'][0]['name']
    intent = kind_of_intent.split('contexts/')[1]
    print(intent)
    if intent == 'findtv' or intent == 'findtv-followup':
        return False
    elif intent == 'findmovies' or intent == 'findmovies-followup':
        return True
    return None


class ExtendedMovieRecommender(Resource):
    API_KEY = get_api_key()

    @staticmethod
    def post():
        api_key = get_api_key()

        try:
            result = {}
            follow_up = check_request_body()
            queries = extract_params(api_key)

            # get whether it's an movie or tv request
            movie_kind = get_tv_or_movie_intent(request.json)
            if movie_kind is None:
                # something went wrong with the request
                print(request.json)
                return make_response(
                    jsonify({'fulfillmentText': "Sorry, something went wrong: {}".format(traceback.format_exc())}))

            if movie_kind:
                kind = "movie"
            else:
                kind = "tv"

            print(kind)

            if follow_up:
                if kind != last_kind[-1]:
                    print("Wrong intent matched")
                    kind = last_kind[-1]
                result = follow_up_logic(api_key, queries, kind=kind)
                watch_provider = result.get("watch_provider")
                print(watch_provider)
                if watch_provider is not None:
                    watch_text = ""

                    # checking if there can be a watch provider found for the UK
                    if watch_provider.get("GB") is None:
                        watch_provider = watch_provider.get("US")
                    else:
                        # take US if not found
                        watch_provider = watch_provider.get("GB")
                    if watch_provider is None:
                        watch_text += f'This result of type {kind} is not available on watch providers.'

                    if watch_provider.get("rent"):
                        watch_text += f'Rent this {kind} result on {watch_provider["rent"][0]["provider_name"]}. '
                    if watch_provider.get("buy"):
                        watch_text += f'Buy this {kind} result on {watch_provider["buy"][0]["provider_name"]}. '
                    if watch_provider.get("flatrate"):
                        watch_text += f'Watch this {kind} result on {watch_provider["flatrate"][0]["provider_name"]}. '
                    result['fulfillmentText'] += watch_text

                response = result

            else:
                # first request for recommendation
                last_kind.append(kind)
                api_request = format_api_query(queries, api_key, kind=kind)
                print(api_request)
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
                    print(result)
                    for i in range(len(result['results'])):
                        if result['results'][i].get('known_for') is not None:
                            result = {'results': result['results'][i]['known_for']}
                            break
                response = format_recommendation(result, queries, api_key, kind=kind)

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
