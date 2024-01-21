from django.urls import path
from . import views


urlpatterns = [
    # обычные представления
    path('', views.MainView.as_view(), name='main_page'),
    path('server_info/<int:server_id>', views.ServerInfoView.as_view(), name='server_info'),
    path('server_functional/<str:user_id>/<int:server_id>', views.DepositView.as_view(), name='server_functional'),

    # взаимодействие с пользователем
    path('register', views.RegistrationView.as_view(), name='register'),
    path('login', views.UserLoginView.as_view(), name='login'),
    path('logout', views.user_logout, name='logout'),
    path('profile/<slug:slug>', views.ProfileView.as_view(), name='profile'),
    path('change_token', views.ChangeToken.as_view(), name='change_token'),

    # api
    path('deposit/<str:user_uuid>', views.GetDepositInfoAPI.as_view(), name='get_deposit_info'),
    path('user/<str:user_id>/<int:server_id>', views.UserInfoView.as_view(), name='user_info'),
    path('user/<str:user_id>', views.UserInfoView.as_view(), name='user_info'),
    path('server_info_api/<int:server_id>', views.ServerInfoApiView.as_view(), name='server_info_api'),

    # взаимодействие аккаунта в дискорд с аккаунтом на сайте
    path('authorize_user', views.AuthorizUser.as_view(), name='authorize_user'),
    path('AnAuthorize/<slug:slug>', views.AnAuthoriz.as_view(), name='anauthoriz'),
    path('anauthorizeuser', views.AnAuthorizUser.as_view(), name='anauthorizuser'),

    # представления, позволяющие работать с функционалом бота через сайт
    path('server_functional', views.CreateDepositView.as_view(), name='create_deposit'),
    path('delete_deposit', views.DeleteDepositView.as_view(), name='delete_deposit'),
]
