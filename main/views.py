from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from rest_framework.response import Response
from SiteForDSBot.settings import BASE_DIR
from rest_framework.views import APIView
from django.utils.text import slugify
from django.shortcuts import redirect
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import shortuuid as shortuuid
from . import models
from . import forms
import psycopg2
import environ
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


class MainView(ListView, FormView):
    template_name = 'main/main_page.html'
    context_object_name = 'users'
    paginate_by = 10
    form_class = forms.UserLoginForm

    def get_queryset(self):
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


'''
Проверка данных формы на валидность
возвращает словарь с ошибками / пустой словарь
'''
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


# получение детальной информации о сервере
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
        try:
            slug = self.kwargs['slug']
        except:
            slug = None

        if slug:
            user = models.CustomUser.users.get(slug=slug)
        else:
            user = models.CustomUser.users.get(slug=self.request.user.slug)
        user_ds = None

        if user.is_authorized:
            connection = connect_db()
            cursor = connection.cursor()
            cursor.execute(
                '''
                SELECT * FROM users WHERE user_id=%s ORDER BY points DESC;
                ''', (user.discord_server_id, )
            )

            user_ds = cursor.fetchall()
            close_db(cursor, connection)
        return {'user': user, 'user_ds': user_ds}


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


'''
Отвязываем аккаунт дискорда от пользователя на сервере
'''
class AnAuthoriz(LoginRequiredMixin, View):
    def get(self, request, slug):
        user = models.CustomUser.objects.get(slug=slug)
        if request.user.slug == user.slug:
            user.is_authorized = False
            user.discord_server_id = ' '
            user.save()
        return redirect('main_page')



