import hvac
import logging
import os
from flask import Flask, render_template, request
from pipeline.prediction_pipeline import hybrid_recommendation_by_anime

app = Flask(__name__)

# Setup logging to write to /app/logs in a format compatible with Logstash
log_dir = "/app/logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=os.path.join(log_dir, "ml-app.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"  # Matches Logstash grok filter
)
logger = logging.getLogger(__name__)

# Initialize Vault client to fetch credentials
try:
    vault_client = hvac.Client(url='http://vault:8200', token='myroot')
    logger.info("Successfully initialized Vault client")
except Exception as e:
    logger.error(f"Failed to initialize Vault client: {str(e)}")
    vault_client = None

# Fetch Elasticsearch credentials from Vault (used for logging/monitoring if needed)
try:
    if vault_client and vault_client.is_authenticated():
        secret = vault_client.secrets.kv.read_secret_version(path='ml-app/elasticsearch')
        elastic_user = secret['data']['data']['user']
        elastic_password = secret['data']['data']['password']
        logger.info("Successfully fetched Elasticsearch credentials from Vault")
    else:
        elastic_user = "elastic"
        elastic_password = "changeme"
        logger.warning("Vault client not initialized; using default Elasticsearch credentials")
except Exception as e:
    logger.error(f"Error fetching Elasticsearch credentials from Vault: {str(e)}")
    elastic_user = "elastic"
    elastic_password = "changeme"

@app.route('/', methods=['GET', 'POST'])
def home():
    recommendations = None
    anime_name = ""

    if request.method == 'POST':
        try:
            anime_name = request.form["animeName"]
            logger.info(f"Received recommendation request for anime: {anime_name}")
            recommendations = hybrid_recommendation_by_anime(anime_name)
            logger.info(f"Successfully generated recommendations for anime: {anime_name}")
        except Exception as e:
            error_message = f"Error occurred while generating recommendations for '{anime_name}': {str(e)}"
            logger.error(error_message)
            recommendations = None  # Ensure the template can handle this

    return render_template('index.html', recommendations=recommendations, anime_name=anime_name)

# ✅ Health check route (already suitable for Kubernetes liveness/readiness probe)
@app.route('/health')
def health():
    logger.debug("Health check endpoint called")
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)