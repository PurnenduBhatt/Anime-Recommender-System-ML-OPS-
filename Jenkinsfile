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

        stage('Vault') {
            steps {
                script {
                    sh '''
                        # Remove existing Vault container if it exists
                        if docker ps -a --format '{{.Names}}' | grep -q "^vault$"; then
                            docker rm -f vault
                        fi

                        # Download Vault CLI for macOS and set permissions
                        mkdir -p /tmp/vault-cli
                        curl -fsSL https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_darwin_amd64.zip -o /tmp/vault-cli/vault.zip
                        unzip -o /tmp/vault-cli/vault.zip -d /tmp/vault-cli
                        mv -f /tmp/vault-cli/vault ${WORKSPACE}/vault-cli
                        chmod +x ${WORKSPACE}/vault-cli

                        # Start Vault server in dev mode
                        docker run -d --name vault -p 8200:8200 --cap-add=IPC_LOCK \
                            -e 'VAULT_DEV_ROOT_TOKEN_ID=root' \
                            -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
                            hashicorp/vault

                        # Wait for Vault to be ready
                        sleep 10

                        export VAULT_ADDR=http://127.0.0.1:8200
                        export VAULT_TOKEN=root

                        # Test Vault connection
                        echo "Testing Vault connection..."
                        ${WORKSPACE}/vault-cli status

                        # In dev mode, the KV v2 secrets engine is already enabled at secret/
                        # So we directly add our credentials using KV v2 syntax
                        echo "Adding Docker Hub credentials to Vault..."
                        ${WORKSPACE}/vault-cli kv put secret/mlopsproject username=kunal2221 password=Docker123

                        # Verify the secret was stored
                        echo "Verifying stored credentials..."
                        ${WORKSPACE}/vault-cli kv get secret/mlopsproject
                    '''
                }
            }
        }

        stage('Push to Docker Hub using Vault Credentials') {
            steps {
                script {
                    echo '🚀 Pushing Docker image using credentials from Vault...'
                    sh '''
                    # Set Vault environment using working root token
                    export VAULT_ADDR=http://localhost:8200
                    export VAULT_TOKEN=root

                    # Retrieve Docker Hub credentials from Vault
                    DOCKER_USERNAME=$(${WORKSPACE}/vault-cli kv get -field=username secret/mlopsproject)
                    DOCKER_PASSWORD=$(${WORKSPACE}/vault-cli kv get -field=password secret/mlopsproject)

                    # Docker login
                    echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin

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
                    # First, let's check current cluster status
                    echo "=== Kubernetes Cluster Status ==="
                    kubectl cluster-info
                    kubectl get nodes
                    
                    # Check existing deployment status
                    echo "=== Current Deployment Status ==="
                    kubectl get deployments -o wide || echo "No deployments found"
                    kubectl get pods -o wide || echo "No pods found"
                    
                    # Apply the deployment configuration
                    echo "=== Applying Deployment Configuration ==="
                    kubectl apply -f deployment.yaml
                    
                    # Update the image
                    echo "=== Updating Container Image ==="
                    kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                    
                    # Wait a bit for pods to start being created
                    echo "=== Waiting for pods to be created ==="
                    sleep 30
                    
                    # Monitor pod creation and status in real-time
                    echo "=== Monitoring Pod Status ==="
                    for i in {1..20}; do
                        echo "--- Check $i/20 ---"
                        kubectl get pods -l app=ml-app -o wide
                        kubectl get rs -l app=ml-app -o wide
                        
                        # Get all events related to our app
                        echo "--- Recent Events ---"
                        kubectl get events --field-selector involvedObject.name!=ml-app --sort-by=.metadata.creationTimestamp | grep ml-app | tail -10 || echo "No ml-app events found"
                        
                        # Check if any pods exist and get their details
                        PODS=$(kubectl get pods -l app=ml-app -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
                        if [ ! -z "$PODS" ]; then
                            for pod in $PODS; do
                                echo "--- Pod $pod Status ---"
                                kubectl get pod $pod -o yaml | grep -A 5 -B 5 "phase\\|containerStatuses\\|conditions" || true
                                
                                echo "--- Pod $pod Events ---"
                                kubectl describe pod $pod | grep -A 20 "Events:" || echo "No events for $pod"
                                
                                echo "--- Pod $pod Logs (if available) ---"
                                kubectl logs $pod --previous 2>/dev/null || kubectl logs $pod 2>/dev/null || echo "No logs available for $pod"
                            done
                        else
                            echo "No pods found with label app=ml-app"
                        fi
                        
                        sleep 15
                    done
                    
                    # Final attempt to wait for rollout
                    echo "=== Final Rollout Status Check ==="
                    kubectl rollout status deployment/ml-app --timeout=60s || {
                        echo "❌ Final deployment check failed. Getting comprehensive diagnostics..."
                        
                        echo "=== All Resources ==="
                        kubectl get all -l app=ml-app -o wide
                        
                        echo "=== Deployment Description ==="
                        kubectl describe deployment ml-app
                        
                        echo "=== ReplicaSet Description ==="
                        kubectl describe rs -l app=ml-app
                        
                        echo "=== All Events (Last 50) ==="
                        kubectl get events --sort-by=.metadata.creationTimestamp | tail -50
                        
                        echo "=== Node Resources ==="
                        kubectl describe nodes | grep -A 5 -B 5 "Allocated resources"
                        
                        echo "=== Checking if image exists and is pullable ==="
                        docker pull ${DOCKER_IMAGE}:${DOCKER_TAG} || echo "Image pull failed - this might be the issue"
                        
                        # Try to rollback
                        echo "=== Attempting Rollback ==="
                        kubectl rollout undo deployment/ml-app || echo "Rollback failed or no previous revision"
                        
                        exit 1
                    }
                    
                    echo "=== Deployment Successful ==="
                    kubectl get pods -l app=ml-app -o wide
                    kubectl get services
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
                
                # Collect Kubernetes logs if deployment exists
                echo "=== Collecting Kubernetes Deployment Information ==="
                kubectl get all -l app=ml-app > logs/k8s-status.log 2>&1 || echo "Could not collect k8s status"
                kubectl describe deployment ml-app > logs/k8s-deployment.log 2>&1 || echo "Could not describe deployment"
                '''
                archiveArtifacts artifacts: 'coverage.xml, **/ml-app.log, **/k8s-*.log', allowEmptyArchive: true
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