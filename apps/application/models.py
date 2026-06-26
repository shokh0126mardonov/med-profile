from django.db import models

class Applications(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'Yangi (Operator kutilmoqda)'),
        ('ASSIGNED', 'Shifokor biriktirildi'),
        ('REJECTED', 'Rad etildi'),
        ('COMPLETED', 'Yakunlandi (Shifokor javob berdi)'),
        ('CLOSED', 'Yopildi (Bemorga javob yuborildi)'),
    ]

    sick = models.ForeignKey(
        'users.SickModel', on_delete=models.CASCADE, related_name='applications'
    )
    doctor = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'role': 'DOCTOR'},
        related_name='doctor_applications'
    )
    
    text = models.TextField(verbose_name="Bemor arizasi matni")
    
    doctor_response = models.TextField(null=True, blank=True, verbose_name="Shifokor tashxisi/javobi")
    operator_response = models.TextField(null=True, blank=True, verbose_name="Operator izohi")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pk}  ----- {self.sick.phone}"

    class Meta:
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"