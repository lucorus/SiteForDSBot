from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from SiteForDSBot.settings import BASE_DIR
from django.utils.text import slugify
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import shortuuid as shortuuid
from rest_framework.response import Response
from rest_framework.views import APIView
from . import forms
from . import models
import psycopg2
import environ
import os


# возвращает объект connection
def connect_db() -> psycopg2.extensions.connection:
    print('Установка соединения')
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
    print('PostgreSQL соединение завершено')


class MainView(ListView, FormView):
    template_name = 'main/main_page.html'
    context_object_name = 'users'
    paginate_by = 1
    form_class = forms.UserLoginForm

    def get_queryset(self):
        users = []

        try:
            connection = connect_db()
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM users")

            users = cursor.fetchall()


        # try:
        #     env = environ.Env()
        #     environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
        #     host = env('host')
        #     user = env('user')
        #     password = env('password')
        #     database = env('database')
        #
        #     connection = psycopg2.connect(
        #         host=host,
        #         user=user,
        #         password=password,
        #         database=database,
        #     )
        #
        #     cursor = connection.cursor()
        #
        #     cursor.execute("SELECT * FROM users")
        #
        #     users = cursor.fetchall()

        except:
            pass
        finally:
            # cursor.close()
            # connection.close()
            close_db(cursor, connection)
            #print('PostgreSQL connection closed')

        return users


class RegistrationView(View):
    def post(self, request):
        username = str(request.POST.get('username'))
        password = str(request.POST.get('password'))
        email = str(request.POST.get('email'))

        # Проверка данных формы
        errors = {}
        if models.CustomUser.objects.filter(username__iexact=username).exists():
            errors['username'] = 'Пользователь с таким именем уже существует!'
        if len(password) < 8:
            errors['password'] = 'Пароль должен состоять минимум из 8 символов'
        if models.CustomUser.objects.filter(email__iexact=email).exists():
            errors['email'] = 'Пользователь с такой почтой уже существует!'

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


class ServerInfoView(DetailView):
    template_name = 'main/server.html'
    context_object_name = 'server'

    def get_object(self, queryset=None):
        server_id = self.kwargs['server_id']
        connection = connect_db()
        cursor = connection.cursor()

        cursor.execute('''
            SELECT * FROM users WHERE server_id=%s
        ''', (server_id, ))

        server = cursor.fetchall()

        close_db(cursor, connection)
        return server


class ProfileView(LoginRequiredMixin, ListView):
    login_url = 'main_page'
    template_name = 'main/profile.html'
    context_object_name = 'user'

    def get_queryset(self):
        pk = self.request.GET.get('user_pk')
        if pk:
            user = models.CustomUser.users.get(pk=pk)
        else:
            user = models.CustomUser.users.get(pk=self.request.user.pk)

        user_ds = None

        if user.is_authorized:
            connection = connect_db()
            cursor = connection.cursor()

            cursor.execute(
                '''
                SELECT * FROM users WHERE user_id=%s
                ''', (user.discord_server_id, )
            )

            user_ds = cursor.fetchall()

            close_db(cursor, connection)

        return {'user': user, 'user_ds': user_ds}


# Бот может вызвать данное API, чтобы присоединить аккаунт дискорд к аккаунту на сервере
class AuthorizUser(APIView):
    def post(self, request):
        try:
            token = request.POST.get('token')
            user = request.POST.get('user')
            user_in_db = models.CustomUser.objects.get(token=token)
            if user_in_db.is_authorized:
                pass
            else:
                user_in_db.discord_server_id = user
                user_in_db.is_authorized = True
                user_in_db.save()

            return Response({'status': 'success'})
        except Exception as ex:
            print(ex)
            return Response({'status': 'error'})
