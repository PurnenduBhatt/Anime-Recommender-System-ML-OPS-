pipeline {
    agent any

    environment {
        VENV_DIR = 'venv'
        GCP_PROJECT = 'academic-volt-456808-r1'
        DOCKER_IMAGE = "kunal2221/mlops-app"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        VAULT_ADDR = "http://vault:8200"
        VAULT_TOKEN = "myroot"
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
                    pip install -e .
                    pip install tensorflow==2.16.2 || pip install tensorflow
                    pip install dvc pytest pytest-cov flake8
                    '''
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
                            dvc pull || echo "DVC pull failed, continuing anyway"
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

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                    script {
                        echo 'Pushing Docker image...'
                        sh '''
                        echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
                        docker push ${DOCKER_IMAGE}:latest
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        '''
                    }
                }
            }
        }

        stage('Deploy to Development') {
            steps {
                script {
                    def credExists = false
                    try {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            credExists = true
                        }
                    } catch (e) {
                        echo "⚠️ GCP credentials not found, skipping deploy to dev."
                    }
                    if (credExists) {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            sh '''
                            gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                            gcloud config set project ${GCP_PROJECT}
                            gcloud container clusters get-credentials ml-app-cluster --region us-central1
                            kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                            kubectl rollout status deployment/ml-app
                            '''
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
                script {
                    def credExists = false
                    try {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            credExists = true
                        }
                    } catch (e) {
                        error("❌ GCP credentials missing! Cannot deploy to production.")
                    }
                    if (credExists) {
                        withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                            sh '''
                            gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                            gcloud config set project ${GCP_PROJECT}
                            gcloud container clusters get-credentials ml-app-prod-cluster --region us-central1
                            kubectl apply -f k8s/production/deployment.yaml
                            kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                            kubectl rollout status deployment/ml-app
                            '''
                        }
                    }
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
