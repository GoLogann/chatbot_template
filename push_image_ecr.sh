#!/bin/bash

set -e

# Configure estas variáveis de acordo com seu ambiente
aws_account_id=${AWS_ACCOUNT_ID:-"YOUR_AWS_ACCOUNT_ID"}
aws_region=${AWS_REGION:-"us-east-1"}
docker_tag=${DOCKER_TAG:-"latest"}
ecr_repo_name=${ECR_REPO_NAME:-"chatbot-template-repo"}
docker_image_name=${DOCKER_IMAGE_NAME:-"chatbot-template"}
aws_profile=${AWS_PROFILE:-"default"}

echo "🔨 Construindo imagem Docker..."
docker build -t ${docker_image_name} .

echo "🔐 Logando no Amazon ECR..."
AWS_PROFILE=${aws_profile} aws ecr get-login-password --region ${aws_region} | \
  docker login --username AWS --password-stdin ${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com

echo "🏷  Adicionando tag na imagem..."
docker tag ${docker_image_name} ${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${ecr_repo_name}:${docker_tag}

echo "📤 Enviando imagem para o ECR..."
docker push ${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${ecr_repo_name}:${docker_tag}

echo "✅ Imagem enviada com sucesso!"