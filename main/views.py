from django.views.generic import ListView, FormView
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
from django.views import View
import shortuuid as shortuuid
from . import serializers
from . import functions
from . import forms
from . import models
import logging
import environ
import os

logger = logging.getLogger('main')


class MainView(ListView, FormView):
    template_name = 'main/main_page.html'
    context_object_name = 'users'
    paginate_by = 10
    form_class = forms.UserLoginForm

    def get_queryset(self):
        users = functions.get_users_info()
        return users


class RegistrationView(View):
    def post(self, request):
        try:
            username = str(request.POST.get('username'))
            password = str(request.POST.get('password'))
            email = str(request.POST.get('email'))

            # проверяем форму на валидность
            errors = functions.checking_form_data(username, password, email)

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
        server = functions.get_users_info(int(self.kwargs['server_id']))
        return server

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guild = functions.get_guild(self.kwargs['server_id'])
        context['guild'] = guild
        return context


class GetDepositInfoAPI(APIView):
    def get(self, request, user_uuid: str):
        try:
            deposit = functions.get_deposit_info(user_uuid)
            if deposit:
                change = functions.calculate_deposit(deposit[0], deposit[5], deposit[4])
                if change:
                    deposit = functions.get_deposit_info(user_uuid)
                return JsonResponse({'status': 'success', 'data': deposit})
            else:
                return JsonResponse({'status': 'error'})
        except Exception as ex:
            logger.error(ex)
            return JsonResponse({'status': 'error'})


# отображает информацию о депозите / выводит форму для создания депозита
class DepositView(LoginRequiredMixin, View):
    def get(self, request, user_id: str, server_id: int):
        try:
            user_data = functions.get_user_info(user_id=user_id, guild_id=server_id)[0]
            return render(request, 'main/server_functional.html', {'user_ds': user_data})
        except Exception as ex:
            print(ex)
            return render(request, 'main/server_functional.html', {'user_ds': []})


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
                functions.create_deposit(user_uuid, user_points, points)
                return redirect('server_info', server_id=server_id)
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')


class DeleteDepositView(LoginRequiredMixin, APIView):
    def post(self, request):
        try:
            deposit_uuid = request.POST.get('deposit_uuid')
            user_uuid = request.POST.get('user_uuid')
            user_points = int(request.POST.get('user_points'))
            deposit_points = int(request.POST.get('deposit_points'))
            server_id = int(request.POST.get('server_id'))

            functions.delete_deposit(deposit_uuid, user_points, deposit_points, user_uuid)
            return redirect('server_info', server_id=server_id)
        except Exception as ex:
            logger.error(ex)
        return redirect('main_page')


class ServerInfoApiView(APIView):
    def get(self, request, server_id):
        server = functions.get_users_info(server_id)
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
                user_ds = functions.get_user_info(instance.discord_server_id)
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
            user_info = functions.get_user_info(user_id, server_id)
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

