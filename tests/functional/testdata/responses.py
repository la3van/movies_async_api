def genre_to_response(document: dict) -> dict:
    return {
        'uuid': document['uuid'],
        'name': document['name'],
    }


def movie_to_short_response(document: dict) -> dict:
    return {
        'uuid': document['uuid'],
        'title': document['title'],
        'imdb_rating': document['imdb_rating'],
    }
