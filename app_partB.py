import requests
import traceback
import json
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from app import get_api_key, format_api_query, format_recommendation, follow_up_logic, check_request_body, extract_params
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
* image: GET /movie/<movie_id>/image
    


"""


def rich_reply():
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
            follow_up = check_request_body()
            queries = extract_params(api_key)

            # get whether it's an movie or tv request
            movie_kind = get_tv_or_movie_intent(request.json)
            print("movie kind: ", movie_kind)
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
                return make_response(jsonify(follow_up_logic(api_key, queries, kind=kind)))
            else:
                # first request for recommendation
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
                return make_response(jsonify(format_recommendation(result, queries, api_key, kind=kind)))

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
