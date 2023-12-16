from django.urls import path
from . import views


urlpatterns = [
    path('', views.MainView.as_view(), name='main_page'),
    path('register', views.RegistrationView.as_view(), name='register'),
    path('login', views.UserLoginView.as_view(), name='login'),
    path('logout', views.user_logout, name='logout'),
    path('profile', views.ProfileView.as_view(), name='profile'),
    path('profile/<slug:slug>', views.ProfileView.as_view(), name='profile'),
    path('authorize_user', views.AuthorizUser.as_view(), name='authorize_user'),
    path('server_info/<int:server_id>', views.ServerInfoView.as_view(), name='server_info'),
    path('AnAuthorize/<slug:slug>', views.AnAuthoriz.as_view(), name='anauthoriz'),
]
