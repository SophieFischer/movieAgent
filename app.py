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
discover_path = 'https://api.themoviedb.org/3/discover/'
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


# for part B, couldn't keep it in part B because of cyclic import issues
def get_watch_provider(result_id, api_key, kind='movie'):
    api_query = f'https://api.themoviedb.org/3/{kind}/{result_id}/watch/providers?api_key={api_key}'
    r = requests.get(api_query)
    results = json.loads(r.text)['results']
    if results == []:
        # no watch provider found in the database
        return None
    return results


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


def get_genre_id(genre_query, api_key, kind='movie'):
    # find the genre ID in the movie API so that we can query movies with that genre
    # retrieve all genres with their IDs
    genres = requests.get(
        "https://api.themoviedb.org/3/genre/{}/list?api_key={}&language=en-US".format(kind, api_key)).text
    # try matching the passed in parameter from the user with one of the existing genres
    for g in json.loads(genres)["genres"]:
        if g["name"] == genre_query.capitalize():
            return g["id"]
    # no matching genre has been found
    return None


def format_api_query(queries, api_key, kind='movie'):
    # formatting the parameters (in their ID form) so that we can discover movies matching the user request
    formatted_query_string = ""
    person = False
    genre = False
    for q in queries:
        if q[0] == 'genre':
            genre = True
            formatted_query_string += "&with_genres={}".format(q[1])
        elif q[0] == 'starring':
            person = True
            formatted_query_string += "&with_cast={}".format(q[1])
        elif q[0] == "director":
            person = True
            formatted_query_string += "&with_crew={}".format(q[1])
        # elif q[0] == "watch_provider":
        #    genre = True
        #    formatted_query_string += f'&with_watch_providers={q[1]}'

    if kind == 'tv' and person and not genre:
        api_request = "{}/multi?api_key={}{}&query={}".format(search_path, api_key, options, queries[0][2])
    else:
        api_request = "{}{}?api_key={}&language=en-US&sort_by=popularity.desc{}&include_video=false{}".format(
            discover_path, kind, api_key,
            options, formatted_query_string)
    return api_request


def format_recommendation(results, queries, api_key, kind='movie'):
    # depending on the results retrieved by the movie discover query, format the response
    fulfil_txt = ""
    if results['results'] == []:
        fulfil_txt += "I didn't find anything in {} that matched your query. ".format(kind)
        # get a random recommendation by the movie API
        api_request = format_api_query({}, api_key)
        results = json.loads(requests.get(api_request).text)

    # we don't always want to return the same result
    # we generate a random number which result we should recommend from the list of movies retrieved
    i = randint(0, len(results['results'])-1)

    first_result = results['results'][i]
    title = first_result.get('original_title')
    if title is None:
        title = first_result.get('original_name')
    # save the recommendation from this search retrieval so that we can later look it up to answer follow up requests
    prev_recommendation_id.append(first_result['id'])
    fulfil_txt += "How about {}? It has an average rating of {}".format(title, first_result['vote_average'])
    return {'fulfillmentText': fulfil_txt, 'details': results['results'][i]}


def get_result_details(result_id, api_key, kind='movie'):
    # get movie details for movie that was recommended in last recommendation
    api_request = "https://api.themoviedb.org/3/{}/{}?api_key={}&language=en-US".format(
        kind, result_id, api_key)
    return json.loads(requests.get(api_request).text)


def get_result_credits(result_id, api_key, kind='movie'):
    # get movie credits details for cast and crew information
    api_request = "https://api.themoviedb.org/3/{}/{}/credits?api_key={}&language=en-US".format(
        kind, result_id, api_key)
    return json.loads(requests.get(api_request).text)


def extract_data_from_details(parameter_type, details, api_key, kind='movie'):
    fulfil_txt = ""
    watch_providers = None
    people_ids = []
    if parameter_type == "genre":
        genres = []
        # retrieve all genres that the movie is classified as
        for g in details["genres"]:
            genres.append(g['name'])
        fulfil_txt += "It is a {}.".format(" and ".join(genres))

    elif parameter_type == 'starring' or parameter_type == 'director':
        # get movie credits details for cast and crew information
        people_details = get_result_credits(prev_recommendation_id[-1], api_key, kind)
        if parameter_type == 'director':
            directors = []
            dir_ids = []

            # retrieve all directors from crew information

            for c in people_details.get('crew'):
                if c['job'] == 'Director' or c['known_for_department'] == 'Directing':
                    if c['name'] not in directors:
                        directors.append(c['name'])
                        dir_ids.append(('director', c['id']))

            # check for directors in crew dict if there is no crew dict
            if people_details.get('crew') == []:
                for c in people_details.get('cast'):
                    if c['known_for_department'] == 'Directing' and c['name'] not in directors:
                        directors.append(c['name'])
                        dir_ids.append(('director', c['id']))

            if directors == []:
                test_dir = details.get('created_by')
                if test_dir is not None:
                    print(test_dir)
                    directors.append(test_dir[0]['name'])
                    dir_ids.append(('director', test_dir[0]['id']))

            # only return the first two directors
            if len(directors) > 2:
                directors = directors[:2]
                dir_ids = dir_ids[:2]

            # format response message
            if directors != []:
                fulfil_txt += "It is directed by {}.".format(" and ".join(directors))
                people_ids.extend(dir_ids)
            else:
                title = details.get('original_name')
                if title is None:
                    title = details.get('original_title')
                fulfil_txt += "There is no director in the database for {}".format(title)

        else:
            actors = []
            # retrieve the first three actors from the cast information
            if people_details.get('cast') is not None:
                for a in people_details['cast'][:3]:
                    actors.append(a['name'])
                    people_ids.append(('actor', a['id']))
                fulfil_txt += "It is starring {}.".format(" and ".join(actors))

    elif parameter_type == 'watch_provider':
        watch_providers = get_watch_provider(result_id=prev_recommendation_id[-1], api_key=api_key, kind=kind)

    return fulfil_txt, watch_providers, people_ids


def follow_up_logic(api_key, queries, kind='movie'):
    # get movie details for movie that was recommended in last recommendation
    movie_details = get_result_details(prev_recommendation_id[-1], api_key, kind)
    fulfil_txt = ""
    watch_providers = None
    people_details = None
    for q in queries:
        # extract results from API response
        fulfil_txt, watch_providers, people_details = extract_data_from_details(q[0], movie_details, api_key, kind)

    if queries == {}:
        # if no input parameters have been detected, still recommend something of the correct kind
        api_request = format_api_query(queries, api_key)
        result = json.loads(requests.get(api_request).text)
        return format_recommendation(result, queries, api_key)

    if watch_providers is not None:
        return {'fulfillmentText': fulfil_txt, 'watch_provider': watch_providers, 'details': movie_details,
                'id': prev_recommendation_id[-1], 'people': people_details}

    # create response that can be passed back as fulfilment text to Dialogflow
    return {'fulfillmentText': fulfil_txt, 'details': movie_details, 'id': prev_recommendation_id[-1],
            'people': people_details}


def extract_params(api_key):
    queries = []

    # getting the parameters found in the user utterance on Dialogflow
    params = request.json['queryResult']['parameters']
    print("params: ", params)

    # depending on the parameter found, format the query to be usable for movie API request
    if params['director'] != "":
        formatted_person = "%20".join(params['director'].split(" "))
        person_id = get_person_id(formatted_person, api_key)
        queries.append(('director', person_id, formatted_person))
    if params['starring'] != "":
        formatted_person = "%20".join(params['starring'].split(" "))
        person_id = get_person_id(formatted_person, api_key)
        queries.append(('starring', person_id, formatted_person))
    if params['genre'] != "":
        genre_id = get_genre_id(params['genre'], api_key)
        queries.append(('genre', genre_id, params['genre']))
    if params.get('watch_provider') != "" and params.get('watch_provider') is not None:
        queries.append(('watch_provider', 0, params['watch_provider']))

    return queries


def check_request_body():
    # request body coming from Dialogflow webhook
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
    return follow_up


class MovieRecommender(Resource):
    API_KEY = get_api_key()

    @staticmethod
    def post():
        api_key = get_api_key()

        try:
            follow_up = check_request_body()
            queries = extract_params(api_key)

            if follow_up:
                response = follow_up_logic(api_key, queries)

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
                response = format_recommendation(result, queries, api_key)
            return make_response(jsonify({'fulfillmentText': response['fulfillmentText']}))

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
