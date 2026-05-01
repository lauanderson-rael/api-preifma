from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'name', 'xp', 'streak', 'last_study_date', 'is_staff')
    search_fields = ('email', 'username', 'name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('name', 'username')}),
        ('Gamificação', {'fields': ('xp', 'streak', 'last_study_date')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'username', 'password', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ('created_at', 'last_login')
