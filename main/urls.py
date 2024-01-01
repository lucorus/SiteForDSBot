from django.urls import path
from . import views


urlpatterns = [
    path('', views.MainView.as_view(), name='main_page'),
    path('register', views.RegistrationView.as_view(), name='register'),
    path('login', views.UserLoginView.as_view(), name='login'),
    path('logout', views.user_logout, name='logout'),
    path('profile/<slug:slug>', views.ProfileView.as_view(), name='profile'),
    path('user/<str:user_id>/<int:server_id>', views.UserInfoView.as_view(), name='user_info'),
    path('user/<str:user_id>', views.UserInfoView.as_view(), name='user_info'),
    path('authorize_user', views.AuthorizUser.as_view(), name='authorize_user'),
    path('server_info/<int:server_id>', views.ServerInfoView.as_view(), name='server_info'),
    path('server_info_api/<int:server_id>', views.ServerInfoApiView.as_view(), name='server_info_api'),
    path('AnAuthorize/<slug:slug>', views.AnAuthoriz.as_view(), name='anauthoriz'),
    path('anauthorizeuser', views.AnAuthorizUser.as_view(), name='anauthorizuser'),
    path('server_functional/<str:user_id>/<int:server_id>', views.DepositView.as_view(), name='server_functional'),
    path('server_functional/<str:user_uuid>/<int:user_points>/<int:server_id>',
         views.CreateDepositView.as_view(), name='create_deposit'),
    path('delete_deposit/<str:deposit_uuid>/<str:user_uuid>/<int:user_points>/<int:deposit_points>/<int:server_id>',
         views.DeleteDepositView.as_view(), name='delete_deposit')
]
