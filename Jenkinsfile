pipeline {
    agent any

    environment {
        VENV_DIR = 'venv'
        DOCKER_IMAGE = "kunal2221/mlops-app"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        PATH = "${env.PATH}"
    }

    parameters {
        booleanParam(name: 'RUN_TESTS', defaultValue: true, description: 'Run automated tests')
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
                echo 'Workspace cleaned'
            }
        }

        stage("Clone Repo") {
            steps {
                checkout scm
            }
        }

        stage("Create Virtual Env & Install Deps") {
            steps {
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage("Static Analysis") {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    flake8 . || true
                '''
            }
        }

        stage("Run Tests") {
            when {
                expression { return params.RUN_TESTS }
            }
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    pytest
                '''
            }
        }

        stage("Build Docker Image") {
            steps {
                sh '''
                    docker build -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                '''
            }
        }

        stage("Push to Docker Hub") {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', passwordVariable: 'DOCKER_PASSWORD', usernameVariable: 'DOCKER_USERNAME')]) {
                    sh '''
                        echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
                        docker push ${DOCKER_IMAGE}:latest
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                    '''
                }
            }
        }

        stage("Deploy ELK Stack & Vault with Docker Compose") {
            steps {
                sh '''
                    docker-compose down || true
                    docker-compose up -d --build
                '''
            }
        }

        stage("Deploy ml-app to Local Kubernetes") {
            steps {
                sh '''
                    kubectl apply -f k8s/production/deployment.yaml
                    kubectl rollout status deployment/ml-app
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo '✅ Build and deployment succeeded!'
        }
        failure {
            echo '❌ Build or deployment failed!'
        }
    }
}
