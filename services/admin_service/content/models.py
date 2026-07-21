"""Неуправляемые Django-модели существующей контентной базы."""
from __future__ import annotations

import uuid

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _


class UUIDMixin(models.Model):
    """Добавляет UUID-первичный ключ модели."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        """Метаданные абстрактного UUID-миксина."""
        abstract = True


class TimeStampedMixin(models.Model):
    """Добавляет даты создания и изменения записи."""
    created = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )
    modified = models.DateTimeField(
        auto_now=True,
        null=True,
    )

    class Meta:
        """Метаданные абстрактного временного миксина."""
        abstract = True


class Genre(
    UUIDMixin,
    TimeStampedMixin,
):
    """Жанр фильма или сериала."""
    name = models.CharField(
        _("name"),
        max_length=255,
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        """Возвращает название жанра."""
        return self.name

    class Meta:
        """Метаданные модели жанра."""
        managed = False
        db_table = 'content"."genre'
        verbose_name = _("genre")
        verbose_name_plural = _("genres")
        ordering = ("name",)


class Person(
    UUIDMixin,
    TimeStampedMixin,
):
    """Персона, участвовавшая в создании фильма."""
    full_name = models.CharField(
        _("full name"),
        max_length=255,
    )

    def __str__(self) -> str:
        """Возвращает полное имя персоны."""
        return self.full_name

    class Meta:
        """Метаданные модели персоны."""
        managed = False
        db_table = 'content"."person'
        verbose_name = _("person")
        verbose_name_plural = _("persons")
        ordering = ("full_name",)


class FilmTypes(models.TextChoices):
    """Допустимые типы кинопроизведений."""

    MOVIE = "movie", _("movie")
    TV_SHOW = "tv show", _("tv show")


class FilmWork(
    UUIDMixin,
    TimeStampedMixin,
):
    """Фильм или сериал."""
    title = models.CharField(
        _("title"),
        max_length=255,
    )
    description = models.TextField(
        _("description"),
        blank=True,
        null=True,
    )
    creation_date = models.DateField(
        _("creation date"),
        blank=True,
        null=True,
    )
    rating = models.FloatField(
        _("rating"),
        blank=True,
        null=True,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(10.0),
        ],
    )
    type = models.CharField(
        _("type"),
        max_length=7,
        choices=FilmTypes.choices,
        default=FilmTypes.MOVIE,
    )

    genres = models.ManyToManyField(
        Genre,
        through="GenreFilmWork",
        related_name="film_works",
        verbose_name=_("genres"),
    )
    persons = models.ManyToManyField(
        Person,
        through="PersonFilmWork",
        related_name="film_works",
        verbose_name=_("persons"),
    )

    def __str__(self) -> str:
        """Возвращает название кинопроизведения."""
        return self.title

    class Meta:
        """Метаданные модели кинопроизведения."""
        managed = False
        db_table = 'content"."film_work'
        verbose_name = _("film")
        verbose_name_plural = _("films")
        ordering = (
            "-creation_date",
            "title",
        )


class GenreFilmWork(UUIDMixin):
    """Связь кинопроизведения с жанром."""
    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        related_name="film_work_links",
        verbose_name=_("genre"),
    )
    film_work = models.ForeignKey(
        FilmWork,
        on_delete=models.CASCADE,
        related_name="genre_links",
        verbose_name=_("film"),
    )
    created = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )

    def __str__(self) -> str:
        """Возвращает текстовое представление связи."""
        return f"{self.film_work} — {self.genre}"

    class Meta:
        """Метаданные связи фильма и жанра."""
        managed = False
        db_table = 'content"."genre_film_work'
        verbose_name = _("film genre")
        verbose_name_plural = _("film genres")
        unique_together = (
            (
                "film_work",
                "genre",
            ),
        )


class Roles(models.TextChoices):
    """Роли персоны в создании кинопроизведения."""
    ACTOR = "actor", _("actor")
    DIRECTOR = "director", _("director")
    WRITER = "writer", _("writer")


class PersonFilmWork(UUIDMixin):
    """Связь кинопроизведения с персоной и её ролью."""
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="film_work_links",
        verbose_name=_("person"),
    )
    film_work = models.ForeignKey(
        FilmWork,
        on_delete=models.CASCADE,
        related_name="person_links",
        verbose_name=_("film"),
    )
    role = models.CharField(
        _("role"),
        max_length=10,
        choices=Roles.choices,
        default=Roles.ACTOR,
    )
    created = models.DateTimeField(
        auto_now_add=True,
        null=True,
    )

    def __str__(self) -> str:
        """Возвращает текстовое представление связи."""
        return (
            f"{self.film_work} — "
            f"{self.person} ({self.get_role_display()})"
        )

    class Meta:
        """Метаданные связи фильма и персоны."""
        managed = False
        db_table = 'content"."person_film_work'
        verbose_name = _("film person")
        verbose_name_plural = _("film persons")
        unique_together = (
            (
                "film_work",
                "person",
                "role",
            ),
        )
