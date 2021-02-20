import requests
import traceback
import json
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from random import randint

app = Flask(__name__)
api = Api(app)

# docs:
# https://www.themoviedb.org/documentation/api

search_path = 'https://api.themoviedb.org/3/search'
genre_path = 'https://api.themoviedb.org/3/genre/movie/list?'
discover_path = 'https://api.themoviedb.org/3/discover/movie?'
options = '&page=1&include_adult=false'
prev_recommendation_id = []

"""
API paths used:
First requests:
* movie discover (first request): GET /discover/movie 
* genres retrieval: GET /genre/movie/list

Follow ups:
* person follow up: GET /search/person/
* movie details follow up: GET /movie/<movie_id>
    - doesn't contain information about the cast/ crew
* movie credits follow up: GET /movie/<movie_id>/credits
    - contains crew and cast information


"""


def get_api_key():
    with open("api_key.txt", "r") as f:
        line = f.readlines()
        return line[0]


def get_person_id(person_query, api_key):
    # find the person ID in the movie API so that we can query movies with that person
    api_query = "{}/person?api_key={}&language=en-US&query={}{}".format(search_path, api_key, person_query, options)
    r = requests.get(api_query)
    results = json.loads(r.text)["results"]
    if results == []:
        # no person with that name is the movie API database
        return None
    return results[0]["id"]


def get_genre_id(genre_query, api_key):
    # find the genre ID in the movie API so that we can query movies with that genre
    # retrieve all genres with their IDs
    genres = requests.get(
        "https://api.themoviedb.org/3/genre/movie/list?api_key={}&language=en-US".format(api_key)).text
    # try matching the passed in parameter from the user with one of the existing genres
    for g in json.loads(genres)["genres"]:
        if g["name"] == genre_query.capitalize():
            return g["id"]
    # no matching genre has been found
    return None


def format_api_query(queries, api_key):
    # formatting the parameters (in their ID form) so that we can discover movies matching the user request
    formatted_query_string = ""
    for q in queries:
        if q[0] == 'genre':
            formatted_query_string += "&with_genres={}".format(q[1])
        if q[0] == 'starring':
            formatted_query_string += "&with_cast={}".format(q[1])
        if q[0] == "director":
            formatted_query_string += "&with_crew={}".format(q[1])

    api_request = "{}api_key={}&language=en-US&sort_by=popularity.desc{}&include_video=false{}".format(
        discover_path, api_key,
        options, formatted_query_string)

    return api_request


def format_recommendation(results, queries, api_key):
    # depending on the results retrieved by the movie discover query, format the response
    fulfil_txt = ""
    if results['results'] == []:
        fulfil_txt += "I didn't find any movies that match your query. "
        # get a random recommendation by the movie API
        api_request = format_api_query({}, api_key)
        results = json.loads(requests.get(api_request).text)

    i = 0
    if queries == []:
        # we don't always want to return the same movie when no parameters have been detected/ passed
        # we generate a random number which movie we should recommend from the list of movies retrieved
        i = randint(0, len(results['results'])-1)

    first_result = results['results'][i]
    # save the recommendation from this search retrieval so that we can later look it up to answer follow up requests
    prev_recommendation_id.append(first_result['id'])
    fulfil_txt += "How about {}? It has an average rating of {}".format(first_result['original_title'],
                                                                        first_result['vote_average'])
    return {'fulfillmentText': fulfil_txt}


class MovieRecommender(Resource):
    API_KEY = get_api_key()

    @staticmethod
    def post():
        api_key = get_api_key()
        queries = []

        try:
            # request body coming from Dialogflow webhook
            print(request.json)
            if not request.json:
                # something went wrong with the request
                print('No json body was provided in the request.')
                return make_response(
                    jsonify({'fulfillmentText': "Sorry, something went wrong: {}".format(traceback.format_exc())}))
            elif request.json['queryResult'].get('action') != "" and request.json['queryResult'].get(
                    'action') is not None:
                # follow up questions about movie request has an action field in it which makes it distinguishable
                # from first request
                follow_up = True
                print('Follow up detected!')
            else:
                follow_up = False
                print("First request")

            # getting the parameters found in the user utterance on Dialogflow
            params = request.json['queryResult']['parameters']
            print("params: ", params)

            # depending on the parameter found, format the query to be usable for movie API request
            if params['director'] != "":
                person_id = get_person_id("%20".join(params['director'].split(" ")), api_key)
                queries.append(('director', person_id))
            if params['starring'] != "":
                person_id = get_person_id("%20".join(params['starring'].split(" ")), api_key)
                queries.append(('starring', person_id))
            if params['genre'] != "":
                genre_id = get_genre_id(params['genre'], api_key)
                queries.append(('genre', genre_id))

            if follow_up:
                # get movie details for movie that was recommended in last recommendation
                api_request = "https://api.themoviedb.org/3/movie/{}?api_key={}&language=en-US".format(
                    prev_recommendation_id[-1], api_key)
                movie_details = json.loads(requests.get(api_request).text)
                fulfil_txt = ""
                for q in queries:
                    if q[0] == "genre":
                        genres = []
                        # retrieve all genres that the movie is classified as
                        for g in movie_details["genres"]:
                            genres.append(g['name'])
                        fulfil_txt += "The movie is a {}.".format(" and ".join(genres))
                    else:
                        # get movie credits details for cast and crew information
                        api_request = "https://api.themoviedb.org/3/movie/{}/credits?api_key={}&language=en-US".format(
                            prev_recommendation_id[-1], api_key)
                        people_details = json.loads(requests.get(api_request).text)
                        if q[0] == 'director':
                            directors = []
                            # retrieve all directors from crew information
                            for c in people_details['crew']:
                                if c['job'] == 'Director':
                                    directors.append(c['name'])
                            fulfil_txt += "It is directed by {}.".format(" and ".join(directors))
                        else:
                            actors = []
                            # retrieve the first three actors from the cast information
                            for a in people_details['cast'][:3]:
                                actors.append(a['name'])
                            fulfil_txt += "It is starring {}.".format(" and ".join(actors))

                if queries == {}:
                    # if no input parameters have been detected, still recommend a movie
                    api_request = format_api_query(queries, api_key)
                    result = json.loads(requests.get(api_request).text)
                    return make_response(jsonify(format_recommendation(result, queries, api_key)))

                # create response that can be passed back as fulfilment text to Dialogflow
                return make_response(jsonify({'fulfillmentText': fulfil_txt}))

            else:
                # first request for movie recommendation
                api_request = format_api_query(queries, api_key)
                result = json.loads(requests.get(api_request).text)
                if result == []:
                    # if no result is found for the user query, try finding a result matching the individual parameters
                    for q in queries:
                        api_request = format_api_query([q], api_key)
                        result = json.loads(requests.get(api_request).text)
                        if result != []:
                            # there has been a result found, yay!
                            break
                return make_response(jsonify(format_recommendation(result, queries, api_key)))

        except Exception:
            print("Error")
            return make_response(
                jsonify({'fulfillmentText': "Sorry, something went wrong: {}".format(traceback.format_exc())}))


# Register the movie recommender endpoint to be handled by the QuizGenerator class.
api.add_resource(MovieRecommender, '/')

if __name__ == '__main__':
    # start the server
    get_api_key()
    app.run()
    # then call ngrok http 5000, and copy paste the https link generated into the webhook settings in Dialogflow