import hvac
import logging
import os
import stat
from flask import Flask, render_template, request
from pipeline.prediction_pipeline import hybrid_recommendation_by_anime
from datetime import datetime
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

# Set up logs directory
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ml-app.log")

# Ensure log file is writable by all
try:
    if not os.path.exists(log_file):
        open(log_file, 'a').close()
    os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # 666 permissions
except Exception as e:
    print(f"Failed to set permissions for log file: {str(e)}")

# Configure JSON logger
log_handler = logging.FileHandler(log_file)
formatter = jsonlogger.JsonFormatter(
    fmt='%(asctime)s %(levelname)s %(message)s %(remote_addr)s %(method)s %(path)s %(payload)s',
    datefmt='%Y-%m-%dT%H:%M:%S.000Z',  # ISO 8601 format
    rename_fields={"asctime": "asctime", "levelname": "levelname", "message": "message"}
)
log_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Log startup
logger.info("Application starting", extra={"remote_addr": None, "method": None, "path": None, "payload": None})

# Initialize Vault client
vault_client = None
try:
    vault_client = hvac.Client(url='http://vault:8200', token=os.getenv('VAULT_TOKEN', 'myroot'))
    logger.info("Successfully initialized Vault client", extra={"remote_addr": None, "method": None, "path": None, "payload": None})
except Exception as e:
    logger.error(f"Failed to initialize Vault client: {str(e)}", extra={"remote_addr": None, "method": None, "path": None, "payload": None})

# Fetch Elasticsearch credentials
elastic_user = os.getenv('ELASTIC_USER', 'elastic')
elastic_password = os.getenv('ELASTIC_PASSWORD', 'changeme')
try:
    if vault_client and vault_client.is_authenticated():
        secret = vault_client.secrets.kv.read_secret_version(path='ml-app/elasticsearch')
        elastic_user = secret['data']['data']['user']
        elastic_password = secret['data']['data']['password']
        logger.info("Fetched Elasticsearch credentials from Vault", extra={"remote_addr": None, "method": None, "path": None, "payload": None})
    else:
        logger.warning("Vault not authenticated; using default or environment credentials", extra={"remote_addr": None, "method": None, "path": None, "payload": None})
except Exception as e:
    logger.error(f"Error fetching credentials from Vault: {str(e)}", extra={"remote_addr": None, "method": None, "path": None, "payload": None})

# Log request info
@app.before_request
def log_request_info():
    logger.info(
        "Request received",
        extra={
            "remote_addr": request.remote_addr,
            "method": request.method,
            "path": request.path,
            "payload": request.get_data(as_text=True) if request.method == 'POST' else None
        }
    )

# Main route
@app.route('/', methods=['GET', 'POST'])
def home():
    recommendations = None
    anime_name = ""

    if request.method == 'POST':
        try:
            anime_name = request.form["animeName"]
            logger.info(f"Recommendation request for anime: {anime_name}", extra={"remote_addr": request.remote_addr, "method": request.method, "path": request.path, "payload": request.get_data(as_text=True)})
            recommendations = hybrid_recommendation_by_anime(anime_name)
            logger.info(f"Generated recommendations for anime: {anime_name}", extra={"remote_addr": request.remote_addr, "method": request.method, "path": request.path, "payload": None})
        except Exception as e:
            error_message = f"Error generating recommendations for '{anime_name}': {str(e)}"
            logger.error(error_message, extra={"remote_addr": request.remote_addr, "method": request.method, "path": request.path, "payload": None})
            recommendations = None

    return render_template('index.html', recommendations=recommendations, anime_name=anime_name)

# Health check
@app.route('/health')
def health():
    logger.debug("Health check endpoint hit", extra={"remote_addr": request.remote_addr, "method": request.method, "path": request.path, "payload": None})
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)