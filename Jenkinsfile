pipeline {
    agent any

    environment {
        VENV_DIR = 'venv'
        GCP_PROJECT = 'academic-volt-456808-r1'
        DOCKER_IMAGE = "kunal2221/mlops-app"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        VAULT_ADDR = "http://localhost:8200"
        VAULT_TOKEN = "myroot"  // Only for development, use Jenkins credentials in production
        PATH = "${env.HOME}/.pyenv/shims:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
    }

    parameters {
        booleanParam(name: 'RUN_TESTS', defaultValue: true, description: 'Run automated tests')
        booleanParam(name: 'DEPLOY_TO_PRODUCTION', defaultValue: false, description: 'Deploy to production environment')
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    stages {
        stage("Clean Workspace") {
            steps {
                cleanWs()
                echo 'Workspace cleaned successfully'
            }
        }

        stage("Setup Environment") {
            steps {
                script {
                    echo 'Validating Docker Desktop setup...'

                    sh '''
                    echo "PATH: $PATH"
                    echo "Docker version:"
                    if ! command -v docker &> /dev/null; then
                        echo "❌ Docker command not found. Please ensure Docker Desktop is installed and running."
                        exit 1
                    fi

                    docker info > /dev/null 2>&1
                    if [ $? -ne 0 ]; then
                        echo "❌ Docker is installed but not responsive. Is Docker Desktop running?"
                        exit 1
                    fi

                    echo "✅ Docker is installed and responsive."
                    '''
                }
            }
        }

        stage("Cloning from Github") {
            steps {
                script {
                    echo 'Cloning from Github...'
                    checkout scmGit(branches: [[name: '*/main']],
                             extensions: [],
                             userRemoteConfigs: [[credentialsId: 'github-token',
                             url: 'https://github.com/PurnenduBhatt/Anime-Recommender-System-ML-OPS-.git']])
                    echo 'Repository cloned successfully'
                }
            }
        }

stage("Creating Virtual Environment") {
            steps {
                script {
                    echo 'Creating virtual environment...'
                    sh '''
                    if ! command -v python3.10 &> /dev/null; then
                        echo "❌ Python 3.10 is not installed or not in PATH."
                        exit 1
                    fi

                    python3.10 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip

                    # Install base project dependencies first
                    pip install -e .
                    pip install tensorflow==2.16.2 || pip install tensorflow

                    # Explicitly install/upgrade DVC and its GCS-related dependencies.
                    echo "Attempting to install/upgrade DVC and GCS dependencies with specific gcsfs version..."
                    # Pin gcsfs to a known stable version
                    pip install --upgrade dvc dvc-gs "gcsfs==2024.5.0" google-cloud-storage google-auth-oauthlib
                    
                    pip install pytest pytest-cov flake8
                    '''
                }
            }
        }
        // --- NEW STAGE TO VERIFY PACKAGE VERSIONS ---
        stage("Verify Package Versions") {
            steps {
                script {
                    echo "--- START DVC/GCS Package Versions ---"
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    pip show dvc || echo "dvc not found"
                    pip show dvc-gs || echo "dvc-gs not found"
                    pip show gcsfs || echo "gcsfs not found"
                    pip show google-cloud-storage || echo "google-cloud-storage not found"
                    pip show google-auth-oauthlib || echo "google-auth-oauthlib not found"
                    '''
                    echo "--- END DVC/GCS Package Versions ---"
                }
            }
        }
        // --- END NEW STAGE ---

        stage('Static Code Analysis') {
            steps {
                script {
                    echo 'Running flake8...'
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "Flake8 issues detected"
                    '''
                }
            }
        }

        stage('DVC Pull') {
            steps {
                script {
                    def credExists = false
                    try {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            credExists = true
                        }
                    } catch (e) {
                        echo "⚠️ GCP credentials not found, skipping DVC pull."
                    }
                    if (credExists) {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            sh '''
                            . ${VENV_DIR}/bin/activate
                            echo "Attempting DVC pull with environment variable GOOGLE_APPLICATION_CREDENTIALS set to: ****"
                            dvc pull || {
                                echo "DVC pull failed with an error."
                                exit 1 # Fail the stage if DVC pull fails
                            }
                            echo "DVC pull completed successfully."
                            '''
                        }
                    }
                }
            }
        }

        stage('Run Tests') {
            when {
                expression { return params.RUN_TESTS }
            }
            steps {
                script {
                    echo 'Running tests...'
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    mkdir -p test-results
                    python tester.py || echo "Some tests failed"
                    '''
                }
            }
        }
        
        stage("Clean Old Docker Images & Containers") {
            steps {
                script {
                    echo '🧹 Cleaning up old Docker containers and images...'
                    sh '''
                    # Stop and remove all containers
                    docker container prune -f

                    # Remove dangling (untagged) images and old versions of the app
                    docker images --filter "reference=${DOCKER_IMAGE}" --format "{{.Repository}}:{{.Tag}}" | grep -v ":${BUILD_NUMBER}" | xargs -r docker rmi -f

                    # Also remove dangling images
                    docker image prune -f
                    '''
                }
            }
        }
        
        stage("Clean Old ELK Volumes") {
            steps {
                script {
                    echo '🧹 Cleaning up old ELK-related Docker volumes...'
                    sh '''
                    # Remove volumes related to ELK stack
                    docker volume ls --format "{{.Name}}" | grep -i "elk\\|logstash\\|kibana" | xargs -r docker volume rm -f

                    # Optionally remove unused volumes
                    docker volume prune -f
                    '''
                }
            }
        }
        
        stage('Cleanup Docker Artifacts') {
            steps {
                script {
                    echo '🧹 Removing old Docker images, volumes, and networks...'
                    sh '''
                    docker image prune -af || true
                    docker container prune -f || true
                    docker volume prune -f || true
                    docker network prune -f || true
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Building Docker image...'
                    sh '''
                    docker build -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:${DOCKER_TAG} . || exit 1
                    '''
                }
            }
        }

        stage('Start ELK and Vault Stack') {
            steps {
                script {
                    echo '📦 Starting ELK + Vault stack via Docker Compose...'
                    sh '''
                    # Stop and remove any pre-existing 'vault' container to prevent "Conflict" errors
                    docker rm -f vault || true
                    
                    docker-compose down || true
                    docker-compose up -d
                    sleep 30  # Wait for containers to be ready
                    '''
                }
            }
        }

        stage('Initialize Vault with Docker Credentials') {
            steps {
                script {
                    echo '🔐 Setting up Vault with Docker Hub credentials...'
                    // We'll use the Jenkins credentials one last time to set up Vault
                    withCredentials([usernamePassword(credentialsId: 'dockerhub', passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                        sh '''
                        # Install vault CLI if needed
                        if ! command -v vault &> /dev/null; then
                            echo "Installing Vault CLI..."
                            # Note: Hardcoding version 1.15.0 - ensure it's compatible or adjust
                            
                            # Add this line to forcefully remove any existing vault executable
                            sudo rm -f /usr/local/bin/vault || true
                            
                            curl -fsSL https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip -o vault.zip
                            unzip -o vault.zip
                            sudo mv vault /usr/local/bin/  # Use sudo for mv as well
                            rm vault.zip
                        fi
                        
                        # Configure Vault client
                        export VAULT_ADDR=${VAULT_ADDR}
                        export VAULT_TOKEN=${VAULT_TOKEN}
                        
                        # Enable key-value secrets engine if not already enabled
                        vault secrets enable -path=secret kv || echo "KV secrets engine already enabled"
                        
                        # Store Docker Hub credentials in Vault
                        vault kv put secret/dockerhub username=${DOCKER_USERNAME} password=${DOCKER_PASSWORD}
                        
                        echo "✅ Docker Hub credentials stored in Vault"
                        '''
                    }
                }
            }
        }

        stage('Push to Docker Hub using Vault Credentials') {
            steps {
                script {
                    echo '🚀 Pushing Docker image using credentials from Vault...'
                    sh '''
                    # Configure Vault client
                    export VAULT_ADDR=${VAULT_ADDR}
                    export VAULT_TOKEN=${VAULT_TOKEN}
                    
                    # Retrieve Docker Hub credentials from Vault
                    DOCKER_USERNAME=$(vault kv get -field=username secret/dockerhub)
                    DOCKER_PASSWORD=$(vault kv get -field=password secret/dockerhub)
                    
                    # Login to Docker Hub
                    echo ${DOCKER_PASSWORD} | docker login -u ${DOCKER_USERNAME} --password-stdin
                    
                    # Push Docker images
                    docker push ${DOCKER_IMAGE}:latest
                    docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                    '''
                }
            }
        }
        
        stage('Deploy to Development') {
            steps {
                script {
                    echo '🚀 Deploying to local Kubernetes using deployment.yaml...'
                    sh '''
                    kubectl apply -f deployment.yaml
                    kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                    kubectl rollout status deployment/ml-app
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                echo 'Cleaning up...'
                sh '''
                touch coverage.xml || true
                mkdir -p logs
                touch logs/ml-app.log || true
                '''
                archiveArtifacts artifacts: 'coverage.xml, **/ml-app.log', allowEmptyArchive: true
            }
            cleanWs()
        }
        success {
            echo '✅ Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed!'
        }
    }
}