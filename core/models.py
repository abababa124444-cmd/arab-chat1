from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Try to generate a unicode-friendly slug first
            s = slugify(self.name, allow_unicode=True)
            if s:
                self.slug = s
            else:
                # Save to obtain a PK, then set a fallback slug
                super().save(*args, **kwargs)
                self.slug = f"room-{self.pk}"
                super().save(update_fields=["slug"])
                return
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    author_name = models.CharField(max_length=50)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return f"{self.author_name}: {self.content[:30]}"


class DirectThread(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dm_threads_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dm_threads_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user1', 'user2'),)

    def save(self, *args, **kwargs):
        # ensure (user1.id <= user2.id) to keep uniqueness independent of order
        if self.user1_id and self.user2_id and self.user1_id > self.user2_id:
            self.user1_id, self.user2_id = self.user2_id, self.user1_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"DM {self.user1_id}-{self.user2_id}"


class DirectMessage(models.Model):
    thread = models.ForeignKey(DirectThread, related_name='messages', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return f"DM {self.author_id}: {self.content[:30]}"
