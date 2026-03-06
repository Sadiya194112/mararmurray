from django.urls import path

from apps.posts.views import (
    create_post,
    delete_post,
    delete_post_image,
    explore_feed,
    get_post_detail,
    get_post_image,
    get_trending_hashtags,
    get_user_profile,
    list_user_posts,
    search_by_hashtag,
    search_posts,
    update_post,
    upload_post_image,
)

urlpatterns = [
    # 5. Post APIs
    # 5.1 Create Post
    path("posts/create/", create_post, name="create-post"),
    # 5.2 List User Posts
    path("posts/", list_user_posts, name="list-user-posts"),
    # 5.3 Get Post Detail
    path("posts/<int:post_id>/", get_post_detail, name="get-post-detail"),
    # 5.4 Update Post
    path("posts/<int:post_id>/update/", update_post, name="update-post"),
    # 5.5 Delete Post
    path("posts/<int:post_id>/delete/", delete_post, name="delete-post"),
    # 5.6 Upload Post Image
    path(
        "posts/<int:post_id>/image/upload/",
        upload_post_image,
        name="upload-post-image",
    ),
    # 5.7 Get Post Image
    path(
        "posts/<int:post_id>/image/",
        get_post_image,
        name="get-post-image",
    ),
    # 5.8 Delete Post Image
    path(
        "posts/<int:post_id>/image/delete/",
        delete_post_image,
        name="delete-post-image",
    ),
    # 7. Explore APIs
    # 7.1 Explore Feed
    path("explore/feed/", explore_feed, name="explore-feed"),
    # 7.2 Search Posts
    path("explore/search/", search_posts, name="search-posts"),
    # 7.3 Search by Hashtag
    path("explore/hashtag/<str:hashtag>/", search_by_hashtag, name="search-hashtag"),
    # 7.4 Get Trending Hashtags
    path("explore/trending/", get_trending_hashtags, name="trending-hashtags"),
    # 7.5 Get User Profile
    path("explore/user/<int:user_id>/", get_user_profile, name="user-profile"),
]
