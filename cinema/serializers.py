from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order, Ticket


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class CinemaHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieListSerializer(MovieSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )


class MovieDetailSerializer(MovieSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class MovieSessionListSerializer(MovieSessionSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity", read_only=True
    )

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "cinema_hall_name",
            "cinema_hall_capacity",
        )


class MovieSessionDetailSerializer(MovieSessionSerializer):
    movie = MovieListSerializer(many=False, read_only=True)
    cinema_hall = CinemaHallSerializer(many=False, read_only=True)

    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = (
            "id",
            "row",
            "seat",
            "movie_session",
        )


class TicketMovieListSerializer(TicketSerializer):
    movie_session = MovieSessionListSerializer(read_only=True)
    class Meta:
        model = Ticket
        fields = (
            "id",
            "row",
            "seat",
            "movie_session",
        )


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'id',
            'tickets',
            'created_at',
        )

    def create(self, validated_data):
        tickets_data = validated_data.pop("tickets")
        user = self.context["request"].user

        with transaction.atomic():
            # Create the order
            order = Order.objects.create(user=user)

            for ticket_data in tickets_data:
                # Get the movie_session ID from the ticket data
                movie_session_id = ticket_data.pop("movie_session")

                # Retrieve the MovieSession instance
                try:
                    movie_session = MovieSession.objects.get(id=movie_session_id)
                except MovieSession.DoesNotExist:
                    raise serializers.ValidationError(
                        {"movie_session": f"MovieSession with ID {movie_session_id} does not exist."}
                    )

                # Create the ticket using the primary key for movie_session
                Ticket.objects.create(
                    order=order,
                    movie_session=movie_session,
                    **ticket_data
                )

            return order


class OrderListSerializer(serializers.ModelSerializer):
    tickets = TicketMovieListSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = (
            'id',
            'tickets',
            'created_at',
        )