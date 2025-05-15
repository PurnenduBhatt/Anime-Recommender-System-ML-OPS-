pipeline {
    agent {
        docker {
            image 'python:3.12-slim'  // Use a Docker image with Python 3.12
            args '-u root'  // Run as root to avoid permission issues
        }
    }
    
    environment {
        VENV_DIR = 'venv'
        GCP_PROJECT = 'academic-volt-456808-r1'
        GCLOUD_PATH = "/var/jenkins_home/google-cloud-sdk/bin"
        KUBECTL_AUTH_PLUGIN = "/usr/lib/google-cloud-sdk/bin"
        DOCKER_IMAGE = "kunal2221/mlops-app"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        VAULT_ADDR = "http://vault:8200"
        VAULT_TOKEN = "myroot"
        PATH = "/opt/homebrew/bin:/usr/bin:/usr/local/bin:$PATH"  // Include /usr/local/bin for installed tools
        PYTHON_VERSION = "3.12"
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
        
        stage("Install Dependencies") {
            steps {
                script {
                    echo 'Installing required system dependencies...'
                    sh '''
                    apt-get update
                    apt-get install -y git docker.io google-cloud-sdk kubectl ansible vault
                    '''
                    echo 'System dependencies installed successfully'
                }
            }
        }
        
        stage("Cloning from Github") {
            steps {
                script {
                    echo 'Cloning from Github...'
                    sh 'echo $PATH'
                    sh 'which git'
                    sh 'git --version'
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
                    pip install tensorflow==2.16.2
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
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
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
                        dvc pull
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
                    pytest --cov=. --cov-report=xml:coverage.xml
                    '''
                    echo 'Tests completed successfully'
                }
                publishCoverage adapters: [istanbulCoberturaAdapter('coverage.xml')]
            }
        }
        
        stage('Fetch Credentials from Vault') {
            steps {
                script {
                    echo 'Fetching credentials from Vault...'
                    sh '''
                    export VAULT_ADDR=${VAULT_ADDR}
                    vault login ${VAULT_TOKEN}
                    ELASTIC_USER=$(vault kv get -field=user secret/ml-app/elasticsearch)
                    ELASTIC_PASSWORD=$(vault kv get -field=password secret/ml-app/elasticsearch)
                    echo "ELASTIC_USER=${ELASTIC_USER}" >> vault.env
                    echo "ELASTIC_PASSWORD=${ELASTIC_PASSWORD}" >> vault.env
                    '''
                    echo 'Credentials fetched from Vault successfully'
                }
            }
        }
        
        stage('Build and Push Image to Docker Hub') {
            steps {
                script {
                    echo 'Building and pushing Docker image to Docker Hub...'
                    sh '''
                    docker build -t ${DOCKER_IMAGE}:latest -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                    docker push ${DOCKER_IMAGE}:latest
                    docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                    '''
                    echo 'Docker image built and pushed successfully'
                }
            }
        }
        
        stage('Deploy to Development') {
            steps {
                withCredentials([file(credentialsId:'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Deploying to Development Kubernetes Cluster...'
                        sh '''
                        export PATH=$PATH:${GCLOUD_PATH}:${KUBECTL_AUTH_PLUGIN}
                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud container clusters get-credentials ml-app-cluster --region us-central1
                        kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                        kubectl rollout status deployment/ml-app
                        '''
                        echo 'Deployment to Development completed'
                    }
                }
            }
        }
        
        stage('Run Ansible Configuration') {
            steps {
                script {
                    echo 'Running Ansible playbooks for configuration management...'
                    def vaultEnv = readFile('vault.env').trim().split('\n')
                    vaultEnv.each { envVar ->
                        def (key, value) = envVar.split('=')
                        env."${key}" = value
                    }
                    try {
                        sh '''
                        export ANSIBLE_HOST_KEY_CHECKING=False
                        ansible-playbook -i inventory/localhost.yml playbooks/configure-elk.yml \
                            -e "elastic_user=${ELASTIC_USER}" \
                            -e "elastic_password=${ELASTIC_PASSWORD}"
                        '''
                        echo 'Ansible configuration completed successfully'
                    } catch (Exception e) {
                        echo "Ansible configuration failed: ${e.getMessage()}"
                        currentBuild.result = 'UNSTABLE'
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
                        sh '''
                        export PATH=$PATH:${GCLOUD_PATH}:${KUBECTL_AUTH_PLUGIN}
                        gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
                        gcloud config set project ${GCP_PROJECT}
                        gcloud container clusters get-credentials ml-app-prod-cluster --region us-central1
                        kubectl apply -f k8s/production/deployment.yaml
                        kubectl set image deployment/ml-app ml-app-container=${DOCKER_IMAGE}:${DOCKER_TAG}
                        kubectl rollout status deployment/ml-app
                        '''
                        echo 'Deployment to Production completed'
                    }
                }
            }
        }
    }
    
    post {
        always {
            echo 'Cleaning up workspace...'
            archiveArtifacts artifacts: 'vault.env, coverage.xml, **/ml-app.log', allowEmptyArchive: true
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