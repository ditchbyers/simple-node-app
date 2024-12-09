import groovy.json.JsonOutput

pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: '6abcb036-fd5b-4cd1-996e-c12253741675', url: 'https://github.com/ditchbyers/simple-node-app.git']])
            }
        }
        stage('Run Python Script') {
            steps {
                script {
                    // Run the Python script to get commit info
                    def output = sh(script: '. .venv/bin/activate && python3 git-info.py', returnStdout: true).trim()
                    echo "Output: ${output}}"
                }
            }
        }
    }
}
