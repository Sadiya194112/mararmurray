from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.models import User
from apps.posts.models import Post
from apps.posts.serializers import PostDetailSerializer, PostSerializer

# ============== Post APIs ==============


@swagger_auto_schema(method="post", tags=["5. Posts"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def create_post(request):
    """5.1 Create post with description and optional image"""
    serializer = PostSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(
            {
                "message": "Post created successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="get", tags=["5. Posts"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def list_user_posts(request):
    """5.2 List all posts for authenticated user"""
    posts = Post.objects.filter(user=request.user).order_by("-created_at")
    serializer = PostSerializer(posts, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="get", tags=["5. Posts"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def get_post_detail(request, post_id):
    """5.3 Get post detail by ID"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    serializer = PostSerializer(post, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="patch", tags=["5. Posts"])
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def update_post(request, post_id):
    """5.4 Update post description and/or image"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    serializer = PostSerializer(
        post, data=request.data, partial=True, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                "message": "Post updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method="delete", tags=["5. Posts"])
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def delete_post(request, post_id):
    """5.5 Delete post"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    post.delete()
    return Response(
        {"message": "Post deleted successfully"},
        status=status.HTTP_200_OK,
    )


# ============== Post Image APIs ==============


@swagger_auto_schema(method="post", tags=["5. Posts"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def upload_post_image(request, post_id):
    """5.6 Upload post image"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    image_file = request.FILES.get("image")
    if not image_file:
        return Response(
            {"message": "No image file provided"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    post.image = image_file
    post.save()
    return Response(
        {
            "message": "Post image uploaded successfully",
            "image_url": post.image.url if post.image else None,
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["5. Posts"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def get_post_image(request, post_id):
    """5.7 Get post image"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    if post.image:
        return Response({"image_url": post.image.url}, status=status.HTTP_200_OK)
    return Response({"message": "No post image"}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(method="delete", tags=["5. Posts"])
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication])
def delete_post_image(request, post_id):
    """5.8 Delete post image"""
    post = get_object_or_404(Post, id=post_id, user=request.user)
    if post.image:
        post.image.delete()
        post.image = None
        post.save()
        return Response(
            {"message": "Post image deleted successfully"},
            status=status.HTTP_200_OK,
        )
    return Response(
        {"message": "No post image to delete"}, status=status.HTTP_404_NOT_FOUND
    )


# ============== Explore APIs ==============


@swagger_auto_schema(method="get", tags=["7. Explore"])
@api_view(["GET"])
@permission_classes([AllowAny])
def explore_feed(request):
    """7.1 Get explore feed - All public posts"""
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    start = (page - 1) * limit

    posts = Post.objects.all()[start : start + limit]
    serializer = PostDetailSerializer(posts, many=True, context={"request": request})
    return Response(
        {
            "data": serializer.data,
            "page": page,
            "limit": limit,
            "total": Post.objects.count(),
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["7. Explore"])
@api_view(["GET"])
@permission_classes([AllowAny])
def search_posts(request):
    """7.2 Search posts by description, tags, or user"""
    query = request.GET.get("q", "")
    if not query:
        return Response(
            {"error": "Search query required"}, status=status.HTTP_400_BAD_REQUEST
        )

    posts = Post.objects.filter(
        Q(description__icontains=query)
        | Q(tags__icontains=query)
        | Q(user__name__icontains=query)
        | Q(user__email__icontains=query)
    )[:50]

    serializer = PostDetailSerializer(posts, many=True, context={"request": request})
    return Response(
        {
            "query": query,
            "results": serializer.data,
            "count": len(posts),
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["7. Explore"])
@api_view(["GET"])
@permission_classes([AllowAny])
def search_by_hashtag(request, hashtag):
    """7.3 Get posts by hashtag"""
    # Remove # if present
    hashtag = hashtag.lstrip("#")
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))
    start = (page - 1) * limit

    posts = Post.objects.filter(tags__icontains=f"#{hashtag}")[start : start + limit]

    serializer = PostDetailSerializer(posts, many=True, context={"request": request})
    return Response(
        {
            "hashtag": f"#{hashtag}",
            "data": serializer.data,
            "page": page,
            "limit": limit,
            "total": Post.objects.filter(tags__icontains=f"#{hashtag}").count(),
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["7. Explore"])
@api_view(["GET"])
@permission_classes([AllowAny])
def get_trending_hashtags(request):
    """7.4 Get trending hashtags"""
    # Simple implementation - count hashtag occurrences

    posts = Post.objects.exclude(tags__isnull=True).exclude(tags__exact="")

    hashtags = {}
    for post in posts:
        tags = post.tags.split(",") if post.tags else []
        for tag in tags:
            tag = tag.strip()
            if tag:
                hashtags[tag] = hashtags.get(tag, 0) + 1

    # Sort by count
    trending = sorted(hashtags.items(), key=lambda x: x[1], reverse=True)[:20]

    return Response(
        {
            "trending_hashtags": [tag for tag, count in trending],
            "hashtag_counts": dict(trending),
        },
        status=status.HTTP_200_OK,
    )


@swagger_auto_schema(method="get", tags=["7. Explore"])
@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_profile(request, user_id):
    """7.5 Get user profile with posts"""
    from apps.accounts.serializers import UserSerializer

    user = get_object_or_404(User, id=user_id)
    user_data = UserSerializer(user, context={"request": request}).data

    posts = Post.objects.filter(user=user).order_by("-created_at")
    posts_data = PostSerializer(posts, many=True, context={"request": request}).data

    return Response(
        {
            "user": user_data,
            "posts": posts_data,
            "post_count": posts.count(),
        },
        status=status.HTTP_200_OK,
    )
