import pandas as pd
import numpy as np
import joblib
from config.paths_config import *

############# 1. GET_ANIME_FRAME

def getAnimeFrame(anime, path_df):
    df = pd.read_csv(path_df)
    df["eng_version"] = df["eng_version"].astype(str).str.strip().str.lower()

    if isinstance(anime, int):
        return df[df.anime_id == anime]
    if isinstance(anime, str):
        anime = anime.strip().lower()
        result = df[df.eng_version == anime]
        if result.empty:
            print(f"Anime '{anime}' not found in dataset.")
        return result
    return pd.DataFrame()


########## 2. GET_SYNOPSIS

def getSynopsis(anime, path_synopsis_df):
    synopsis_df = pd.read_csv(path_synopsis_df)
    synopsis_df["Name"] = synopsis_df["Name"].astype(str).str.strip().str.lower()

    if isinstance(anime, int):
        return synopsis_df[synopsis_df.MAL_ID == anime].sypnopsis.values[0]
    if isinstance(anime, str):
        anime = anime.strip().lower()
        return synopsis_df[synopsis_df.Name == anime].sypnopsis.values[0]


########## 3. CONTENT RECOMMENDATION

def find_similar_animes(name, path_anime_weights, path_anime2anime_encoded, path_anime2anime_decoded, path_anime_df, n=10, return_dist=False, neg=False):
    anime_weights = joblib.load(path_anime_weights)
    anime2anime_encoded = joblib.load(path_anime2anime_encoded)
    anime2anime_decoded = joblib.load(path_anime2anime_decoded)

    anime_row = getAnimeFrame(name, path_anime_df)
    if anime_row.empty:
        return pd.DataFrame()

    index = anime_row.anime_id.values[0]
    encoded_index = anime2anime_encoded.get(index)

    if encoded_index is None:
        print(f"Encoded index not found for anime ID: {index}")
        return pd.DataFrame()

    dists = np.dot(anime_weights, anime_weights[encoded_index])
    sorted_dists = np.argsort(dists)
    n = n + 1
    closest = sorted_dists[:n] if neg else sorted_dists[-n:]

    if return_dist:
        return dists, closest

    SimilarityArr = []
    for close in closest:
        decoded_id = anime2anime_decoded.get(close)
        anime_frame = getAnimeFrame(decoded_id, path_anime_df)
        if anime_frame.empty:
            continue
        anime_name = anime_frame.eng_version.values[0]
        genre = anime_frame.Genres.values[0]
        similarity = dists[close]

        SimilarityArr.append({
            "anime_id": decoded_id,
            "name": anime_name,
            "similarity": similarity,
            "genre": genre,
        })

    Frame = pd.DataFrame(SimilarityArr).sort_values(by="similarity", ascending=False)
    return Frame[Frame.anime_id != index].drop(['anime_id'], axis=1)


######## 4. FIND_SIMILAR_USERS

def find_similar_users(item_input, path_user_weights, path_user2user_encoded, path_user2user_decoded, n=10, return_dist=False, neg=False):
    try:
        user_weights = joblib.load(path_user_weights)
        user2user_encoded = joblib.load(path_user2user_encoded)
        user2user_decoded = joblib.load(path_user2user_decoded)

        encoded_index = user2user_encoded.get(item_input)
        if encoded_index is None:
            print(f"User ID {item_input} not found in encoded dictionary.")
            return pd.DataFrame()

        dists = np.dot(user_weights, user_weights[encoded_index])
        sorted_dists = np.argsort(dists)
        n = n + 1
        closest = sorted_dists[:n] if neg else sorted_dists[-n:]

        if return_dist:
            return dists, closest

        SimilarityArr = []
        for close in closest:
            similarity = dists[close]
            decoded_id = user2user_decoded.get(close)
            if decoded_id != item_input:
                SimilarityArr.append({"similar_users": decoded_id, "similarity": similarity})

        return pd.DataFrame(SimilarityArr).sort_values(by="similarity", ascending=False)

    except Exception as e:
        print("Error Occurred", e)
        return pd.DataFrame()


################## 5. GET USER PREF

def get_user_preferences(user_id, path_rating_df, path_anime_df):
    rating_df = pd.read_csv(path_rating_df)
    df = pd.read_csv(path_anime_df)

    animes_watched_by_user = rating_df[rating_df.user_id == user_id]
    if animes_watched_by_user.empty:
        return pd.DataFrame()

    user_rating_percentile = np.percentile(animes_watched_by_user.rating, 75)
    animes_watched_by_user = animes_watched_by_user[animes_watched_by_user.rating >= user_rating_percentile]
    top_animes_user = animes_watched_by_user.sort_values(by="rating", ascending=False).anime_id.values

    anime_df_rows = df[df["anime_id"].isin(top_animes_user)][["eng_version", "Genres"]]
    return anime_df_rows


######## 6. USER RECOMMENDATION

def get_user_recommendations(similar_users, user_pref, path_anime_df, path_synopsis_df, path_rating_df, n=10):
    recommended_animes = []
    anime_list = []

    for user_id in similar_users.similar_users.values:
        pref_list = get_user_preferences(int(user_id), path_rating_df, path_anime_df)
        pref_list = pref_list[~pref_list.eng_version.isin(user_pref.eng_version.values)]

        if not pref_list.empty:
            anime_list.append(pref_list.eng_version.values)

    if anime_list:
        anime_list = pd.DataFrame(anime_list)
        sorted_list = pd.DataFrame(pd.Series(anime_list.values.ravel()).value_counts()).head(n)

        for anime_name in sorted_list.index:
            n_user_pref = sorted_list.loc[anime_name].values[0]
            frame = getAnimeFrame(anime_name, path_anime_df)
            if frame.empty:
                continue
            anime_id = frame.anime_id.values[0]
            genre = frame.Genres.values[0]
            synopsis = getSynopsis(int(anime_id), path_synopsis_df)

            recommended_animes.append({
                "n": n_user_pref,
                "anime_name": anime_name,
                "Genres": genre,
                "Synopsis": synopsis
            })

    return pd.DataFrame(recommended_animes).head(n)
