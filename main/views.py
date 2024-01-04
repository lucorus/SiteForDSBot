from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from rest_framework import generics
from rest_framework.response import Response
from SiteForDSBot.settings import BASE_DIR
from rest_framework.views import APIView
from django.utils.text import slugify
from django.shortcuts import redirect
from django.http import JsonResponse
from django.shortcuts import render
from datetime import datetime
from django.views import View
import shortuuid as shortuuid
from typing import Union
from . import serializers
from . import models
from . import forms
import psycopg2
import logging
import environ
import pytz
import uuid
import os


logger = logging.getLogger('main')
try:
    env = environ.Env()
    environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
    host = env('host')
    user = env('user')
    password = env('password')
    database = env('database')

    with psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database,
    ) as connection:
        cursor = connection.cursor()
except Exception as ex:
    logger.critical(ex)


def time_now() -> str:
    timezone = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(timezone)
    formatted_time = moscow_time.strftime('%Y/%m/%d/%H/%M')
    return formatted_time


# возвращает id пользователя, если пользователь на сервере, иначе false
def on_server(user_id: str, server_id: int) -> Union[str, bool]:
    cursor.execute(
        '''
        SELECT user_id FROM users WHERE server_id=%s
        ''', (server_id, )
    )
    users = cursor.fetchall()

    if (user_id,) in users:
        return user_id
    return False


def get_deposit_info(user_uuid: str) -> list:
    deposit = []
    try:
        cursor.execute(
            '''
            SELECT * FROM deposit WHERE investor=%s
            ''', (user_uuid, )
        )
        deposit = cursor.fetchone()
    except Exception as ex:
        logger.error(ex)
    return deposit


# возвращает данные о 100 пользователях с самым большим количеством баллов / пользователях одного сервера
def get_users_info(server_id: int=None) -> list:
    users = []
    try:
        if server_id == None:
            cursor.execute("SELECT * FROM users ORDER BY points DESC LIMIT 100")
        else:
            cursor.execute("SELECT * FROM users WHERE server_id=%s ORDER BY points DESC", (server_id, ))
        users = cursor.fetchall()
    except Exception as ex:
        logger.error(ex)
    return users


class MainView(ListView, FormView):
    template_name = 'main/main_page.html'
    context_object_name = 'users'
    paginate_by = 10
    form_class = forms.UserLoginForm

    def get_queryset(self):
        users = get_users_info()
        return users


# Проверяет данные формы на валидность и возвращает словарь с ошибками
def checking_form_data(username, password, email) -> dict:
    errors = {}
    if models.CustomUser.objects.filter(username__iexact=username).exists():
        errors['username'] = 'Пользователь с таким именем уже существует!'
    if len(password) < 8:
        errors['password'] = 'Пароль должен состоять минимум из 8 символов'
    if models.CustomUser.objects.filter(email__iexact=email).exists():
        errors['email'] = 'Пользователь с такой почтой уже существует!'
    return errors


class RegistrationView(View):
    def post(self, request):
        try:
            username = str(request.POST.get('username'))
            password = str(request.POST.get('password'))
            email = str(request.POST.get('email'))

            # проверяем форму на валидность
            errors = checking_form_data(username, password, email)

            if errors:
                return JsonResponse({'status': 'error', 'errors': errors})
            else:
                # Создание нового пользователя
                user = models.CustomUser.objects.create_user(username=username, password=password,
                                                            email=email, slug=slugify(username),
                                                            token=shortuuid.uuid()[:12])
                user.save()
                login(request, user)

                return JsonResponse({'status': 'success'})
        except Exception as ex:
            logger.error(ex)
            return JsonResponse({'status': 'error'})

    def get(self, request):
        return render(request, 'main/register.html')


class UserLoginView(View):
    def get(self, request):
        try:
            form = forms.UserLoginForm()
            return render(request, 'main/login.html', {'form': form})
        except Exception as ex:
            logger.error(ex)
            return redirect('main_page')

    def post(self, request):
        try:
            form = forms.UserLoginForm(data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if not user.is_banned:
                    login(request, user)
                return redirect('main_page')
        except Exception as ex:
            logger.error(ex)


@login_required
def user_logout(request):
    try:
        logout(request)
        return redirect('main_page')
    except Exception as ex:
        logger.error(ex)


class ServerInfoView(ListView):
    context_object_name = 'server'
    template_name = 'main/server.html'
    paginate_by = 10

    def get_queryset(self):
        server = get_users_info(int(self.kwargs['server_id']))
        return server


# возвращает информацию о всех серверах, где есть пользователь / о сервере с переданным id
def get_user_info(user_id: str, server_id: int=None) -> list:
    try:
        if not server_id:
            # если id сервера нет, то возвращаем все сервера с данным юзером
            cursor.execute(
                '''
                SELECT * FROM users WHERE user_id=%s ORDER BY points DESC;
                ''', (user_id,)
            )
        else:
            # иначе только сервер с указанным id
            cursor.execute(
                '''
                SELECT * FROM users WHERE user_id=%s AND server_id=%s;
                ''', (user_id, server_id)
            )
        user_ds = cursor.fetchall()
        return user_ds
    except Exception as ex:
        logger.error(ex)
        return []


# Вычисляет сколько баллов получил пользователь по депозиту с процентом contribution_coefficient
def calculate_percent(points, time_delta) -> int:
    points = points * 0.05 + points
    time_delta -= 1
    if time_delta > 0:
        return calculate_percent(points, time_delta)
    else:
        return round(points)


# Изменяет кол-во баллов пользователя по его вкладу в базе данных (возвращает True если было изменение, а иначе False)
def calculate_deposit(deposit_uuid: str, points: int, deposit_last_update_time_time: str) -> bool:
    try:
        # находим кол-во дней со дня создания счёта
        time_delta = datetime.strptime(time_now(), "%Y/%m/%d/%H/%M") \
                 - datetime.strptime(deposit_last_update_time_time, "%Y/%m/%d/%H/%M")
        time_delta = time_delta.total_seconds() // 86400

        # если прошло больше дня, то изменяем кол-во баллов на счёте
        if time_delta >= 1:
            points = calculate_percent(points, time_delta)
            cursor.execute(
                '''
                UPDATE deposit SET current_points=%s AND last_update=%s WHERE uuid=%s
                ''', points, time_now(), deposit_uuid)
            connection.commit()
            return True
    except Exception as ex:
        logger.error(ex)
    return False


# отображает информацию о депозите / выводит форму для создания депозита
class DepositView(LoginRequiredMixin, APIView):
    def get(self, request, user_id: str, server_id: int):
        user_data = get_user_info(user_id=user_id, server_id=server_id)
        return render(request, 'main/server_functional.html', {'user_ds': user_data[0]})


def create_deposit(user_uuid: str, user_points: int, points: int) -> None:
    cursor.execute(
        '''
        INSERT INTO deposit VALUES(%s, %s, %s, %s, %s, %s);
        UPDATE users SET points=%s WHERE uuid=%s;
        ''', (
            str(uuid.uuid4()), user_uuid, points, time_now(),
            time_now(), points, user_points - points, user_uuid
        )
    )
    connection.commit()


# создаёт депозит
class CreateDepositView(LoginRequiredMixin, APIView):
    def post(self, request):
        try:
            points = int(request.POST.get('points'))
            user_points = int(request.POST.get('user_points'))
            user_uuid = request.POST.get('user_uuid')
            server_id = int(request.POST.get('server_id'))

            if points < 20 or user_points < points:
                return redirect('server_info', server_id=server_id)
            else:
                create_deposit(user_uuid, user_points, points)
                return redirect('server_info', server_id=server_id)
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')


def delete_deposit(deposit_uuid: str, user_points: int, deposit_points: int, user_uuid: str) -> None:
    cursor.execute(
        '''
        DELETE FROM deposit WHERE uuid=%s;
        UPDATE users SET points=%s WHERE uuid=%s
        ''', (deposit_uuid, user_points + deposit_points, user_uuid)
    )
    connection.commit()


# удаляет депозит
class DeleteDepositView(LoginRequiredMixin, APIView):
    def post(self, request):
        try:
            deposit_uuid = request.POST.get('deposit_uuid')
            user_uuid = request.POST.get('user_uuid')
            user_points = int(request.POST.get('user_points'))
            deposit_points = int(request.POST.get('deposit_points'))
            server_id = int(request.POST.get('server_id'))

            delete_deposit(deposit_uuid, user_points, deposit_points, user_uuid)
            return redirect('server_info', server_id=server_id)
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')


class ServerInfoApiView(APIView):
    def get(self, request, server_id):
        server = get_users_info(server_id)
        return JsonResponse({'status': 'success', 'users': server})


class ProfileView(generics.RetrieveAPIView):
    serializer_class = serializers.UserSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        try:
            slug = self.kwargs['slug']
        except:
            slug = self.request.user.slug
        return models.CustomUser.users.filter(slug=slug)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            user_ds = None
            if instance.is_authorized:
                # если пользователь авторизован, то возвращаем данные о его дискорд аккаунте
                user_ds = get_user_info(instance.discord_server_id)
            return render(request, 'main/profile.html', {
                                                            'user': serializer.data,
                                                            'user_ds': user_ds
                                                        })
        except Exception as ex:
            logger.error(ex)
            return redirect('main_page')


# возвращает информацию о пользователе на основе его id
class UserInfoView(APIView):
    def get(self, request, user_id: str, server_id: int=None):
        try:
            user_info = get_user_info(user_id, server_id)
            return JsonResponse({'status': 'success', 'user_info': user_info})
        except Exception as ex:
            logger.error(ex)
            return JsonResponse({'status': 'error'})


'''
Дискорд бот может обратиться к данному API, передав в него token пользователя (пользователь дискорд пишет его боту в личные сообщения),
id пользователя, который написал боту и токен доступа.
Если данный дискорд аккаунт ещё не привязан к какому-либо аккаунту на сайте и если пользователь с таким token существует,
то привязываем аккаунт в дискорд к данному аккаунту на сайте (аккаунту с переданным token)
'''
class AuthorizUser(APIView):
    def post(self, request):
        try:
            access_token = request.headers['Access'] # получаем токен доступа
            env = environ.Env()
            environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
            if access_token != env('access_token'):
                return JsonResponse({'status': 'error', 'message': 'Incorrect access token'})

            token = request.headers['Token']  # токен пользователя на сайте
            user = request.headers['User']  # id пользователя в дискорд
            user_in_db = models.CustomUser.objects.get(token=token)
            if user_in_db.is_authorized:
                '''
                если боту напишут токен уже авторизированного пользователя на сайте
                '''
                return Response({'status': 'error', 'message': 'This User is already authorized'})
            elif len(models.CustomUser.objects.filter(discord_server_id=user)) > 0:
                '''
                если боту напишут токен с дискорд аккаунта, который уже привязан к другому аккаунту на сайте
                '''
                return JsonResponse({'status': 'error', 'message': 'This account already authorized'})
            else:
                user_in_db.discord_server_id = user
                user_in_db.is_authorized = True
                user_in_db.save()
                return JsonResponse({'status': 'success'})
        except Exception as ex:
            logger.error(ex)
            return JsonResponse({'status': 'error', 'message': 'Unknown error'})


# Отвязываем аккаунт дискорда от пользователя на сервере через сайт
class AnAuthoriz(LoginRequiredMixin, View):
    def get(self, request, slug):
        try:
            user = models.CustomUser.objects.get(slug=slug)
            if request.user.slug == user.slug:
                user.is_authorized = False
                user.discord_server_id = ' '
                user.save()
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')


class AnAuthorizUser(APIView):
    def post(self, request):
        try:
            access_token = request.headers['Access']  # получаем токен доступа
            env = environ.Env()
            environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
            if access_token != env('access_token'):
                return JsonResponse({'status': 'error', 'message': 'Incorrect access token'})

            user = request.headers['User']  # id пользователя в дискорд
            user_in_db = models.CustomUser.objects.get(discord_server_id=user)
            if user_in_db.is_authorized:
                # если пользователь найден
                user_in_db.discord_server_id = ' '
                user_in_db.is_authorized = False
                user_in_db.save()
                return JsonResponse({'status': 'success', 'message': 'user authorized'})
            else:
                return JsonResponse({'status': 'error', 'message': 'user not found'})
        except Exception as ex:
            logger.error(ex)
            return JsonResponse({'status': 'error', 'message': 'Unknown error'})


class ChangeToken(LoginRequiredMixin, View):
    def get(self, request):
        try:
            request.user.token = shortuuid.uuid()[:12]
            request.user.save()
            return redirect('profile', slug=request.user.slug)
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')

