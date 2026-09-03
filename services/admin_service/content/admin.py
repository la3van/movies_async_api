"""Конфигурация моделей контента в Django Admin."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from content.models import (
    FilmWork,
    Genre,
    GenreFilmWork,
    Person,
    PersonFilmWork,
)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    """Настройки управления жанрами."""

    list_display = (
        "name",
        "created",
        "modified",
    )
    search_fields = (
        "name",
        "description",
    )
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
    ordering = ("name",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Настройки управления персонами."""

    list_display = (
        "full_name",
        "created",
        "modified",
    )
    search_fields = ("full_name",)
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
    ordering = ("full_name",)


class GenreFilmWorkInline(admin.TabularInline):
    """Inline-редактор жанров кинопроизведения."""

    model = GenreFilmWork
    autocomplete_fields = ("genre",)
    readonly_fields = (
        "id",
        "created",
    )
    extra = 0
    show_change_link = True


class PersonFilmWorkInline(admin.TabularInline):
    """Inline-редактор персон кинопроизведения."""

    model = PersonFilmWork
    autocomplete_fields = ("person",)
    readonly_fields = (
        "id",
        "created",
    )
    extra = 0
    show_change_link = True


@admin.register(FilmWork)
class FilmWorkAdmin(admin.ModelAdmin):
    """Настройки управления фильмами и сериалами."""

    inlines = (
        GenreFilmWorkInline,
        PersonFilmWorkInline,
    )
    list_display = (
        "title",
        "type",
        "creation_date",
        "rating",
        "get_genres",
        "modified",
    )
    list_filter = (
        "type",
        "genres",
        "creation_date",
    )
    search_fields = (
        "title",
        "description",
        "id",
    )
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
    ordering = (
        "-creation_date",
        "title",
    )
    date_hierarchy = "creation_date"
    save_on_top = True
    list_per_page = 50

    def get_queryset(
        self,
        request: HttpRequest,
    ) -> QuerySet[FilmWork]:
        """Добавляет предварительную загрузку жанров."""
        queryset = super().get_queryset(
            request,
        )

        return queryset.prefetch_related(
            "genres",
        )

    @admin.display(
        description=_("genres"),
    )
    def get_genres(
        self,
        film_work: FilmWork,
    ) -> str:
        """Возвращает жанры фильма одной строкой."""
        return ", ".join(genre.name for genre in film_work.genres.all())
