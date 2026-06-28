from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        if not email:
            raise ValueError('O usuário precisa ter um e-mail')
        email = self.normalize_email(email)
        if not username:
            username = email.split('@')[0]
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user 

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Email")
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    name = models.CharField(max_length=120, verbose_name="Nome")
    
    # Gamificação
    xp = models.IntegerField(default=0, verbose_name="Pontuação de XP")
    ai_daily_limit = models.PositiveIntegerField(default=3, verbose_name="Limite de diário de IA", help_text="Limite de explicações por IA por dia")
    
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    is_staff = models.BooleanField(default=False, verbose_name="Membro Administrador?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cadastrado em")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
