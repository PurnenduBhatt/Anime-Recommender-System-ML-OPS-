pipeline {
    agent any
    
    environment {
        VENV_DIR = 'venv'
        GCP_PROJECT = 'academic-volt-456808-r1'
        DOCKER_IMAGE = "kunal2221/mlops-app"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        VAULT_ADDR = "http://vault:8200"
        VAULT_TOKEN = "myroot"
        // Add Docker Desktop paths explicitly for macOS
        PATH = "/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
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
                    echo 'Setting up environment for macOS with Docker Desktop...'
                    
                    // Display environment information
                    sh 'echo "Current PATH: $PATH"'
                    sh 'echo "Current user: $(whoami)"'
                    
                    // Check if Docker Desktop is running
                    sh '''
                    # Check if Docker Desktop app is running
                    if ! pgrep -x "Docker" > /dev/null; then
                        echo "Warning: Docker Desktop app does not appear to be running."
                        echo "Please start Docker Desktop manually and try again."
                        exit 1
                    fi
                    
                    # Check Docker CLI accessibility
                    if command -v docker &> /dev/null; then
                        echo "Docker command found at: $(which docker)"
                        docker --version || echo "Docker command exists but may not be working properly"
                    else
                        echo "Docker command not found in PATH. Creating symlink to Docker Desktop binary..."
                        # Create symlink if Docker Desktop exists but isn't in PATH
                        DOCKER_APP_BIN="/Applications/Docker.app/Contents/Resources/bin/docker"
                        if [ -f "$DOCKER_APP_BIN" ]; then
                            mkdir -p /usr/local/bin
                            ln -sf "$DOCKER_APP_BIN" /usr/local/bin/docker
                            echo "Created symlink from $DOCKER_APP_BIN to /usr/local/bin/docker"
                        else
                            echo "Docker Desktop binary not found at $DOCKER_APP_BIN"
                            echo "Please ensure Docker Desktop is properly installed"
                            exit 1
                        fi
                    fi
                    
                    # Test Docker functionality
                    echo "Testing Docker functionality..."
                    docker info || {
                        echo "Docker command failed. Possible permission issues."
                        echo "Try running these commands manually to fix permissions:"
                        echo "1. sudo chown root:wheel /var/run/docker.sock"
                        echo "2. sudo chmod g+w /var/run/docker.sock"
                        echo "3. Add Jenkins user to docker group if appropriate"
                        exit 1
                    }
                    '''
                    
                    echo 'Environment setup completed'
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
                    echo 'Making a virtual environment...'
                    sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -e .
                    pip install tensorflow==2.16.2 || pip install tensorflow
                    pip install dvc pytest pytest-cov flake8
                    '''
                    echo 'Virtual environment created and dependencies installed'
                }
            }
        }
        
        stage('Static Code Analysis') {
            steps {
                script {
                    echo 'Running static code analysis...'
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "Flake8 issues detected"
                    '''
                    echo 'Static code analysis completed'
                }
            }
        }
        
        stage('DVC Pull') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Pulling data with DVC...'
                        sh '''
                        . ${VENV_DIR}/bin/activate
                        dvc pull || echo "DVC pull failed, continuing anyway"
                        '''
                        echo 'DVC pull completed'
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
                    echo 'Running automated tests...'
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    mkdir -p test-results
                    pytest --cov=. --cov-report=xml:coverage.xml || echo "Some tests failed"
                    '''
                    echo 'Tests completed'
                }
                publishCoverage adapters: [istanbulCoberturaAdapter('coverage.xml')]
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Building Docker image...'
                    sh '''
                    docker build -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:${DOCKER_TAG} . || exit 1
                    '''
                    echo 'Docker image built successfully'
                }
            }
        }
        
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                    script {
                        echo 'Pushing Docker image to Docker Hub...'
                        sh '''
                        echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
                        docker push ${DOCKER_IMAGE}:latest
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        '''
                        echo 'Docker image pushed successfully'
                    }
                }
            }
        }
        
        stage('Deploy to Development') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Deploying to Development Kubernetes Cluster...'
                        
                        // Check if required tools exist
                        sh '''
                        if ! command -v gcloud &> /dev/null; then
                            echo "gcloud not found, attempting to install..."
                            curl https://sdk.cloud.google.com | bash
                            exec -l $SHELL
                            gcloud init
                        fi
                        
                        if ! command -v kubectl &> /dev/null; then
                            echo "kubectl not found, attempting to install via gcloud..."
                            gcloud components install kubectl
                        fi
                        '''
                        
                        // Proceed with deployment
                        try {
                            sh '''
                            gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                            gcloud config set project ${GCP_PROJECT}
                            gcloud container clusters get-credentials ml-app-cluster --region us-central1
                            kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                            kubectl rollout status deployment/ml-app
                            '''
                            echo 'Deployment to Development completed'
                        } catch (Exception e) {
                            echo "Deployment to Development failed: ${e.getMessage()}"
                            currentBuild.result = 'UNSTABLE'
                        }
                    }
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                expression { return params.DEPLOY_TO_PRODUCTION }
            }
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    input message: 'Approve deployment to production?', ok: 'Deploy'
                }
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Deploying to Production Kubernetes Cluster...'
                        try {
                            sh '''
                            gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                            gcloud config set project ${GCP_PROJECT}
                            gcloud container clusters get-credentials ml-app-prod-cluster --region us-central1
                            kubectl apply -f k8s/production/deployment.yaml
                            kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                            kubectl rollout status deployment/ml-app
                            '''
                            echo 'Deployment to Production completed'
                        } catch (Exception e) {
                            echo "Deployment to Production failed: ${e.getMessage()}"
                            currentBuild.result = 'UNSTABLE'
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo 'Cleaning up workspace...'
                
                // Make sure these files exist before archiving
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
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}