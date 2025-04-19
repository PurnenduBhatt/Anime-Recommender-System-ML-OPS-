from flask import Flask, render_template, request
from pipeline.prediction_pipeline import hybrid_recommendation_by_anime  # use updated function

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    recommendations = None
    anime_name = ""

    if request.method == 'POST':
        try:
            anime_name = request.form["animeName"]
            recommendations = hybrid_recommendation_by_anime(anime_name)
        except Exception as e:
            print(f"Error occurred: {e}")

    return render_template('index.html', recommendations=recommendations, anime_name=anime_name)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
