from config.paths_config import *
from utils.helpers import *

def hybrid_recommendation_by_anime(anime_name, content_weight=1.0):
    """
    Generate hybrid recommendations based on a given anime name using content-based logic.

    Parameters:
        anime_name (str): The title of the anime to base recommendations on.
        content_weight (float): Weighting factor (kept for compatibility, only content is used).

    Returns:
        list: Top 10 recommended anime names.
    """
    try:
        # Get similar animes using content-based filtering
        similar_animes_df = find_similar_animes(
            anime_name,
            ANIME_WEIGHTS_PATH,
            ANIME2ANIME_ENCODED,
            ANIME2ANIME_DECODED,
            DF,
            return_dist=False
        )

        if similar_animes_df is None or similar_animes_df.empty:
            print(f"No similar animes found for {anime_name}")
            return []

        return similar_animes_df["name"].tolist()[:10]

    except Exception as e:
        print(f"Error in hybrid_recommendation_by_anime: {e}")
        return []
