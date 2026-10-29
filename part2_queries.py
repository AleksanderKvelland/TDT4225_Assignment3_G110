import inspect
import sys
from collections import defaultdict
from itertools import combinations
from pprint import pprint

from DbConnector import DbConnector

TASKS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


class QueryProgram:

    def __init__(self):
        self.connection = DbConnector()
        self.client = self.connection.client
        self.db = self.connection.db
        self.movies = self.db["movies"]
        self.ratings = self.db["ratings"]
        self._movie_genres_by_id = None

    def movie_genres_by_id(self):
        """TMDB movie id -> list of genre names (used by task 10)."""
        if self._movie_genres_by_id is None:
            self._movie_genres_by_id = {}
            for doc in self.movies.find({}, {"genres.name": 1}):
                self._movie_genres_by_id[doc["_id"]] = [
                    genre["name"] for genre in doc.get("genres", [])
                ]
        return self._movie_genres_by_id

    def print_result(self, result, n_docs=20):
        """Pretty-print aggregation/cursor results (first n_docs) and return the full list."""
        docs = list(result)
        for doc in docs[:n_docs]:
            pprint(doc)
        if len(docs) > n_docs:
            print("(%d docs, showing the first %d)" % (len(docs), n_docs))
        elif len(docs) == 0:
            print("(no results)")

        return docs

    def task_1(self):
        """
        Considering only crew with job = Director, which 10 directors with >= 5
        movies have the highest median revenue? Also report each director's movie
        count and mean vote_average.
        """
        pipeline = [
            {"$unwind": "$crew"},
            {"$match": {"crew.job": "Director"}},
            {"$group": {
                "_id": {"id": "$crew.id", "name": "$crew.name"},
                "movie_count": {"$sum": 1},
                "median_revenue": {
                    "$median": {"input": "$revenue", "method": "approximate"},
                },
                "mean_vote_average": {"$avg": "$vote_average"},
            }},
            {"$match": {"movie_count": {"$gte": 5}, "median_revenue": {"$ne": None}}},
            {"$sort": {"median_revenue": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "director": "$_id.name",
                "director_id": "$_id.id",
                "movie_count": 1,
                "median_revenue": 1,
                "mean_vote_average": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=10)

    def task_2(self):
        """
        List actor pairs that have co-starred in >= 3 movies together, their number
        of co-appearances, and their average movie vote_average. Sort by number of
        co-appearances.
        """
        pair_counts = defaultdict(int)
        pair_votes = defaultdict(list)
        pair_names = {}

        cursor = self.movies.find(
            {"cast.1": {"$exists": True}},
            {"cast.id": 1, "cast.name": 1, "vote_average": 1},
        )
        for movie in cursor:
            actors = {
                person["id"]: person["name"]
                for person in movie.get("cast", [])
                if "id" in person
            }
            vote = movie.get("vote_average")
            for id_a, id_b in combinations(sorted(actors.keys()), 2):
                pair = (id_a, id_b)
                pair_counts[pair] += 1
                if pair not in pair_names:
                    pair_names[pair] = (actors[id_a], actors[id_b])
                if vote is not None:
                    pair_votes[pair].append(vote)

        results = []
        for pair, count in pair_counts.items():
            if count < 3:
                continue
            name_a, name_b = pair_names[pair]
            votes = pair_votes[pair]
            avg_vote = sum(votes) / len(votes) if votes else None
            results.append({
                "actor_a": name_a,
                "actor_b": name_b,
                "co_appearances": count,
                "avg_vote_average": avg_vote,
            })

        results.sort(key=lambda row: row["co_appearances"], reverse=True)
        self.print_result(results, n_docs=20)

    def task_3(self):
        """
        List the top 10 actors (with >= 10 credited movies) that have the widest
        genre breadth. Report the actor, the number of distinct genres they've
        appeared in, and up to 5 example genres.
        """
        pipeline = [
            {"$unwind": "$cast"},
            {"$group": {
                "_id": {"id": "$cast.id", "name": "$cast.name"},
                "movie_ids": {"$addToSet": "$_id"},
                "genre_lists": {"$push": "$genres.name"},
            }},
            {"$match": {"$expr": {"$gte": [{"$size": "$movie_ids"}, 10]}}},
            {"$addFields": {
                "distinct_genres": {
                    "$reduce": {
                        "input": "$genre_lists",
                        "initialValue": [],
                        "in": {"$setUnion": ["$$value", "$$this"]},
                    }
                },
            }},
            {"$addFields": {
                "movie_count": {"$size": "$movie_ids"},
                "genre_count": {"$size": "$distinct_genres"},
            }},
            {"$sort": {"genre_count": -1, "movie_count": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "actor": "$_id.name",
                "actor_id": "$_id.id",
                "movie_count": 1,
                "genre_count": 1,
                "example_genres": {"$slice": ["$distinct_genres", 5]},
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=10)

    def task_4(self):
        """
        For film collections (belongs_to_collection.name not null) with >= 3 movies,
        which 10 collections have the largest total revenue? For each, report movie
        count, total revenue, median vote_average, and the earliest -> latest
        release date.
        """
        pipeline = [
            {"$match": {"belongs_to_collection.name": {"$exists": True}}},
            {"$group": {
                "_id": "$belongs_to_collection.name",
                "movie_count": {"$sum": 1},
                "total_revenue": {"$sum": "$revenue"},
                "median_vote_average": {
                    "$median": {"input": "$vote_average", "method": "approximate"},
                },
                "earliest_release": {"$min": "$release_date"},
                "latest_release": {"$max": "$release_date"},
            }},
            {"$match": {"movie_count": {"$gte": 3}}},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "collection": "$_id",
                "movie_count": 1,
                "total_revenue": 1,
                "median_vote_average": 1,
                "earliest_release": 1,
                "latest_release": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=10)

    def task_5(self):
        """
        By decade (e.g., 1970s, 1980s, …) and primary genre (first element in
        genres), what is the median runtime and movie count? List results sorted
        by decade then median runtime (desc).
        """
        pipeline = [
            {"$match": {
                "release_date": {"$exists": True},
                "runtime": {"$exists": True},
                "genres.0": {"$exists": True},
            }},
            {"$group": {
                "_id": {
                    "decade": {
                        "$multiply": [
                            {"$floor": {"$divide": [{"$year": "$release_date"}, 10]}},
                            10,
                        ]
                    },
                    "primary_genre": {"$arrayElemAt": ["$genres.name", 0]},
                },
                "median_runtime": {
                    "$median": {"input": "$runtime", "method": "approximate"},
                },
                "movie_count": {"$sum": 1},
            }},
            {"$sort": {"_id.decade": 1, "median_runtime": -1}},
            {"$project": {
                "_id": 0,
                "decade": "$_id.decade",
                "primary_genre": "$_id.primary_genre",
                "median_runtime": 1,
                "movie_count": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline))

    def task_6(self):
        """
        For each movie's top-billed 5 cast (by order), what is the proportion of
        female cast? Aggregate by decade and list decades sorted by average female
        proportion (desc), including movie counts used. Unknown gender may be
        ignored.
        """
        decade_stats = defaultdict(lambda: {"proportion_sum": 0.0, "movie_count": 0})
        cursor = self.movies.find(
            {"release_date": {"$exists": True}, "cast.0": {"$exists": True}},
            {"release_date": 1, "cast": 1},
        )
        for movie in cursor:
            top5 = movie["cast"][:5]
            with_gender = [
                person for person in top5
                if person.get("gender") in ("female", "male")
            ]
            if len(with_gender) == 0:
                continue
            female_count = sum(
                1 for person in with_gender if person.get("gender") == "female"
            )
            proportion = female_count / len(with_gender)
            decade = (movie["release_date"].year // 10) * 10
            decade_stats[decade]["proportion_sum"] += proportion
            decade_stats[decade]["movie_count"] += 1

        results = []
        for decade, stats in decade_stats.items():
            results.append({
                "decade": decade,
                "avg_female_proportion": stats["proportion_sum"] / stats["movie_count"],
                "movie_count": stats["movie_count"],
            })
        results.sort(key=lambda row: row["avg_female_proportion"], reverse=True)
        self.print_result(results)

    def task_7(self):
        """
        Using a text search over overview and tagline, which 20 movies matching
        "noir" or "neo-noir" (and vote_count >= 50) have the highest vote_average?
        Return title, year, vote_average, and vote_count.
        """
        pipeline = [
            {"$match": {
                "$text": {"$search": "noir"},
                "vote_count": {"$gte": 50},
            }},
            {"$sort": {"vote_average": -1}},
            {"$limit": 20},
            {"$project": {
                "_id": 0,
                "title": 1,
                "year": {"$year": "$release_date"},
                "vote_average": 1,
                "vote_count": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=20)

    def task_8(self):
        """
        Which 20 director-actor pairs with >= 3 collaborations (same movie) have
        the highest mean vote_average, considering only movies with vote_count >=
        100? Include the pair's films count and mean revenue.
        """
        pipeline = [
            {"$match": {"vote_count": {"$gte": 100}}},
            {"$unwind": "$crew"},
            {"$match": {"crew.job": "Director"}},
            {"$unwind": "$cast"},
            {"$group": {
                "_id": {
                    "movie_id": "$_id",
                    "director_id": "$crew.id",
                    "director_name": "$crew.name",
                    "actor_id": "$cast.id",
                    "actor_name": "$cast.name",
                },
                "vote_average": {"$first": "$vote_average"},
                "revenue": {"$first": "$revenue"},
            }},
            {"$group": {
                "_id": {
                    "director": {"id": "$_id.director_id", "name": "$_id.director_name"},
                    "actor": {"id": "$_id.actor_id", "name": "$_id.actor_name"},
                },
                "film_count": {"$sum": 1},
                "mean_vote_average": {"$avg": "$vote_average"},
                "mean_revenue": {"$avg": "$revenue"},
            }},
            {"$match": {"film_count": {"$gte": 3}}},
            {"$sort": {"mean_vote_average": -1}},
            {"$limit": 20},
            {"$project": {
                "_id": 0,
                "director": "$_id.director.name",
                "actor": "$_id.actor.name",
                "film_count": 1,
                "mean_vote_average": 1,
                "mean_revenue": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=20)

    def task_9(self):
        """
        Among movies where original_language != "en" but at least one production
        company or country is United States, which are the top 10 original
        languages by count? For each language, report the count and one example
        title.
        """
        pipeline = [
            {"$match": {
                "original_language": {"$exists": True, "$ne": "en"},
                "$or": [
                    {"production_countries.iso_3166_1": "US"},
                    {"production_countries.name": "United States of America"},
                ],
            }},
            {"$group": {
                "_id": "$original_language",
                "count": {"$sum": 1},
                "example_title": {"$first": "$title"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10},
            {"$project": {
                "_id": 0,
                "original_language": "$_id",
                "count": 1,
                "example_title": 1,
            }},
        ]
        self.print_result(self.movies.aggregate(pipeline), n_docs=10)

    def task_10(self):
        """
        For each user, what is their ratings count, population variance of
        ratings, and number of distinct genres rated? List the top 10 most
        genre-diverse users, and separately the top 10 highest-variance users
        (only users with >= 20 ratings).
        """
        movie_genres = self.movie_genres_by_id()
        user_stats = defaultdict(lambda: {"ratings": [], "genres": set()})

        for row in self.ratings.find({}, {"user_id": 1, "movie_id": 1, "rating": 1}):
            user_id = row["user_id"]
            user_stats[user_id]["ratings"].append(row["rating"])
            for genre in movie_genres.get(row["movie_id"], []):
                user_stats[user_id]["genres"].add(genre)

        users = []
        for user_id, stats in user_stats.items():
            ratings = stats["ratings"]
            if len(ratings) < 20:
                continue
            mean = sum(ratings) / len(ratings)
            variance = sum((rating - mean) ** 2 for rating in ratings) / len(ratings)
            users.append({
                "user_id": user_id,
                "ratings_count": len(ratings),
                "population_variance": variance,
                "genre_count": len(stats["genres"]),
            })

        by_genres = sorted(users, key=lambda row: row["genre_count"], reverse=True)[:10]
        by_variance = sorted(users, key=lambda row: row["population_variance"], reverse=True)[:10]

        print("Top 10 most genre-diverse users:")
        for row in by_genres:
            pprint(row)
        print("\nTop 10 highest-variance users:")
        for row in by_variance:
            pprint(row)


def main():
    tasks = sys.argv[1:] or TASKS
    unknown = [task for task in tasks if task not in TASKS]
    if unknown:
        sys.exit("Unknown task(s): %s. Choose from: %s" % (", ".join(unknown), " ".join(TASKS)))

    program = None
    try:
        program = QueryProgram()
        for task in tasks:
            method = getattr(program, "task_" + task)
            question = inspect.getdoc(method).split("\n\n")[0]
            print("\nTask %s: %s\n" % (task, question))
            try:
                method()
            except NotImplementedError:
                print("Not implemented yet")
    except Exception as e:
        print("ERROR: Failed to use database:", e)
    finally:
        if program:
            program.connection.close_connection()


if __name__ == "__main__":
    main()
