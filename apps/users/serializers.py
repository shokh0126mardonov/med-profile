from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserRole

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'phone', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        
        user = super().create(validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        return user

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.role == UserRole.DOCTOR and 'role' in validated_data:
                validated_data.pop('role', None)

        # Parol kelgan bo'lsa, uni sug'urib olamiz va alohida hash qilamiz
        password = validated_data.pop('password', None)
        
        # Qolgan maydonlarni (username, phone, etc.) yangilaymiz
        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        return instance