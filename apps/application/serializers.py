from rest_framework import serializers
from .models import Applications

class ApplicationListRetrieveSerializer(serializers.ModelSerializer):
    # Bemor ma'lumotlarini chiroyli ko'rsatish uchun (ixtiyoriy)
    sick_phone = serializers.CharField(source='sick.phone', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Applications
        fields = [
            'id', 'sick', 'sick_phone', 'doctor', 'doctor_name', 'text', 
            'doctor_response', 'operator_response', 'status', 'created_at', 'updated_at'
        ]
        # Barcha maydonlar default holatda faqat o'qish uchun (GET uchun), chunki umumiy CRUD yo'q!
        read_only_fields = fields


class DoctorResponseSerializer(serializers.ModelSerializer):
    """ Shifokor tashxis yozishi yoki tahrirlashi uchun """
    doctor_response = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Applications
        fields = ['doctor_response']

    def validate(self, attrs):
        # 💡 AGAR ARIZA YOPILGAN BO'LSA, shifokor ham qayta tahrirlay olmaydi
        if self.instance.status == 'CLOSED':
            raise serializers.ValidationError("Ushbu ariza yopilgan! Shifokor javobini tahrirlab bo'lmaydi.")
        return attrs

class OperatorResponseSerializer(serializers.ModelSerializer):
    """ Operator izoh yozishi yoki tahrirlashi uchun """
    operator_response = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Applications
        fields = ['operator_response']

    def validate(self, attrs):
        # Agar ariza allaqachon yopilgan (CLOSED) bo'lsa, umuman tahrirlatmaymiz
        if self.instance.status == 'CLOSED':
            raise serializers.ValidationError("Ushbu ariza yopilgan! Izohni tahrirlab bo'lmaydi.")
        return attrs


