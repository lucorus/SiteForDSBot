from django.urls import reverse
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
from . import models
from . import forms
from . import serializers
import psycopg2
import environ
import pytz
import uuid
import os


# возвращает объект connection
def connect_db() -> psycopg2.extensions.connection:
    env = environ.Env()
    environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
    host = env('host')
    user = env('user')
    password = env('password')
    database = env('database')

    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database,
    )

    return connection


# закрывает postgresql соединение
def close_db(cursor, connection):
    cursor.close()
    connection.close()


def time_now() -> str:
    timezone = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(timezone)
    formatted_time = moscow_time.strftime('%Y/%m/%d/%H/%M')
    return formatted_time


def get_deposit_info(user_uuid: str):
    deposit = []
    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute(
            '''
            SELECT * FROM deposit WHERE investor=%s
            ''', (user_uuid, )
        )
        deposit = cursor.fetchone()
    except Exception as ex:
        print(ex)
        pass
    finally:
        close_db(cursor, connection)
    return deposit


# возвращает данные о 100 пользователях с самым большим количеством баллов
def get_users_info() -> list:
    users = []
    try:
        connection = connect_db()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM users ORDER BY points DESC LIMIT 100")

        users = cursor.fetchall()
    except:
        pass
    finally:
        close_db(cursor, connection)
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

    def get(self, request):
        return render(request, 'main/register.html')


class UserLoginView(View):
    def get(self, request):
        form = forms.UserLoginForm()
        return render(request, 'main/login.html', {'form': form})

    def post(self, request):
        form = forms.UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
        return redirect('main_page')


@login_required
def user_logout(request):
    logout(request)
    return redirect('main_page')


def get_server_info(server_id: int) -> list:
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT * FROM users WHERE server_id=%s ORDER BY points DESC
        ''', (server_id,))

    server = cursor.fetchall()
    close_db(cursor, connection)
    return server


class ServerInfoView(ListView):
    context_object_name = 'server'
    template_name = 'main/server.html'
    paginate_by = 10

    def get_queryset(self):
        server = get_server_info(self.kwargs['server_id'])
        return server


# возвращает информацию о всех серверах, где есть пользователь / о сервере с переданным id
def get_user_info(user_id: str, server_id: int=None) -> list:
    try:
        connection = connect_db()
        cursor = connection.cursor()
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
        close_db(cursor, connection)
        return user_ds
    except Exception as ex:
        print(ex)
        return []


class DepositView(LoginRequiredMixin, APIView):
    def get(self, request, user_id: str, server_id: int):
        user_data = get_user_info(user_id=user_id, server_id=server_id)
        return render(request, 'main/server_functional.html', {'user_ds': user_data[0]})


class CreateDepositView(LoginRequiredMixin, APIView):
    def post(self, request, user_uuid: str, user_points: int, server_id: int):
        try:
            points = int(request.POST.get('numberInput'))
            print(points)
            if points < 20 or user_points < points:
                # return Response({'status': 'error', 'message': 'Вы ввели некорректны размер вклада'})
                return redirect('server_info', server_id=server_id)
            else:
                connection = connect_db()
                cursor = connection.cursor()
                cursor.execute(
                    '''
                    INSERT INTO deposit VALUES($1, $2, $3, $4, $5, $6)
                    ''', (str(uuid.uuid4()), user_uuid, points, time_now(), time_now(), points)
                )
                cursor.execute(
                    '''
                    UPDATE users SET points=%s WHERE uuid=%s
                    ''', (user_points-points, user_uuid)
                )
                return Response({'status': 'success'})
        except Exception as ex:
                print(ex)
        finally:
            try:
                close_db(cursor, connection)
            except:
                pass
        return redirect('server_info', server_id=server_id)
        #return Response({'status': 'error', 'message': 'Неизвестная ошибка'})


class DeleteDepositView(LoginRequiredMixin, APIView):
    def get(self, request, deposit_uuid: str, user_uuid: str, user_points: int, deposit_points: int, server_id: int):
        try:
            connection = connect_db()
            cursor = connection.cursor()
            cursor.execute(
                '''
                DELETE FROM deposit WHERE uuid=%s
                ''', (deposit_uuid, )
            )
            cursor.execute(
                '''
                UPDATE users SET points=%s WHERE uuid=%s
                ''', (user_points + deposit_points, user_uuid)
            )
            print('text')
            return redirect('server_info', server_id=server_id)
        except:
            return redirect('server_info', server_id=server_id)
        finally:
            try:
                close_db(cursor, connection)
            except:
                return redirect('server_info', server_id=server_id)


class ServerInfoApiView(APIView):
    def get(self, request, server_id):
        server = get_server_info(server_id)
        return Response({'status': 'success', 'users': server})


class ProfileView(generics.RetrieveAPIView):
    serializer_class = serializers.UserSerializer
    lookup_field = 'slug'

    # если пользователь авторизован, то получаем данные о его дискорд-аккаунте
    def get_discord_user_data(self, user: models.CustomUser):
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute(
            '''
            SELECT * FROM users WHERE user_id=%s ORDER BY points DESC;
            ''', (user.discord_server_id, )
        )
        user_ds = cursor.fetchall()
        close_db(cursor, connection)
        return user_ds

    def get_queryset(self):
        try:
            slug = self.kwargs['slug']
        except:
            slug = self.request.user.slug
        return models.CustomUser.users.filter(slug=slug)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        user_db = None
        if instance.is_authorized:
            user_db = self.get_discord_user_data(instance)
        return render(request, 'main/profile.html', {
                                                        'user': serializer.data,
                                                        'user_ds': user_db
                                                    })


# возвращает информацию о пользователе на основе его id
class UserInfoView(APIView):
    def get(self, request, user_id: str, server_id: int=None):
        user_info = get_user_info(user_id, server_id)
        return Response({'status': 'success', 'user_info': user_info})


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
                return Response({'status': 'error', 'message': 'Incorrect access token'})

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
                return Response({'status': 'error', 'message': 'This account already authorized'})
            else:
                user_in_db.discord_server_id = user
                user_in_db.is_authorized = True
                user_in_db.save()
                return Response({'status': 'success'})
        except Exception as ex:
            print(ex)
            return Response({'status': 'error', 'message': 'Unknown error'})


# Отвязываем аккаунт дискорда от пользователя на сервере через сайт
class AnAuthoriz(LoginRequiredMixin, View):
    def get(self, request, slug):
        user = models.CustomUser.objects.get(slug=slug)
        if request.user.slug == user.slug:
            user.is_authorized = False
            user.discord_server_id = ' '
            user.save()
        return redirect('main_page')


class AnAuthorizUser(APIView):
    def post(self, request):
        try:
            access_token = request.headers['Access']  # получаем токен доступа
            env = environ.Env()
            environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
            if access_token != env('access_token'):
                return Response({'status': 'error', 'message': 'Incorrect access token'})

            user = request.headers['User']  # id пользователя в дискорд
            user_in_db = models.CustomUser.objects.get(discord_server_id=user)
            if user_in_db.is_authorized:
                # если пользователь найден
                user_in_db.discord_server_id = ' '
                user_in_db.is_authorized = False
                user_in_db.save()
                return Response({'status': 'success', 'message': 'user authorized'})
            else:
                return Response({'status': 'error', 'message': 'user not found'})
        except Exception as ex:
            print(ex)
            return Response({'status': 'error', 'message': 'Unknown error'})



