apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: log
      enabled: true
      paths:
        - /app/logs/*.log
    output.logstash:
      hosts: ["logstash-service:5044"]
    logging.level: info
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-app
  labels:
    app: ml-app
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: ml-app
  template:
    metadata:
      labels:
        app: ml-app
    spec:
      containers:
      - name: ml-app-container
        image: kunal2221/mlops-app:latest
        ports:
        - containerPort: 5000
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        # Updated readiness probe - more lenient timing
        readinessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 5
        # Updated liveness probe - more lenient timing  
        livenessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 120
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        volumeMounts:
        - name: logs-volume
          mountPath: /app/logs
        - name: filebeat-config
          mountPath: /etc/filebeat
      # Add init container to handle any pre-startup tasks
      initContainers:
      - name: init-logs
        image: busybox:1.28
        command: ['sh', '-c', 'mkdir -p /app/logs && chmod 777 /app/logs']
        volumeMounts:
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: logs-volume
        emptyDir: {}
      - name: filebeat-config
        configMap:
          name: filebeat-config
      # Add tolerations and node affinity if needed
      tolerations: []
      affinity: {}
      # Increase termination grace period
      terminationGracePeriodSeconds: 60
---
apiVersion: v1
kind: Service
metadata:
  name: ml-app-service
  labels:
    app: ml-app
spec:
  selector:
    app: ml-app
  ports:
  - name: http
    port: 80
    targetPort: 5000
    protocol: TCP
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: logstash-service
  labels:
    app: logstash
spec:
  selector:
    app: logstash
  ports:
  - name: beats
    port: 5044
    targetPort: 5044
    protocol: TCP
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60