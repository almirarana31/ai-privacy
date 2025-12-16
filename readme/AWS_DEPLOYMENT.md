# AWS CodeDeploy Deployment Guide

## Architecture: ECS Fargate + CodeDeploy + CodePipeline

This setup uses your existing Docker containers deployed to AWS ECS Fargate with automated CI/CD.

## Prerequisites

1. **AWS CLI** installed and configured
2. **AWS Account** with admin access
3. **GitHub** repository (or CodeCommit)
4. **Domain** (optional, for custom domain)

## Step 1: Create ECR Repositories

```bash
# Create ECR repositories for Docker images
aws ecr create-repository --repository-name ai-privacy-backend --region us-east-1
aws ecr create-repository --repository-name ai-privacy-frontend --region us-east-1
```

## Step 2: Create EFS (for persistent JSON files)

```bash
# Create EFS file system for model results
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=ai-privacy-models \
  --region us-east-1

# Note the FileSystemId (fs-xxxxxxxxx)

# Create mount targets in your VPC subnets
aws efs create-mount-target \
  --file-system-id fs-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxx \
  --security-groups sg-xxxxxxxxx

# Create access points for each model directory
aws efs create-access-point \
  --file-system-id fs-xxxxxxxxx \
  --posix-user Uid=1000,Gid=1000 \
  --root-directory Path=/models_research,CreationInfo={OwnerUid=1000,OwnerGid=1000,Permissions=755} \
  --tags Key=Name,Value=models-research
```

## Step 3: Create ECS Cluster

```bash
# Create ECS Fargate cluster
aws ecs create-cluster \
  --cluster-name ai-privacy-cluster \
  --region us-east-1
```

## Step 4: Update Configuration Files

### 4.1 Update `taskdef.json`
- Replace `YOUR_ACCOUNT_ID` with your AWS account ID
- Replace `fs-xxxxxxxxx` with your EFS file system IDs
- Replace `fsap-xxxxxxxxx` with your EFS access point IDs
- Update region if not `us-east-1`

### 4.2 Update `appspec.yml`
- Replace subnet IDs with your VPC subnets
- Replace security group ID

### 4.3 Update `buildspec.yml`
- Verify region matches your setup

## Step 5: Create IAM Roles

```bash
# ECS Task Execution Role (for pulling images, logs)
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# ECS Task Role (for application permissions)
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# CodeBuild Role
aws iam create-role \
  --role-name codebuild-ai-privacy-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "codebuild.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies to CodeBuild role (ECR, S3, Logs)
```

## Step 6: Create CodeBuild Project

```bash
aws codebuild create-project \
  --name ai-privacy-build \
  --source type=GITHUB,location=https://github.com/YOUR_USERNAME/ai-privacy.git \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true \
  --service-role arn:aws:iam::YOUR_ACCOUNT_ID:role/codebuild-ai-privacy-role \
  --region us-east-1
```

## Step 7: Register Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://taskdef.json \
  --region us-east-1
```

## Step 8: Create ECS Service

```bash
# Create Application Load Balancer first
aws elbv2 create-load-balancer \
  --name ai-privacy-alb \
  --subnets subnet-xxxxxxxx subnet-yyyyyyyy \
  --security-groups sg-xxxxxxxxx \
  --scheme internet-facing \
  --type application

# Create target groups
aws elbv2 create-target-group \
  --name ai-privacy-frontend-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxxxxxxxx \
  --target-type ip \
  --health-check-path /

# Create ECS service
aws ecs create-service \
  --cluster ai-privacy-cluster \
  --service-name ai-privacy-service \
  --task-definition ai-privacy-task:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxx,subnet-yyyyyyyy],securityGroups=[sg-xxxxxxxxx],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:YOUR_ACCOUNT_ID:targetgroup/ai-privacy-frontend-tg/xxxxxxxxx,containerName=frontend,containerPort=80 \
  --deployment-controller type=CODE_DEPLOY
```

## Step 9: Create CodeDeploy Application

```bash
# Create CodeDeploy application
aws deploy create-application \
  --application-name ai-privacy-app \
  --compute-platform ECS \
  --region us-east-1

# Create deployment group
aws deploy create-deployment-group \
  --application-name ai-privacy-app \
  --deployment-group-name ai-privacy-dg \
  --deployment-config-name CodeDeployDefault.ECSAllAtOnce \
  --service-role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/CodeDeployServiceRole \
  --ecs-services clusterName=ai-privacy-cluster,serviceName=ai-privacy-service \
  --load-balancer-info targetGroupPairInfoList=[{targetGroups=[{name=ai-privacy-frontend-tg}],prodTrafficRoute={listenerArns=[arn:aws:elasticloadbalancing:...]}}] \
  --blue-green-deployment-configuration 'terminateBlueInstancesOnDeploymentSuccess={action=TERMINATE,terminationWaitTimeInMinutes=5},deploymentReadyOption={actionOnTimeout=CONTINUE_DEPLOYMENT}'
```

## Step 10: Create CodePipeline

```bash
# Create S3 bucket for artifacts
aws s3 mb s3://ai-privacy-pipeline-artifacts-YOUR_ACCOUNT_ID

# Create pipeline
aws codepipeline create-pipeline --cli-input-json file://pipeline.json
```

## Step 11: Deploy!

### Option A: Push to GitHub
```bash
git add .
git commit -m "Deploy to AWS"
git push origin main
```
Pipeline automatically triggers!

### Option B: Manual Deploy
```bash
# Build and push images
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t ai-privacy-backend backend/
docker tag ai-privacy-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-privacy-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-privacy-backend:latest

docker build -t ai-privacy-frontend frontend/
docker tag ai-privacy-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-privacy-frontend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-privacy-frontend:latest

# Update service
aws ecs update-service \
  --cluster ai-privacy-cluster \
  --service ai-privacy-service \
  --force-new-deployment
```

## Adding Results After Deployment

### Via EFS Mount:
```bash
# SSH to EC2 instance in same VPC (or use AWS Transfer Family)
sudo mount -t efs -o tls fs-xxxxxxxxx:/ /mnt/efs

# Copy JSON files
cp research_results.json /mnt/efs/models_research/
cp fl_adult_results.json /mnt/efs/models_fl_adult/
cp dp_continue_results.json /mnt/efs/models_research_dp_continue/

# Files immediately available to containers!
```

### Or use AWS DataSync / S3:
```bash
# Upload to S3, then sync to EFS
aws s3 cp research_results.json s3://your-bucket/models/
aws datasync create-task ... # Configure S3 to EFS sync
```

## Monitoring

```bash
# View service status
aws ecs describe-services --cluster ai-privacy-cluster --services ai-privacy-service

# View logs
aws logs tail /ecs/ai-privacy-backend --follow
aws logs tail /ecs/ai-privacy-frontend --follow

# View deployments
aws deploy list-deployments --application-name ai-privacy-app
```

## Costs Estimate

- **ECS Fargate**: ~$30-50/month (2 tasks, 1vCPU, 2GB RAM each)
- **ALB**: ~$16/month + data transfer
- **EFS**: ~$0.30/GB/month (only for results files, ~1GB)
- **ECR**: $0.10/GB/month for storage
- **Data Transfer**: $0.09/GB outbound
- **Total**: ~$50-80/month for production workload

## Alternative: Simpler EC2 + Docker Compose

If ECS seems complex, you can use CodeDeploy with EC2:
- Deploy docker-compose.yml to EC2 instance
- CodeDeploy runs lifecycle scripts
- Cheaper (~$10-20/month for t3.medium)
- Simpler but less scalable

Want me to set up the EC2 + Docker Compose approach instead?
