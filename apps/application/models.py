from django.db import models

class Applications(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'Yangi (Operator kutilmoqda)'),
        ('ASSIGNED', 'Shifokor(lar) biriktirildi'),
        ('REJECTED', 'Rad etildi'),
        ('COMPLETED', 'Yakunlandi (Shifokorlar javob berdi)'),
        ('CLOSED', 'Yopildi (Bemorga javob yuborildi)'),
    ]

    sick = models.ForeignKey(
        'users.SickModel', on_delete=models.CASCADE, related_name='applications'
    )
    
    user_file_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="Bemor fayli havolasi")

    
    doctors = models.ManyToManyField(
        'users.User',
        through='ApplicationAssignment',
        related_name='doctor_applications',
        verbose_name="Biriktirilgan shifokorlar"
    )

    rejected_by_doctors = models.ManyToManyField(
        'users.User',
        blank=True,
        related_name='skipped_applications',
        verbose_name="Ushbu arizani rad etgan shifokorlar",
        limit_choices_to={'role': 'DOCTOR'}
    )
    
    text = models.TextField(verbose_name="Bemor arizasi matni")
    operator_response = models.TextField(null=True, blank=True, verbose_name="Operator izohi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pk}  ----- {self.sick.phone}"

    class Meta:
        ordering = ['-pk']
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"


class ApplicationAssignment(models.Model):
    application = models.ForeignKey(
        Applications, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    doctor = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'DOCTOR'},
        related_name='assigned_cases'
    )
    

    doctor_response_text = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Shifokor tashxisi/javobi"
    )
    
    doctor_response_file = models.FileField(
        upload_to='doctor_responses//%Y/%m/%d/', 
        null=True, 
        blank=True, 
        verbose_name="Shifokor yuklagan hujjat/fayl (Sayt uchun)",
    )
    
    doctor_response_file_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Shifokor yuborgan faylning Telegram ID-si (Bot uchun)"
    )
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="Javob berilgan vaqt")

    class Meta:
        unique_together = ('application', 'doctor')
        verbose_name = "Shifokor biriktiruvi"
        verbose_name_plural = "Shifokor biriktiruvlari"

    def __str__(self):
        return f"Ariza {self.application.id} -> Dr. {self.doctor.username}"