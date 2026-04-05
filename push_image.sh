
# # Check if there are any uncommitted changes
# if [[ -n $(git status --porcelain) ]]; then
#   echo "Error: There are uncommitted changes. Please commit your changes before running this script."
#   exit 1
# fi

# TAG=$(git rev-parse --short HEAD)
# Information about Docker registry and image
REGISTRY_URL="10.39.125.26:8000"
IMAGE_NAME="nq57_catp"

# Check if --prod flag is passed
if [[ "$1" == "--prod" ]]; then
  echo "Building production image..."
else
  echo "Building test image..."
  IMAGE_NAME="${IMAGE_NAME}_beta"
fi

# Build image Docker without cache
docker build -t $IMAGE_NAME --platform linux/amd64 .

# # Attach image with tag (full tag)
# docker tag $IMAGE_NAME $REGISTRY_URL/$IMAGE_NAME:$TAG

# # Push image to registry with tag
# docker push $REGISTRY_URL/$IMAGE_NAME:$TAG

# Attach image with tag -latest
docker tag $IMAGE_NAME $REGISTRY_URL/$IMAGE_NAME:latest

# Push image to registry with tag 'latest'
docker push $REGISTRY_URL/$IMAGE_NAME:latest

# Remove image local
docker rmi $IMAGE_NAME
# docker rmi $REGISTRY_URL/$IMAGE_NAME:$TAG
docker rmi $REGISTRY_URL/$IMAGE_NAME:latest