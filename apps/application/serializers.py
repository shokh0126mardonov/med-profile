import requests
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.application.models import Applications, ApplicationAssignment
from apps.users.models import SickModel
from decouple import config  # 💡 Config orqali TOKEN'ni chaqiramiz

User = get_user_model()

# 💡 TOKEN'ni aynan sen aytganingdek config'dan oldik:
BOT_TOKEN = config('TOKEN') 

# ==============================================================================
# 1. YORDAMCHI (NESTED) SERIALIZERLAR
# ==============================================================================

class UserShortSerializer(serializers.ModelSerializer):
    """Shifokor ma'lumotlarini qisqa ko'rinishda qaytarish"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']


class SickShortSerializer(serializers.ModelSerializer):
    """
    Bemor ma'lumotlarini qisqa ko'rinishda qaytarish.
    🔒 Shifokor va Operatorlar ko'rmasligi uchun telegram_id olib tashlandi!
    """
    class Meta:
        model = SickModel
        fields = ['id', 'full_name', 'phone']  # 🔒 telegram_id bu yerda yo'q!


class ApplicationAssignmentSerializer(serializers.ModelSerializer):
    """O'rta jadvaldagi shifokorlar tashxisi va fayllari"""
    doctor = UserShortSerializer(read_only=True)
    doctor_response_file = serializers.FileField(read_only=True)

    class Meta:
        model = ApplicationAssignment
        fields = [
            'id', 
            'doctor', 
            'doctor_response_text', 
            'doctor_response_file', 
            'doctor_response_file_id', 
            'assigned_at', 
            'responded_at'
        ]


# ==============================================================================
# 2. ASOSIY ACTION SERIALIZERLARI
# ==============================================================================

class ApplicationListRetrieveSerializer(serializers.ModelSerializer):
    """GET /api/applications/ (list va retrieve) uchun"""
    sick = SickShortSerializer(read_only=True)
    assignments = ApplicationAssignmentSerializer(many=True, read_only=True)
    user_file = serializers.SerializerMethodField()

    class Meta:
        model = Applications
        fields = [
            'id', 
            'sick', 
            'text', 
            'user_file', 
            'status', 
            'operator_response', 
            'assignments', 
            'created_at', 
            'updated_at'
        ]

    def get_user_file(self, obj):
        if not obj.file_id:
            return None
            
        try:
            # Telegram API orqali fayl yo'lini (file_path) so'raymiz
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
            response = requests.get(url, params={'file_id': obj.file_id}, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    file_path = result['result']['file_path']
                    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    
        except Exception as e:
            print(f"💥 Telegram fayl yo'lini olishda xatolik: {e}")
            
        return None


class DoctorResponseSerializer(serializers.ModelSerializer):
    """Shifokor saytdan matnli tashxis va fayl yuklashi uchun"""
    class Meta:
        model = ApplicationAssignment
        fields = ['doctor_response_text', 'doctor_response_file']
        extra_kwargs = {
            'doctor_response_text': {'required': True}
        }


class OperatorResponseSerializer(serializers.ModelSerializer):
    """Operator arizaga o'z izohini yozishi uchun"""
    class Meta:
        model = Applications
        fields = ['operator_response']
        extra_kwargs = {
            'operator_response': {'required': True}
        }