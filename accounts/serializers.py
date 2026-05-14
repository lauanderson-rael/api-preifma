from rest_framework import serializers
from django.contrib.auth import get_user_model
from .level_utils import level_progress

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    xp_to_next_level = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()

    def _lp(self, obj): 
        # Cacheia no contexto do serializer para não recalcular 3x
        if not hasattr(obj, '_level_cache'):
            obj._level_cache = level_progress(obj.xp)
        return obj._level_cache

    def get_level(self, obj):
        return self._lp(obj)['level']

    def get_xp_to_next_level(self, obj):
        return self._lp(obj)['xp_to_next_level']

    def get_progress_pct(self, obj):
        return self._lp(obj)['progress_pct']

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'name',
            'xp', 'level', 'xp_to_next_level', 'progress_pct',
            'streak', 'last_study_date', 'created_at',
        ]
        read_only_fields = ['xp', 'level', 'xp_to_next_level', 'progress_pct', 'streak', 'last_study_date', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'username']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            username=validated_data.get('username', None),
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
