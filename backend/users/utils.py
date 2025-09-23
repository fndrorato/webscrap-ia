import os

def user_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    user_id = instance.user.id if instance.user else 'unknown'
    return f'uploads/users/photos/user_{user_id}.{ext}'
