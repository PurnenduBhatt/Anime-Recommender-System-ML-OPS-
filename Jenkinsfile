pipeline {
    agent any
    
    environment {
        VENV_DIR = 'venv'
        GCP_PROJECT = 'academic-volt-456808-r1'
        GCLOUD_PATH = "/var/jenkins_home/google-cloud-sdk/bin"
        KUBECTL_AUTH_PLUGIN = "/usr/lib/google-cloud-sdk/bin"
        DOCKER_IMAGE = "gcr.io/${GCP_PROJECT}/ml-project"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        VAULT_ADDR = "http://vault:8200"
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
                }
            }
        }
        
        stage("Creating Virtual Environment") {
            steps {
                script {
                    echo 'Making a virtual environment...'
                    sh '''
                    python -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -e .
                    pip install dvc pytest pytest-cov flake8
                    '''
                }
            }
        }
        
        stage('Static Code Analysis') {
            steps {
                script {
                    echo 'Running static code analysis...'
                    sh '''
                    . ${VENV_DIR}/bin/activate
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
                    '''
                }
            }
        }
        
        stage('DVC Pull') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'DVC Pull....'
                        sh '''
                        . ${VENV_DIR}/bin/activate
                        dvc pull
                        '''
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
                    pytest --cov=. --cov-report=xml:coverage.xml
                    '''
                }
                publishCoverage adapters: [istanbulCoberturaAdapter('coverage.xml')]
            }
        }
        
        stage('Build and Push Image to GCR') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Build and Push Image to GCR'
                        sh '''
                        export PATH=$PATH:${GCLOUD_PATH}
                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud auth configure-docker --quiet
                        
                        # Build with both latest and versioned tags
                        docker build -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                        
                        # Push both tags
                        docker push ${DOCKER_IMAGE}:latest
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        '''
                    }
                }
            }
        }
        
        stage('Deploy to Development') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Deploying to Development Kubernetes Cluster'
                        sh '''
                        export PATH=$PATH:${GCLOUD_PATH}:${KUBECTL_AUTH_PLUGIN}
                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud container clusters get-credentials ml-app-cluster --region us-central1
                        
                        # Update deployment image using kubectl set image
                        kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                        kubectl rollout status deployment/ml-app
                        '''
                    }
                }
            }
        }
        
        stage('Run Ansible Configuration') {
            steps {
                script {
                    echo 'Running Ansible playbooks for configuration management'
                    sh '''
                    export ANSIBLE_HOST_KEY_CHECKING=False
                    ansible-playbook -i inventory/gcp.yml playbooks/configure-elk.yml
                    '''
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
                        echo 'Deploying to Production Kubernetes Cluster'
                        sh '''
                        export PATH=$PATH:${GCLOUD_PATH}:${KUBECTL_AUTH_PLUGIN}
                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud container clusters get-credentials ml-app-prod-cluster --region us-central1
                        
                        # Apply production configuration
                        kubectl apply -f k8s/production/deployment.yaml
                        kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                        kubectl rollout status deployment/ml-app
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            echo 'Cleaning up workspace'
            cleanWs()
        }
        success {
            echo 'Pipeline completed successfully!'
            slackSend(color: 'good', message: "Build #${env.BUILD_NUMBER} - Success! ML App deployed successfully.")
        }
        failure {
            echo 'Pipeline failed!'
            slackSend(color: 'danger', message: "Build #${env.BUILD_NUMBER} - Failed! Check the logs for details.")
        }
    }
}