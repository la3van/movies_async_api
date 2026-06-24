from models.film import ShortFilm


def build_short_film(source: dict) -> ShortFilm:
    """Собирает краткую модель фильма из данных Elasticsearch."""
    return ShortFilm(
        uuid=source['uuid'],
        title=source['title'],
        imdb_rating=source.get('imdb_rating'),
    )
