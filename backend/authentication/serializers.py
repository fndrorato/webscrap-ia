from django.contrib.auth.models import Permission
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Adiciona campos customizados ao token (opcional)
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['user_id'] = user.id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Adiciona campos customizados à resposta
        user = self.user
        data['first_name'] = user.first_name
        data['last_name'] = user.last_name
        data['user_id'] = user.id
      
        # Pegando permissões via grupos
        permissions = Permission.objects.filter(group__user=user).values_list('codename', flat=True).distinct()
        data['permissions'] = list(permissions)

        return data
