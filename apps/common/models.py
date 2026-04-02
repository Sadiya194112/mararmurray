from django.db import models
from tinymce.models import HTMLField


class PrivacyPolicy(models.Model):
    content = HTMLField()

    class Meta:
        verbose_name_plural = "Privacy Policy"

    def __str__(self):
        return "Privacy Policy"


class TermsConditions(models.Model):
    content = HTMLField()

    class Meta:
        verbose_name_plural = "Terms & Conditions"

    def __str__(self):
        return "Terms & Conditions"


class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name} - {self.subject}"
