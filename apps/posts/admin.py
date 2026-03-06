from django.contrib import admin

from apps.posts.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "description", "image", "created_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["user__email", "description"]
    readonly_fields = ["created_at", "updated_at"]
