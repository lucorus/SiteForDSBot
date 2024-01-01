from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_banned=False)


class CustomUser(AbstractUser):
    username = models.CharField(max_length=25, unique=True, verbose_name='Имя пользователя')
    slug = models.SlugField(unique=True)
    '''
    токен генирируется на основе id пользователя, с его помощью можно привязать аккаунт на сайте с аккаунтом в дискорде
    '''
    token = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=130, blank=True, verbose_name='Описание')

    discord_server_id = models.CharField(max_length=50, blank=True, verbose_name='id пользователя дискорд')
    is_authorized = models.BooleanField(default=False, verbose_name='Авторизирован?')
    is_banned = models.BooleanField(default=False, verbose_name='Забанен?')
    objects = UserManager()
    users = CustomUserManager()

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
